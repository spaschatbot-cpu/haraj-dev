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

from celery import shared_task

from apps.core.locks import single_instance

from .verification import verify_ledger

log = logging.getLogger(__name__)


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
