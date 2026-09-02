"""Asking Odoo whether it agrees with us (Article 2-5).

Our ledger proving itself consistent says nothing about whether it is right.
In v1 a customer's balance showed 10,000 and he bid with it, while Odoo's
ledger for him closed at zero — and every guard built at the time was checking
our numbers against our numbers.

**Q2, decided 2026-09-02:** Odoo exposes no balance endpoint, so `theirs` is
computed as confirmed subscriptions minus confirmed refunds, via `call_kw`.
That is weaker than reading a real balance, and this module is written to keep
that weakness visible rather than let it harden into a number people trust:

* the method and its version are recorded on every row, so results from an
  older definition stay distinguishable from newer ones;
* "confirmed" is defined here, in one place, by an explicit list of Odoo
  states;
* a state we have never seen is **neither counted nor silently skipped** — it
  is recorded in `detail` and named in the note, because a new state on their
  side may be real money we do not know how to count (Article 2-3).

A difference opens a record. **It never moves a riyal** — reconciling by
writing to the ledger would be the system correcting the book of record with
the copy.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation

from apps.money.models import AccountKind
from apps.money.services import account_for

from .client import call
from .models import BalanceCheck, CustomerLink

log = logging.getLogger(__name__)

#: Named and versioned. When the definition changes — and it will — old rows
#: stay readable as products of the old rule instead of blending into the new.
METHOD = "subscriptions_minus_refunds/v1"

#: What Odoo calls a subscription that really was paid.
CONFIRMED_SUBSCRIPTION_STATES = frozenset({"paid", "posted", "done", "confirmed"})

#: And a refund that really went out.
CONFIRMED_REFUND_STATES = frozenset({"paid", "posted", "done", "confirmed"})

#: States we know about and deliberately do not count.
KNOWN_UNCOUNTED_STATES = frozenset({"draft", "cancel", "cancelled", "pending"})

ZERO = Decimal("0.00")


@dataclass
class TheirBalance:
    """What Odoo's records add up to, and what we could not make sense of."""

    total: Decimal = ZERO
    subscriptions: Decimal = ZERO
    refunds: Decimal = ZERO
    unknown_states: dict[str, int] = field(default_factory=dict)
    unreadable_amounts: int = 0

    @property
    def is_complete(self) -> bool:
        return not self.unknown_states and not self.unreadable_amounts


def compute_their_balance(odoo_customer_id: str) -> TheirBalance:
    """Subscriptions minus refunds, as Odoo has them.

    Anything in a state this module has never seen is counted in
    `unknown_states` rather than added or dropped. The resulting figure is
    then known to be incomplete, and the caller says so instead of presenting
    it as a comparison.
    """
    result = TheirBalance()

    subscriptions = call(
        "call_kw",
        {
            "model": "sale.subscription",
            "method": "search_read",
            "domain": [["partner_id", "=", odoo_customer_id]],
            "fields": ["amount_total", "state"],
        },
        reference=f"balance:{odoo_customer_id}:subscriptions",
    )
    refunds = call(
        "call_kw",
        {
            "model": "account.move",
            "method": "search_read",
            "domain": [
                ["partner_id", "=", odoo_customer_id],
                ["move_type", "=", "out_refund"],
            ],
            "fields": ["amount_total", "state"],
        },
        reference=f"balance:{odoo_customer_id}:refunds",
    )

    result.subscriptions = _sum_rows(
        subscriptions.get("records", []), CONFIRMED_SUBSCRIPTION_STATES, result
    )
    result.refunds = _sum_rows(
        refunds.get("records", []), CONFIRMED_REFUND_STATES, result
    )
    result.total = result.subscriptions - result.refunds
    return result


def _sum_rows(rows, confirmed_states: frozenset, result: TheirBalance) -> Decimal:
    total = ZERO
    for row in rows:
        state = str(row.get("state", ""))
        if state not in confirmed_states and state not in KNOWN_UNCOUNTED_STATES:
            # Not counted, and not ignored either. Somebody has to look.
            result.unknown_states[state] = result.unknown_states.get(state, 0) + 1
            continue
        if state not in confirmed_states:
            continue
        try:
            total += Decimal(str(row.get("amount_total", "0")))
        except (InvalidOperation, TypeError):
            result.unreadable_amounts += 1
    return total


def our_balance(user) -> Decimal:
    """What the customer holds with us, across every insurance bucket.

    All three, not just the free one: a deposit that is held for an auction or
    locked against a debt is still the customer's money and still corresponds
    to something Odoo recorded.
    """
    return sum(
        (
            account_for(user, kind).balance
            for kind in (
                AccountKind.INSURANCE_FREE,
                AccountKind.INSURANCE_HELD,
                AccountKind.INSURANCE_LOCKED,
            )
        ),
        start=ZERO,
    )


def check_customer(link: CustomerLink) -> BalanceCheck:
    """Compare one customer's balance with Odoo's, and record the result.

    Always writes a row, agreement or not. A comparison that only records
    disagreements cannot tell "we checked and it matched" from "we never
    checked", which is the distinction the whole exercise depends on.
    """
    theirs = compute_their_balance(link.odoo_customer_id)
    ours = our_balance(link.user)
    difference = ours - theirs.total

    note_parts = []
    if theirs.unknown_states:
        note_parts.append(
            "حالات أودو غير معروفة لم تُحسب: "
            + "، ".join(
                f"{state}×{count}" for state, count in theirs.unknown_states.items()
            )
        )
    if theirs.unreadable_amounts:
        note_parts.append(f"{theirs.unreadable_amounts} مبلغاً غير قابل للقراءة")
    if not theirs.is_complete:
        note_parts.append("الرقم ناقص — لا يصلح للمقارنة وحده")

    check = BalanceCheck.objects.create(
        user=link.user,
        ours=ours,
        theirs=theirs.total,
        difference=difference,
        method=METHOD,
        detail={
            "odoo_customer_id": link.odoo_customer_id,
            "subscriptions": str(theirs.subscriptions),
            "refunds": str(theirs.refunds),
            "unknown_states": theirs.unknown_states,
            "unreadable_amounts": theirs.unreadable_amounts,
            "complete": theirs.is_complete,
            "note": " · ".join(note_parts),
        },
    )
    log.info(
        "balance check: user %s ours %s theirs %s diff %s (complete=%s)",
        link.user_id,
        ours,
        theirs.total,
        difference,
        theirs.is_complete,
    )
    return check


def open_differences():
    """Checks that disagreed and have not been resolved by a person."""
    return BalanceCheck.objects.filter(resolved_at__isnull=True).exclude(difference=ZERO)
