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
from apps.money import services as money
from apps.money import verification
from apps.money.models import ZERO, AccountKind, Entry, HoldState

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


@console_page("console:money-ledger")
def ledger(request):
    """Find a customer, by phone or by name, and see what they hold with us.

    Typing a full phone number redirects to that person's page. It is the
    overwhelmingly common case — support is holding a phone call — and making
    them read a one-row result table first is a click nobody would defend. A
    redirect rather than a render, so the address bar ends up holding a link
    that can be pasted into a ticket.

    The list itself shows **only customers who have money with us**, because the
    question this screen answers is always about a balance. A search that
    returns every account ever registered buries the four people the operator
    could have meant.
    """
    query = (request.GET.get("q") or "").strip()

    exact = find_by_phone(query) if query else None
    if exact is not None:
        return redirect("console:money-customer", pk=exact.pk)

    rows = (
        User.objects.filter(accounts__kind__in=AccountKind.customer_owned())
        .exclude(accounts__balance=ZERO)
        .distinct()
    )
    if query:
        rows = rows.filter(
            Q(full_name__icontains=query)
            | Q(company__name__icontains=query)
            | Q(phone__contains=query)
        )

    # The total is annotated rather than read per row: a list of forty customers
    # that asks the database four times each is the shape of a screen that gets
    # slower every month until somebody notices it in production.
    rows = rows.annotate(
        held_total=Sum(
            "accounts__balance",
            filter=Q(accounts__kind__in=AccountKind.customer_owned()),
        ),
        active_holds=Count(
            "holds", filter=Q(holds__state=HoldState.ACTIVE), distinct=True
        ),
    ).order_by("-held_total", "phone")

    page = Paginator(rows, PAGE_SIZE).get_page(request.GET.get("page"))
    return render(
        request,
        "console/money_ledger.html",
        {"page": page, "q": query, "searched": bool(query)},
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

    return render(
        request,
        "console/money_customer.html",
        {
            "ledger": data,
            "page": Paginator(entries, PAGE_SIZE).get_page(request.GET.get("page")),
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
