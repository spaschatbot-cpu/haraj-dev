"""The one place that decides whether a person may bid on a car.

Every bidding path calls :func:`check_eligibility` and none of them asks a
question of its own. That is the whole design, and it is a reaction to a
measured failure: in v1 the home page alone offered **six** ways to send a bid,
so every new rule had to be added in six places and the one that was missed
became the hole. `ops/checks/one_eligibility_gate.py` fails CI if any other
module on the bidding surface reads one of the facts this function reads.

Two more properties matter as much as the single location:

* **The reasons are enumerated.** :class:`~apps.bidding.models.RefusalReason`
  is the vocabulary; a free-text reason cannot be counted, cannot be tested one
  by one, and cannot be answered by a screen.
* **The answer carries the money it was based on.** The snapshot travels with
  the decision so the refusal record (T502) states what was true at the instant
  of the refusal, not what is true when support finally looks.

Nothing here writes anything. It reads, decides, and returns — so a screen can
ask "may I?" and get the same answer the write path would produce, from the
same code.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from django.conf import settings
from django.utils import timezone

from apps.auctions.states import AuctionState, VehicleState
from apps.money.models import (
    MONEY,
    ZERO,
    Account,
    AccountKind,
    Hold,
    HoldReason,
    HoldState,
    Invoice,
    InvoiceState,
)

from .models import RefusalReason

__all__ = [
    "BIDDABLE_VEHICLE_STATES",
    "Eligibility",
    "MoneySnapshot",
    "check_eligibility",
    "minimum_bid_for",
    "money_snapshot",
]

#: A car takes bids while it is on the block and not a moment longer. `listed`
#: is included because the first bid is what moves it to `bidding`.
BIDDABLE_VEHICLE_STATES = (VehicleState.LISTED, VehicleState.BIDDING)

#: Dues that stand in a bidder's way. A draft invoice has not been issued yet
#: and a cancelled one is not owed; neither is a debt.
UNPAID_INVOICE_STATES = (InvoiceState.OPEN, InvoiceState.PARTIAL)

_CENT = Decimal(1).scaleb(-MONEY["decimal_places"])


@dataclass(frozen=True)
class MoneySnapshot:
    """A bidder's money at one instant, in the words the wallet screen uses.

    Kept as four plain Decimals rather than as a queryset or a live object
    because its whole purpose is to stop being live: it is copied onto the
    refusal record, and the balances move on without it.
    """

    insurance_free: Decimal = ZERO
    insurance_held: Decimal = ZERO
    insurance_locked: Decimal = ZERO
    outstanding_dues: Decimal = ZERO


@dataclass(frozen=True)
class Eligibility:
    """The verdict, its reason, and the evidence behind it."""

    allowed: bool
    money: MoneySnapshot
    #: Renamed from the auction's own column on purpose: this is the gate's
    #: answer about this bidder, and reading it is not reading the rule.
    required_deposit: Decimal
    minimum_bid: Decimal

    #: A :class:`~apps.bidding.models.RefusalReason` value, or ``None`` when
    #: the answer is yes. Never a sentence — the sentence is ``detail``.
    reason: str | None = None

    #: Arabic, ready for a screen, and naming this bidder's own numbers.
    detail: str = ""

    #: True when the deposit for this auction is already held, so the caller
    #: knows this bid costs nothing further (T505).
    already_held: bool = False

    def __bool__(self) -> bool:
        return self.allowed

    @property
    def reason_label(self) -> str:
        return RefusalReason(self.reason).label if self.reason else ""


def minimum_bid_for(vehicle) -> Decimal:
    """The smallest bid the platform accepts, decided in one place.

    Deliberately **not** derived from the car's reserve: bidding under the
    reserve is a supported outcome — the owner then decides — so the reserve is
    not a floor. What this refuses is the one-riyal bid, which in a sealed
    auction is not a signal about a car but noise in the ledger, since every
    bid pins a deposit.
    """
    return Decimal(settings.MINIMUM_BID).quantize(_CENT)


def deposit_required_for(auction) -> Decimal:
    """What this auction asks for, read from the money layer, never from a request."""
    from apps.money import services as money

    return money.deposit_amount_for(auction=auction)


def _buckets(user) -> dict[str, Decimal]:
    """The customer's insurance balances, read without creating a single row.

    Read straight off the account rows rather than through
    ``services.wallet_snapshot``: that one also counts every ledger entry the
    customer owns to itemise the statement, and this runs on the bidding path
    where fifty callers at once is the design point rather than the exception.
    Nothing is created either — a bidder who has never deposited has no rows,
    and asking about them must not bring four into existence.
    """
    return {
        row["kind"]: row["balance"]
        for row in Account.objects.filter(
            owner=user, kind__in=AccountKind.customer_owned()
        ).values("kind", "balance")
    }


def _snapshot(buckets: dict[str, Decimal], dues: Decimal) -> MoneySnapshot:
    return MoneySnapshot(
        insurance_free=buckets.get(AccountKind.INSURANCE_FREE, ZERO),
        insurance_held=buckets.get(AccountKind.INSURANCE_HELD, ZERO),
        insurance_locked=buckets.get(AccountKind.INSURANCE_LOCKED, ZERO),
        outstanding_dues=dues,
    )


def money_snapshot(user) -> MoneySnapshot:
    """The three insurance buckets and what the bidder owes, right now."""
    return _snapshot(_buckets(user), _dues(user)[0])


def _dues(user) -> tuple[Decimal, Decimal]:
    """``(everything owed, what of it still blocks bidding)``.

    The two numbers differ when an owner has granted an exception (T515): the
    debt is still a debt and the snapshot must say so, but a named person with
    a written reason has decided it will not stop this bidder. Recording only
    the second number would erase the debt from the history; gating on the
    first would make the exception meaningless.
    """
    unpaid = list(Invoice.objects.filter(customer=user, state__in=UNPAID_INVOICE_STATES))
    if not unpaid:
        return ZERO, ZERO

    excused = set(
        Hold.objects.filter(
            owner=user,
            state=HoldState.ACTIVE,
            reason=HoldReason.DUES,
            invoice__in=unpaid,
            exception_granted_by__isnull=False,
        )
        .exclude(exception_note="")
        .values_list("invoice_id", flat=True)
    )

    total = sum((invoice.outstanding for invoice in unpaid), start=ZERO)
    blocking = sum(
        (invoice.outstanding for invoice in unpaid if invoice.pk not in excused),
        start=ZERO,
    )
    return total, blocking


def _profile_gap(user) -> str:
    """What is missing from this person's file, in one Arabic phrase, or ``""``.

    A company bids as a company: v1 showed the representative's name on some
    screens and the company's on others, and support could not tell which
    account had bid at all.
    """
    from apps.accounts.models import AccountType

    if not user.full_name.strip():
        return "الاسم"
    if not user.national_id.strip():
        return "رقم الهوية"
    if user.account_type == AccountType.COMPANY and not hasattr(user, "company"):
        return "بيانات الشركة"
    return ""


def _owns(user, vehicle) -> bool:
    if vehicle.owner_company_id is None:
        return False
    company = getattr(user, "company", None)
    return company is not None and vehicle.owner_company_id == company.pk


def check_eligibility(
    user,
    vehicle,
    *,
    amount: Decimal | None = None,
    now: datetime | None = None,
) -> Eligibility:
    """May this person bid this amount on this car? Yes, or no and why.

    ``amount`` is optional so a screen can ask "may I bid at all?" before the
    customer has typed a number; the amount-shaped rule is simply skipped when
    it is absent, and every other rule answers the same either way.

    The order of the checks is the order a person would explain them in: is the
    sale even open, is this car in it, is it yours, do we know who you are, is
    the number sane, do you owe us, have you put down a deposit. Dues come
    before the deposit deliberately — a debtor's insurance is locked, so both
    would refuse, and "عليك مستحقات" is the answer that tells them what to do.
    """
    now = now or timezone.now()
    auction = vehicle.auction

    # Both halves of the dues answer come from one pass over the invoices: the
    # total belongs in the snapshot, the blocking part decides the gate.
    total_dues, blocking_dues = _dues(user)
    money = _snapshot(_buckets(user), total_dues)
    deposit_required = deposit_required_for(auction)
    minimum_bid = minimum_bid_for(vehicle)

    def refuse(reason: str, detail: str) -> Eligibility:
        return Eligibility(
            allowed=False,
            reason=reason,
            detail=detail,
            money=money,
            required_deposit=deposit_required,
            minimum_bid=minimum_bid,
        )

    # --- the sale itself ---------------------------------------------------
    if auction.state in (AuctionState.ENDED, AuctionState.SETTLED) or (
        auction.state == AuctionState.LIVE and now >= auction.ends_at
    ):
        return refuse(RefusalReason.AUCTION_ENDED, "انتهى وقت هذا المزاد.")
    if auction.state != AuctionState.LIVE or now < auction.starts_at:
        return refuse(
            RefusalReason.AUCTION_NOT_LIVE,
            "المزاد غير مفتوح للمزايدة الآن.",
        )

    # --- the car -----------------------------------------------------------
    if vehicle.state not in BIDDABLE_VEHICLE_STATES:
        return refuse(
            RefusalReason.VEHICLE_NOT_BIDDABLE,
            f"المركبة «{VehicleState(vehicle.state).label}» ولا تقبل مزايدة.",
        )
    if _owns(user, vehicle):
        return refuse(RefusalReason.OWN_VEHICLE, "لا يمكنك المزايدة على مركبتك.")

    # --- the person --------------------------------------------------------
    if user.phone_verified_at is None:
        return refuse(
            RefusalReason.PHONE_NOT_VERIFIED,
            "لازم توثّق رقم جوالك قبل المزايدة.",
        )
    gap = _profile_gap(user)
    if gap:
        return refuse(
            RefusalReason.PROFILE_INCOMPLETE, f"ملفك ناقص: {gap} مطلوب للمزايدة."
        )

    # --- the number --------------------------------------------------------
    if amount is not None and amount < minimum_bid:
        return refuse(
            RefusalReason.BELOW_FLOOR,
            f"أقل مزايدة مقبولة {minimum_bid} ريال.",
        )

    # --- the money ---------------------------------------------------------
    if blocking_dues > ZERO:
        return refuse(
            RefusalReason.UNPAID_DUES,
            f"عليك مستحقات غير مسدَّدة قدرها {blocking_dues} ريال.",
        )

    # The deposit is taken once per auction, so a bidder who is already in this
    # auction has paid it and their free balance is beside the point (T505).
    already_held = Hold.objects.filter(
        owner=user, auction=auction, state=HoldState.ACTIVE
    ).exists()
    if not already_held and money.insurance_free < deposit_required:
        return refuse(
            RefusalReason.NO_DEPOSIT,
            f"تحتاج تأميناً متاحاً قدره {deposit_required} ريال للمزايدة في هذا "
            f"المزاد، والمتاح لديك {money.insurance_free} ريال.",
        )

    return Eligibility(
        allowed=True,
        money=money,
        required_deposit=deposit_required,
        minimum_bid=minimum_bid,
        already_held=already_held,
    )
