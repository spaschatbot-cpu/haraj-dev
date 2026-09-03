"""Background work on the ledger.

⚠️ **Nothing here is on a schedule.** The task below is defined and tested, and
putting it on a real beat needs explicit, per-environment permission
(Article 5-2). Defining it is not scheduling it — and that distinction is the
whole reason `apps/auctions/tasks.py` and `apps/odoo/tasks.py` are shaped this
way too.

It holds a single-instance lock (Article 5-1). No exceptions.
"""

from __future__ import annotations

import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from apps.core.locks import single_instance
from apps.odoo.models import InboundMessage, InboundState

from .inbound import INTERPRETED_SOURCE, interpret
from .verification import verify_ledger

log = logging.getLogger(__name__)

#: Give up automatic retries after this many and leave the message for a person.
#: Same figure and same reasoning as `apps.odoo.tasks.MAX_ATTEMPTS`: a message
#: that has failed six times is not failing for a reason a seventh attempt fixes.
MAX_ATTEMPTS = 6

#: Backoff in minutes by attempt number: ~1m, 5m, 25m, 2h, 10h, then daily.
BACKOFF_MINUTES = [1, 5, 25, 125, 625, 1440]


@shared_task(name="money.verify_ledger")
def verify() -> dict:
    """Re-derive everything the ledger claims, and report what disagrees.

    Article 3-4 asks for a periodic job behind every derived column, and this
    is the one behind all of them: `Account.balance` is a cache moved by delta,
    and `Invoice.amount_paid` and `Invoice.state` are derived too. Until now
    `verify_ledger` was called from the test suite and a management command and
    from nothing that could run after a deploy — so a drift in production had
    nothing watching for it, and the first report would have been a customer.

    Read-only by construction: `verification` imports nothing from `services`,
    so a bug in the writing path shows up here instead of being confirmed by it.
    """
    with single_instance("money.verify_ledger") as acquired:
        if not acquired:
            log.info("money.verify_ledger: another instance holds the lock")
            return {"ran": False, "findings": 0}

        findings = verify_ledger()
        for finding in findings:
            log.error("verify_ledger: %s", finding)
        if not findings:
            log.info("verify_ledger: clean")
        return {"ran": True, "findings": len(findings)}


# ---------------------------------------------------------------------------
# The payment gateway's own retry queue
# ---------------------------------------------------------------------------


def next_attempt_after(attempts: int) -> timedelta:
    index = min(attempts, len(BACKOFF_MINUTES) - 1)
    return timedelta(minutes=BACKOFF_MINUTES[index])


def due_gateway_messages(now=None) -> list[InboundMessage]:
    """Gateway messages that failed, whose backoff has elapsed, with attempts left.

    This queue exists because until now there was none. `InboundMessage` is
    shared, and `apps.odoo.tasks.due_messages` filters on Odoo's source — for
    the right reason (T913) — so a card payment that failed to apply was looked
    at by nothing afterwards. `failed` is supposed to mean "try again", and for
    one of the two boundaries it meant "forgotten".

    ``source`` is in this filter for the mirror-image reason it is in that one:
    the boundaries read different field names and neither may interpret the
    other's bodies. `rejected_signature` is excluded by construction — it is a
    separate state precisely so that no queue ever offers an unsigned body.
    """
    now = now or timezone.now()
    candidates = InboundMessage.objects.filter(
        source=INTERPRETED_SOURCE,
        state=InboundState.FAILED,
        attempts__lt=MAX_ATTEMPTS,
    ).order_by("received_at")

    due = []
    for message in candidates:
        last = message.processed_at or message.received_at
        if last + next_attempt_after(message.attempts) <= now:
            due.append(message)
    return due


@shared_task(name="money.retry_failed_gateway")
def retry_failed_gateway() -> dict:
    """Re-interpret gateway messages that failed, with backoff.

    Retrying is safe for the same reason the Odoo side's is: attribution comes
    from the stored intent, and the ledger key from the payment's own id, so a
    message interpreted twice credits once.

    Nothing here decides *what* a message means — `inbound.interpret` does, and
    it is the same call the console button makes. Two callers, one
    interpretation (Article 4-5).
    """
    with single_instance("money.retry_failed_gateway") as acquired:
        if not acquired:
            return {"skipped": "another instance holds the lock"}

        results = {"attempted": 0, "processed": 0, "still_failing": 0}
        for message in due_gateway_messages():
            results["attempted"] += 1
            interpret(message)
            if message.state == InboundState.FAILED:
                results["still_failing"] += 1
            else:
                results["processed"] += 1

        log.info("money.retry_failed_gateway: %s", results)
        return results
