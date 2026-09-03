"""صندوق وارد أودو — every message as it arrived, and one button. T814/T219.

Two screens: the messages with their states, and one message with its raw body
laid out unparsed. The only write is **إعادة تشغيل**, and the whole design of
this file is contained in what that button does:

    process(message)

The same call, on the same object, that `apps.odoo.tasks.retry_failed` makes.
Not a copy of it, not a variant that skips the signature step because a human
asked this time, and not a second interpretation written for the screen. That
is T814's acceptance criterion stated as code, and
`test_the_button_and_the_cron_leave_identical_rows` holds it by running one
message through each path and comparing the rows they leave behind, field by
field.

Why the criterion is worth a test rather than a comment
------------------------------------------------------
A replay button is written second, usually months later, by somebody who has
the message in front of them and knows what it should do. That is exactly the
situation in which a shortcut looks reasonable — "it already passed the
signature check when it arrived", "we know this one is a payment" — and each
shortcut makes the button's path diverge from the automatic one. Then the two
disagree about a message and nobody can say which behaviour is the real one.

What the screen deliberately cannot do
--------------------------------------
It cannot edit a payload, and it cannot set a state by hand. A message is a
record of what somebody sent us (Article 2-2); editing it until it parses turns
evidence into a guess, and marking one `processed` because it looks fine
produces a message with no transaction behind it — which is a payment that
exists in Odoo and nowhere here.
"""

from __future__ import annotations

import json

from django.contrib import messages as flash
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render

from apps.core import audit
from apps.odoo.models import InboundMessage, InboundState
from apps.odoo.processing import process
from apps.odoo.tasks import MAX_ATTEMPTS

from .views import console_page

#: Rows per page. The inbox is read newest-first when something is wrong, and
#: what is wrong is nearly always at the top.
PAGE_SIZE = 50

#: The fields whose before/after a replay is recorded with. A replay can credit
#: money, so what the message looked like beforehand is part of the record.
AUDITED = ("state", "attempts", "note", "resulting_transaction_id")


@console_page("console:odoo-inbox")
def inbox(request):
    """Every message, filterable by state, source and subject.

    `failed` is one click, because it is the reason anybody opens this screen —
    but it is not the default view. A screen that opens showing only failures
    teaches its reader that failures are all it holds, and the question "did
    that payment ever reach us at all?" is answered by the `processed` and
    `ignored` rows.
    """
    rows = InboundMessage.objects.all().select_related("resulting_transaction")

    state = request.GET.get("state", "")
    if state in InboundState.values:
        rows = rows.filter(state=state)

    source = (request.GET.get("source") or "").strip()
    if source:
        rows = rows.filter(source=source)

    search = (request.GET.get("q") or "").strip()
    if search:
        rows = rows.filter(subject_ref__icontains=search)

    return render(
        request,
        "console/odoo_inbox.html",
        {
            "page": Paginator(rows, PAGE_SIZE).get_page(request.GET.get("page")),
            "states": InboundState.choices,
            "state": state,
            "source": source,
            "q": search,
            "sources": sorted(
                InboundMessage.objects.values_list("source", flat=True).distinct()
            ),
            "failed": InboundState.FAILED,
        },
    )


@console_page("console:odoo-message")
def message(request, pk: int):
    """One message, with the body shown as it arrived.

    `raw_body` first and the parsed payload beneath it. When the two disagree —
    which is the case that brings somebody here — the raw text is the evidence
    and the parse is our reading of it, so the evidence goes on top.
    """
    row = get_object_or_404(
        InboundMessage.objects.select_related("resulting_transaction"), pk=pk
    )

    return render(
        request,
        "console/odoo_message.html",
        {
            # Named `row` and not `message`: Django's own `messages` context
            # variable is one letter away, and a template that shadows the flash
            # messages with the object it is displaying loses every warning the
            # replay button produces.
            "row": row,
            "pretty": json.dumps(row.payload, ensure_ascii=False, indent=2),
            "headers": json.dumps(row.headers, ensure_ascii=False, indent=2),
            "exhausted": row.attempts >= MAX_ATTEMPTS,
        },
    )


@console_page("console:odoo-replay")
def replay(request, pk: int):
    """Run one message through the automatic path again, by hand.

    No reason field, unlike every other write in this console. That is not an
    oversight: a replay does not decide anything. It asks the same code the cron
    asks, and whatever it concludes is the message's own doing — while a
    confiscation or a correction is somebody's judgement and needs its
    justification stored beside it. What is recorded here is *who pressed it*
    and what the row looked like before, which is what a later dispute about a
    duplicate credit actually asks.
    """
    row = get_object_or_404(InboundMessage, pk=pk)

    if request.method != "POST":
        return redirect("console:odoo-message", pk=pk)

    before = audit.snapshot(row, AUDITED)
    process(row)

    audit.record(
        action="console.replay_odoo_message",
        entity=row,
        actor=request.user,
        before=before,
        after=audit.snapshot(row, AUDITED),
        note=row.note,
    )

    if row.state == InboundState.FAILED:
        # The processor's own sentence, unchanged. It already says what it could
        # not do, and rewording it here would lose the distinction between "we
        # do not know this event" and "the customer has no Odoo link".
        flash.error(request, f"ما زالت فاشلة: {row.note}")
    else:
        flash.success(request, f"صارت «{InboundState(row.state).label}».")

    return redirect("console:odoo-message", pk=pk)


__all__ = ["inbox", "message", "replay"]
