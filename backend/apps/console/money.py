"""دفتر التأمينات — one customer's money, as the ledger itself has it. T810.

Two screens and no buttons. This file writes nothing, calls no service that
writes, and offers no form: the deposits ledger is where somebody goes to
*understand* a balance, and the moment a screen like it grows an "adjust"
control it stops being the place people trust to tell them what happened
(T811 is where money moves, with a name and a reason attached).

The numbers
-----------
Every figure here is read, never assembled:

* the buckets come from `apps.money.services.wallet_snapshot` — the same
  function that renders the customer's own wallet in the app, so support and
  the customer are never looking at two different totals while on the phone
  with each other;
* the lines come from `apps.money.services.statement_entries`, which is the
  `Entry` rows themselves rather than a summary computed beside them;
* and the totals are checked against `apps.money.verification`, by calling it,
  not by reimplementing it.

That last one is T810's acceptance criterion, and the reason it is written this
way is worth stating plainly. A screen that re-derives what it displays is a
second derivation, and a second derivation can be right on the day the first
one is wrong — which reads, to whoever is looking at it, as the ledger being
fine. So when the stored balance and the entries disagree, this screen says so
**on the screen, above the number**, and does not quietly show either one as
though it were the answer.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from django.core.paginator import Paginator
from django.db.models import Count, Q, Sum
from django.shortcuts import redirect, render

from apps.accounts.models import User
from apps.accounts.services import display_name, find_by_phone
from apps.core.arabic import search_q
from apps.core.permissions import Capability, can
from apps.money import services as money
from apps.money import verification
from apps.money.models import ZERO, AccountKind, Entry, HoldState

from .exports import export, wants_export
from .paging import paged, pager
from .views import console_page

#: Ledger lines per page. A customer with a year of activity has hundreds, and
#: the question that brings somebody here is nearly always about the last few.
PAGE_SIZE = 50


@dataclass(frozen=True)
class CustomerLedger:
    """One customer's money: the pots, the claims on them, and the movements."""

    customer: User
    name: str
    snapshot: money.WalletSnapshot
    findings: list[verification.Finding]

    @property
    def is_sound(self) -> bool:
        """Whether every number on this page is one the ledger stands behind."""
        return not self.findings


def ledger_for(customer: User) -> CustomerLedger:
    """Assemble the page's data — by asking, in every case, rather than computing."""
    return CustomerLedger(
        customer=customer,
        name=display_name(customer),
        snapshot=money.wallet_snapshot(customer),
        findings=verification.verify_customer(customer),
    )


#: دلاءُ التأمين الثلاثة — «إجمالي التأمين» في تقرير v1 مجموعُها.
INSURANCE = (
    AccountKind.INSURANCE_FREE,
    AccountKind.INSURANCE_HELD,
    AccountKind.INSURANCE_LOCKED,
)


def wallet_rows(*, text: str = "", low: str = "", high: str = "", order: str = ""):
    """العملاءُ وأرصدتُهم — **مجموعةً من الدفتر لا من عمود**.

    شاشةُ v1 المقابلة (`/analytics/insurance-report`) تكتب مصدرَها على نفسها:
    «إجمالي مبالغ التأمين 9,390,004.00 — `SUM(total_insurance_paid)`». وذلك
    العمود بالحرف أحدُ الثلاثة التي وجدها جرد T302 في `userss` أعمدةَ رصيدٍ
    مشتقّةً كلُّها تُهمَل. وهنا يُجمَع من `money.Account` عند كل عرض.

    **والمجموعُ من `customer_owned` لا من دلاء التأمين وحدها** — وهو أوسع
    بدلوٍ واحد (`wallet`). وقِيس على الإنتاج في ١٨ سبتمبر ٢٠٢٦: **لا حساب
    `wallet` واحداً** (١٬٦٠٨ متاح · ٣١٧ محجوز · ١٣ مقفول · صفر محفظة)، فالرقمان
    متساويان اليوم. والأوسعُ مقصود: ريالٌ في دلوٍ لا تجمعه الشاشةُ هو ريالٌ
    يختفي من تقرير المال يوم يُستعمل ذلك الدلو.
    """
    rows = (
        User.objects.filter(is_staff=False)
        .annotate(
            # المجموعُ يُحسب في القاعدة لا صفّاً صفّاً: قائمةٌ من أربعين عميلاً
            # تسأل القاعدةَ أربع مرّاتٍ لكلٍّ منهم هي شاشةٌ تبطؤ كلّ شهر.
            held_total=Sum(
                "accounts__balance",
                filter=Q(accounts__kind__in=AccountKind.customer_owned()),
            ),
            active_holds=Count(
                "holds", filter=Q(holds__state=HoldState.ACTIVE), distinct=True
            ),
        )
        .filter(held_total__gt=ZERO)
    )

    text = (text or "").strip()
    if text:
        rows = rows.filter(search_q(text, "full_name", "company__name", "phone"))

    for value, field in ((low, "held_total__gte"), (high, "held_total__lte")):
        value = (value or "").strip()
        if value.replace(".", "", 1).isdigit():
            rows = rows.filter(**{field: Decimal(value)})

    # «الأعلى أوّلاً» افتراضاً كما في v1: السؤالُ الذي تُفتح الشاشة لأجله «من
    # عنده مالٌ عندنا» لا «من سجّل أوّلاً».
    return rows.order_by("held_total" if order == "asc" else "-held_total", "id")


