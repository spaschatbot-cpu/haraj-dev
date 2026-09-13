"""شاشة صحة المال — the four ways money can be wrong, on one page. T813/T220.

Four questions, and they are genuinely different questions:

1. **Does the ledger agree with itself?** `verify_ledger` re-derives every
   balance from the entries and reports each disagreement.
2. **Does it agree with Odoo?** Odoo is the book of record (Article 2-5), and
   green on question 1 says nothing about question 2 — v1 could prove its own
   consistency while a customer bid with 10,000 that Odoo's ledger closed at
   zero. That comparison is `BalanceCheck`, from phase 003.
3. **Is there money here that belongs to nobody yet?** The suspense bucket:
   real riyals that arrived and have not been attributed to a customer.
4. **Is anything waiting on a person?** Money that arrived and was not
   understood, a channel that is refusing messages, a customer silently barred
   from bidding by their own open refund request. None of these is an
   inconsistency — the ledger is perfectly right about all of them — and that
   is exactly why they were invisible: three of v1's nine checks, and the three
   it had that this screen did not.

Why they are not added up
-------------------------
There is no headline "total missing" on this screen, and that is a decision
rather than an omission. A 500 drift in the cache and a 500 difference against
Odoo may well be the *same* 500 seen from two sides; adding them reports 1,000
missing when 500 is missing. The screen shows four counts and four lists, and
lets the person reading decide what one incident it is.

Which is the same rule as the one governing every figure here, and the task
states it as a warning rather than a requirement: **لا يُبالَغ في أي مبلغ
معروض**. A health screen that overstates a shortfall once is a health screen
nobody opens again — and the two ways to overstate one are both closed here.
The notes are recomputed on every render, so a fixed cause is gone from the page
without anyone marking it resolved; and the suspense total is the bucket's own
balance, never the sum of the receipts that have ever landed in it.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from django.db.models import Sum
from django.shortcuts import render

from apps.money.models import ZERO, Account, AccountKind, Entry, TransactionKind
from apps.money.verification import Finding, verify_ledger
from apps.odoo.reconciliation import open_differences

from .views import console_page

#: Suspense movements shown. The bucket is meant to be nearly empty; a page of
#: fifty lines here is itself the finding.
MOVEMENT_LIMIT = 50


@dataclass(frozen=True)
class Suspense:
    """Money that arrived and has not been given an owner.

    :attr:`balance` is the account's balance and nothing else. It is emphatically
    not the sum of the receipts below it: `attribute` moves money out of the
    pool without settling any particular receipt, so a per-receipt "still
    outstanding" column would be a number this codebase does not know. The
    movements are shown as movements — what came in and what went out — and the
    one authoritative figure is the pool.
    """

    balance: Decimal
    derived: Decimal
    movements: list[Entry]

    @property
    def agrees(self) -> bool:
        """Whether the stored pool matches its own entries."""
        return self.balance == self.derived


def suspense_state() -> Suspense:
    """What is sitting unattributed, and the movements that put it there."""
    account = Account.objects.filter(
        kind=AccountKind.SUSPENSE, owner__isnull=True
    ).first()
    if account is None:
        return Suspense(balance=ZERO, derived=ZERO, movements=[])

    derived = (
        Entry.objects.filter(account=account).aggregate(total=Sum("amount"))["total"]
        or ZERO
    )

    movements = list(
        Entry.objects.filter(
            account=account,
            transaction__kind__in=(
                TransactionKind.UNATTRIBUTED_RECEIPT,
                TransactionKind.ATTRIBUTION,
            ),
        ).select_related("transaction")[:MOVEMENT_LIMIT]
    )
    return Suspense(balance=account.balance, derived=derived, movements=movements)


# ---------------------------------------------------------------------------
# ٤) وما ينتظر إنساناً — الفحوصُ الثلاثة التي كانت غائبة
# ---------------------------------------------------------------------------
#
# صحّةُ المحفظة في v1 تسعةُ فحوص، وهنا كانت أربعةً في `verify_ledger` وحالةُ
# المعلَّق. والفرقُ ليس تسعةً ناقص خمسة:
#
# * **`shadow_drift`** هو `check_cached_balances` باسمٍ آخر، و**`odoo_balance_mismatch`**
#   هو `open_differences` أعلاه. موجودان.
# * **`overdebited`** و**`unclassified_void`** و**`live_with_void_reason`**
#   **مستحيلةٌ بنيويّاً هنا ولا تُبنى**: السحبُ الزائد يمنعه قيدُ
#   `customer_buckets_never_go_negative` في القاعدة لا فحصٌ ليليّ، ولا «إلغاء»
#   في هذا الدفتر أصلاً — التصحيحُ قيدٌ عاكسٌ يفرض `reason` و`by` (`correct`).
#   وفحصٌ عن حالةٍ لا يمكن بلوغها هو سطرٌ أخضرُ دائماً، وسطرٌ كهذا يُعلّم القارئ
#   ألّا يقرأ.
# * والباقي **ثلاثة**، وكلُّها عن مالٍ أو عميلٍ **ينتظر يداً** لا عن تناقضٍ في
#   الدفتر — ولذلك مكانُها هنا لا في `verification.py`: تلك الوحدة تقرأ جداول
#   الدفتر وحدها عمداً، وهذه تسأل صندوقَ الوارد والصادر وطلباتِ الاسترداد.
#
# وتُحسب عند كل رندرة كغيرها. لا جدولَ بلاغات — للسبب المكتوب في `health_report`.


@dataclass(frozen=True)
class ChannelFailure:
    """عطلٌ في قناةٍ مع طرفٍ خارجيّ، بصرف النظر عن أيّ الجدولين جاء منه."""

    subject: str
    state: str
    reason: str


@dataclass(frozen=True)
class Waiting:
    """مالٌ أو عميلٌ متوقّفٌ على قرارِ إنسان، بثلاثة أوجه."""

    #: رسائلُ مالٍ وصلت ولم تُفهم، وما زالت في طابور الإعادة.
    stuck_inbound: list
    #: أدلّةُ عطلٍ في القناة: توقيعٌ لم يُقبَل، أو رسالةٌ هُجرت إلى أودو.
    channel_failures: list
    #: عملاءُ طلبُ استردادهم القائم يمنعهم من المزايدة بوديعتهم نفسها.
    blocked_bidders: list

    @property
    def total(self) -> int:
        return (
            len(self.stuck_inbound)
            + len(self.channel_failures)
            + len(self.blocked_bidders)
        )


def waiting_state() -> Waiting:
    """الثلاثةُ، محسوبةً الآن.

    **والعدُّ بالموضوع لا بالرسالة** في الوارد العالق — كما يعدّ v1
    (`inbox_unresolved` «يُعدّ بالدفعة لا بالرسالة»). أودو يرسل ثلاث رسائل عن
    دفعةٍ واحدة، فعدُّها ثلاثاً يجعل عطلاً واحداً يبدو ثلاثة أعطال، ولوحةٌ
    تضاعف مشاكلها ثلاثاً لا تُقرأ.
    """
    from apps.money.models import RefundRequest, RefundRequestState
    from apps.odoo.models import InboundMessage, InboundState, OutboxMessage, OutboxState

    stuck = (
        InboundMessage.objects.filter(state=InboundState.FAILED)
        .order_by("subject_ref", "-received_at")
        .distinct("subject_ref")
    )

    # صفّان مسطَّحان لا نموذجان: الوارد والصادر جدولان مختلفان بأسماء حقولٍ
    # مختلفة، وقالبٌ يسأل كليهما عن `last_error` يرمي على أحدهما. والتسويةُ
    # هنا حيث تُعرف الحقول، لا في القالب بسلسلةِ `default` تُخفي الفرق.
    failures = [
        ChannelFailure(
            subject=str(m),
            state=m.get_state_display(),
            reason=m.note or "توقيع لم يُقبل",
        )
        for m in InboundMessage.objects.filter(
            state=InboundState.REJECTED_SIGNATURE
        ).order_by("-received_at")[:MOVEMENT_LIMIT]
    ] + [
        ChannelFailure(
            subject=str(m),
            state=m.get_state_display(),
            reason=m.last_error or "هُجرت بلا سبب مكتوب",
        )
        for m in OutboxMessage.objects.filter(state=OutboxState.ABANDONED).order_by(
            "-created_at"
        )[:MOVEMENT_LIMIT]
    ]

    # طلبٌ قائمٌ يحجز وديعةً: `spendable = free − refund_pending` في البوّابة،
    # فصاحبُه يقرأ رصيده عشرةَ آلاف ويُرفض عند المزايدة بلا أن يفهم لماذا. وهو
    # حجبٌ صامتٌ لا عطلٌ في الدفتر — ولذلك يُعرض ولا يُعدّ خللاً.
    blocked = list(
        RefundRequest.objects.filter(state__in=RefundRequestState.open_states())
        .select_related("user")
        .order_by("-created_at")[:MOVEMENT_LIMIT]
    )

    return Waiting(
        stuck_inbound=list(stuck[:MOVEMENT_LIMIT]),
        channel_failures=failures,
        blocked_bidders=blocked,
    )


@dataclass(frozen=True)
class Health:
    """Everything the screen renders, gathered once."""

    findings: list[Finding]
    differences: list
    suspense: Suspense
    waiting: Waiting

    @property
    def is_clean(self) -> bool:
        """No note of any of the four kinds. The only state worth a green line."""
        return (
            not self.findings
            and not self.differences
            and self.suspense.balance == ZERO
            and self.suspense.agrees
            and self.waiting.total == 0
        )


def health_report() -> Health:
    """The four checks, run now.

    Run rather than looked up, which is what makes a note close by itself. There
    is no table of open findings anywhere in this codebase — a stored note has
    to be closed by somebody noticing that it should be, and in v1 the
    reconciliation queue's oldest entries were all things that had been fixed
    months earlier and never ticked off, so the queue was ignored wholesale.
    """
    return Health(
        findings=verify_ledger(),
        differences=list(open_differences()),
        suspense=suspense_state(),
        waiting=waiting_state(),
    )


@console_page("console:money-health")
def health(request):
    return render(request, "console/money_health.html", {"report": health_report()})


__all__ = [
    "ChannelFailure",
    "Health",
    "Suspense",
    "Waiting",
    "health",
    "health_report",
    "suspense_state",
    "waiting_state",
]
