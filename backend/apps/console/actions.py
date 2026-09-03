"""الأفعال المالية الإدارية — the three that move money by a decision. T811.

Confiscate a deposit, grant a bidding exception, correct a transaction. They are
the only writes to the ledger anywhere in this console, and each one is three
lines: read the subject, call the service, redirect. Every rule they obey lives
in `apps.money.services` and `apps.bidding.services`, which is I3 stated as
architecture rather than as intent — `ops/checks/money_single_writer.py` fails
the build if a screen ever posts an entry itself.

Why this is not the deposits ledger with buttons added
------------------------------------------------------
It would have been less code. The ledger (T810) is read-only **by
construction**, and a test fails if a `<form method="post">` appears on it: it is
the screen support opens while a customer is on the phone, and the value of a
screen people trust to tell them what happened comes partly from its inability
to change anything. Moving money is a different intent and is a different page
you go to on purpose.

Why every one of them demands a reason
--------------------------------------
Spec 009 §"قواعد المال في اللوحة" 2, and the v1 incident behind it: a
confiscation and a hand-edited exception were indistinguishable afterwards from
a bug, because neither left a sentence saying who decided and why. Here the
reason is mandatory at the service, not at the form — a screen-level check is a
check the next caller does not inherit.

Three trusts, not one
---------------------
The page is guarded by `money.act`; granting an exception additionally needs
`money.exception`, which only the owner holds. That is why the exception form
renders only for whoever may actually use it: an exception is the single action
that lets somebody bid with no money standing behind them, and v1's one
"finance" flag meant anybody who could read a balance could also grant one.
"""

from __future__ import annotations

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from apps.accounts.models import User
from apps.accounts.services import display_name
from apps.bidding import services as bidding
from apps.core.permissions import Capability, can
from apps.money import services as money
from apps.money.models import Hold, HoldReason, HoldState, Transaction

from .views import console_page

#: Transactions offered for correction. Deep history is corrected through the
#: ledger and a shell, deliberately: a mistake worth undoing is nearly always
#: recent, and a page offering to reverse anything ever posted is a page where
#: the wrong row is one mis-click away.
RECENT_TRANSACTIONS = 25


def _reason(request) -> str:
    """The typed justification, or "" — the callers let the service refuse it.

    Not validated here on purpose. A screen that produces its own "reason
    required" message has a second copy of the rule, and the day the service
    starts demanding something more of a reason, the screen still passes what it
    always passed.
    """
    return (request.POST.get("reason") or "").strip()


@console_page("console:money-actions")
def actions(request, pk: int):
    """One customer's holds and recent movements, each with what may be done to it.

    The subject is always shown beside the action — the hold's amount, what it
    secures, the transaction's memo — because "confiscate hold 4102" is not a
    sentence anybody can check before pressing it.
    """
    customer = get_object_or_404(User, pk=pk)

    holds = (
        Hold.objects.filter(owner=customer, state=HoldState.ACTIVE)
        .select_related("auction", "invoice")
        .order_by("-created_at")
    )
    movements = (
        Transaction.objects.filter(entries__owner=customer)
        .distinct()
        .order_by("-occurred_at", "-id")[:RECENT_TRANSACTIONS]
    )

    return render(
        request,
        "console/money_actions.html",
        {
            "customer": customer,
            "name": display_name(customer),
            "holds": holds,
            "movements": movements,
            # Rendered only for whoever may use it. A form that always produces
            # a 403 teaches its reader that the console is broken.
            "may_grant_exception": can(request.user, Capability.MONEY_EXCEPTION),
            "dues": HoldReason.DUES,
        },
    )


@console_page("console:money-confiscate")
def confiscate(request, pk: int):
    """Take a held deposit permanently. `money.services.confiscate` decides."""
    hold = get_object_or_404(Hold.objects.select_related("owner"), pk=pk)

    if request.method != "POST":
        return redirect("console:money-actions", pk=hold.owner_id)

    try:
        money.confiscate(hold, reason=_reason(request), by=request.user)
    except Exception as refusal:
        # The service's own sentence. It already distinguishes "no reason
        # given" from "this hold is not active", and rewording either here
        # would lose that.
        messages.error(request, str(refusal))
    else:
        messages.success(request, f"صودر الحجز {hold.pk} ({hold.amount}).")

    return redirect("console:money-actions", pk=hold.owner_id)


@console_page("console:money-exception")
def grant_exception(request, pk: int):
    """Let one debtor bid despite one unpaid invoice. No money moves.

    The lock stays exactly where it is and the debt stays a debt; what changes
    is that eligibility stops counting this invoice against the bidder. Which is
    why it is `money.exception` and not `money.act`: it is the only action that
    puts somebody in an auction with nothing standing behind their bid.
    """
    hold = get_object_or_404(Hold.objects.select_related("owner", "invoice"), pk=pk)

    if request.method != "POST":
        return redirect("console:money-actions", pk=hold.owner_id)

    try:
        bidding.grant_bidding_exception(hold=hold, note=_reason(request), by=request.user)
    except Exception as refusal:
        messages.error(request, str(refusal))
    else:
        messages.success(request, f"مُنح استثناء على القفل {hold.pk}.")

    return redirect("console:money-actions", pk=hold.owner_id)


@console_page("console:money-correct")
def correct(request, pk: int):
    """Reverse a transaction by a named decision. The original is untouched."""
    txn = get_object_or_404(Transaction, pk=pk)
    owner = _owner_of(txn)
    back = (
        redirect("console:money-ledger")
        if owner is None
        else redirect("console:money-actions", pk=owner)
    )

    if request.method != "POST":
        return back

    try:
        reversal = money.correct(txn, reason=_reason(request), by=request.user)
    except Exception as refusal:
        messages.error(request, str(refusal))
    else:
        messages.success(request, f"صُحّحت الحركة {txn.pk} بالقيد العاكس {reversal.pk}.")

    return back


def _owner_of(txn: Transaction) -> int | None:
    """Whose page this transaction belongs on.

    A transaction spans accounts and can touch a platform bucket as well as a
    customer's, so this reads the first customer-owned entry rather than
    assuming there is exactly one party. A movement with no customer leg at all
    — suspense to revenue, say — has no customer page, and the caller is sent
    back to the search rather than to a customer id of nothing.
    """
    entry = txn.entries.filter(owner__isnull=False).first()
    return None if entry is None else entry.owner_id


__all__ = ["actions", "confiscate", "correct", "grant_exception"]