@console_page("console:money-ledger")
def ledger(request):
    """سجلُّ المحفظة: من يحمل رصيداً عندنا، وكم، وكم منه محجوز.

    **شاشةٌ واحدةٌ بعد أن كانت اثنتين** (قرار المالك، ١٨ سبتمبر ٢٠٢٦): كانت
    «سجل المحفظة» تسرد من يحمل رصيداً، و«تقرير المحفظة» تسرد **القائمةَ
    نفسَها** بمرشّحِ مبلغٍ وبطاقتَي مجموع. والفرقُ بين استعلاميهما دلوٌ واحد
    (`wallet`) **لا حسابَ له على الإنتاج إطلاقاً** — أي أن الشاشتين كانتا
    تعرضان الشيءَ نفسَه بمرشِّحاتٍ مختلفة، وكلُّ واحدةٍ فيها ميزةٌ تنقص الأخرى.
    فاجتمعت المزايا في واحدة.

    وكتابةُ رقم جوّالٍ كاملٍ تذهب مباشرةً إلى دفتر صاحبه: الحالةُ الغالبة أن
    الموظّف على الهاتف، وإجبارُه على قراءة جدولٍ من صفٍّ واحدٍ نقرةٌ لا يدافع
    عنها أحد. وتحويلٌ لا عرضٌ، ليبقى في شريط العنوان رابطٌ يُلصَق في تذكرة.
    """
    query = (request.GET.get("q") or "").strip()

    exact = find_by_phone(query) if query else None
    if exact is not None:
        return redirect("console:money-customer", pk=exact.pk)

    rows = wallet_rows(
        text=query,
        low=request.GET.get("low", ""),
        high=request.GET.get("high", ""),
        order=request.GET.get("order", ""),
    )

    if wants_export(request):
        return export(
            rows,
            name="المحفظة",
            headers=[
                "المعرّف",
                "العميل",
                "الجوال",
                "مجموع رصيده",
                "حجوزات قائمة",
            ],
            cell=lambda u: [
                u.pk,
                display_name(u),
                u.phone,
                u.held_total,
                u.active_holds,
            ],
        )

    page = paged(request, rows)
    return render(
        request,
        "console/money_ledger.html",
        {
            "page": page,
            "pager": pager(request, page, "عميلاً"),
            "customers": rows.count(),
            "total": rows.aggregate(t=Sum("held_total"))["t"] or ZERO,
            "q": query,
            "low": request.GET.get("low", ""),
            "high": request.GET.get("high", ""),
            "order": request.GET.get("order", ""),
            "searched": bool(query),
        },
    )


@console_page("console:money-customer")
def customer_ledger(request, pk: int):
    """One customer: the buckets, the holds with their reasons, and the lines.

    A missing customer is answered with the search screen and a sentence, not a
    404 page: the id in the url came from a link or from somebody's clipboard,
    and "there is no such customer" is more useful next to the box that finds
    one.
    """
    customer = User.objects.filter(pk=pk).first()
    if customer is None:
        return render(
            request,
            "console/money_ledger.html",
            {"page": None, "q": "", "searched": True, "missing": pk},
        )

    data = ledger_for(customer)
    entries = money.statement_entries(customer)

    if wants_export(request):
        return export(
            entries,
            name=f"ledger-{customer.pk}",
            headers=["التاريخ", "الدلو", "الحركة", "المبلغ", "البيان"],
            cell=lambda e: [
                e.transaction.occurred_at,
                e.account.get_kind_display(),
                e.transaction.get_kind_display(),
                e.amount,
                e.transaction.memo,
            ],
        )

    return render(
        request,
        "console/money_customer.html",
        {
            "ledger": data,
            "page": Paginator(entries, PAGE_SIZE).get_page(request.GET.get("page")),
            # A link, never a button. This page stays read-only by construction
            # (T810) and the actions live on their own screen (T811); what is
            # offered here is the way there, and only to somebody who could use
            # it — a link that answers 403 reads as a broken console.
            "may_act": can(request.user, Capability.MONEY_ACT),
        },
    )


def derived_total(customer: User) -> Decimal:
    """What this customer's entries add up to, ignoring every cached balance.

    Used by the tests that hold this file to its acceptance criterion, and by
    nothing that renders: a screen showing a number nobody has checked against
    the stored one is exactly the ambiguity `verify_customer` exists to expose.
    """
    total = (
        Entry.objects.filter(
            owner=customer, account__kind__in=AccountKind.customer_owned()
        ).aggregate(total=Sum("amount"))["total"]
        or ZERO
    )
    return total


__all__ = ["CustomerLedger", "customer_ledger", "derived_total", "ledger", "ledger_for"]
