"""The auction calendar — starting what is due and ending what is over.

⚠️ **Nothing here is on a schedule.** The task is defined and tested; putting
it on a beat is a separate, deliberate decision per environment (Article 5-2).
In v1 one cron that nobody decided to enable issued 38 unintended invoices.

The task holds a single-instance lock (Article 5-1). Two workers activating
the same auction is not a cosmetic race: it is two "auction started" moments,
and downstream that becomes two settlements.

On time zones: the comparison is UTC against UTC. Operators enter Riyadh wall
clocks, `apps.core.time.from_display` converts them once on the way in, and
this task never converts anything — which is why a tick at 21:00 UTC starts
the auction an operator scheduled for midnight Riyadh, on the following Saudi
day, without anyone writing a date-arithmetic line (Article 3-1).
"""

from __future__ import annotations

import logging

from celery import shared_task
from django.utils import timezone

from apps.core.locks import single_instance

from . import services

log = logging.getLogger(__name__)

LOCK_NAME = "auctions.run_calendar"


@shared_task(name=LOCK_NAME)
def run_calendar(now=None) -> dict:
    """Activate what has started, end what has finished. One minute apart.

    Activation runs before ending, on purpose: an auction whose whole window
    passed while the worker was down goes `scheduled → live → ended` in this
    single tick, instead of sitting live until the next one and accepting a
    bid it should not have.
    """
    now = now or timezone.now()

    with single_instance(LOCK_NAME) as acquired:
        if not acquired:
            return {"skipped": "another instance holds the lock"}

        started = services.activate_due(now)
        ended = services.end_due(now)

        result = {"started": started, "ended": ended}
        if started or ended:
            log.info("auctions.run_calendar: %s", result)
        return result
