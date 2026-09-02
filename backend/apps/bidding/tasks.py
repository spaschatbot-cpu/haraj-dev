"""Settling auctions that have ended. T512.

⚠️ **Nothing here is on a schedule.** The task is defined and tested; putting it
on a beat is a separate, deliberate decision per environment (Article 5-2). In
v1 one cron nobody decided to enable issued 38 unintended invoices — and this
task moves more money than that one did.

Every task here holds a single-instance lock (Article 5-1), and on this path the
lock is doing more than tidiness. `settle_auction` is idempotent, so two copies
would not double-release a hold — but they *would* interleave: one computes the
set of competitors, the other resolves a car, and the first then releases a
deposit belonging to somebody who became a competitor half a millisecond ago.
That is the v1 failure re-created by concurrency instead of by logic.

The lock is per **job**, not per auction. A finer lock would let two workers
settle two auctions at once, which is true and tempting and wrong: a bidder can
be in both, and their hold is one row.
"""

from __future__ import annotations

import logging

from celery import shared_task
from django.utils import timezone

from apps.auctions.models import Auction
from apps.auctions.states import AuctionState
from apps.core.locks import single_instance

from . import settlement

log = logging.getLogger(__name__)

LOCK_NAME = "bidding.settle_ended_auctions"


@shared_task(name=LOCK_NAME)
def settle_ended_auctions(now=None) -> dict:
    """Settle every auction that has ended and is not settled yet.

    Auctions are taken oldest first, so a backlog after an outage is worked
    through in the order the auctions actually closed — a bidder in two of them
    sees their deposits resolve in the order they expect.

    One auction failing does not stop the rest. A settlement that raises leaves
    that auction untouched for the next run (each car is its own transaction),
    and the failure is logged with the auction's id rather than swallowed — a
    task that reports success while skipping an auction is how money quietly
    stays held.
    """
    now = now or timezone.now()

    with single_instance(LOCK_NAME) as acquired:
        if not acquired:
            return {"skipped": "another instance holds the lock"}

        due = list(
            Auction.objects.filter(state=AuctionState.ENDED, ends_at__lte=now).order_by(
                "ends_at"
            )
        )

        settled: list[int] = []
        failed: list[int] = []

        for auction in due:
            try:
                report = settlement.settle_auction(auction, now=now)
                settled.append(auction.pk)
                log.info(
                    "settled auction %s: %s cars, %s holds released",
                    auction.pk,
                    len(report.vehicles),
                    len(report.released),
                )
            except Exception:
                # Named, not swallowed. The next run picks it up again, and
                # each car settles in its own transaction so a failure halfway
                # leaves the earlier cars correctly resolved.
                failed.append(auction.pk)
                log.exception("settling auction %s failed", auction.pk)

        result = {"settled": settled, "failed": failed}
        if settled or failed:
            log.info("bidding.settle_ended_auctions: %s", result)
        return result


@shared_task(name="bidding.close_settled_auctions")
def close_settled_auctions(now=None) -> dict:
    """Mark as settled the auctions whose cars are all resolved.

    Separate from the task above because the two answer different questions.
    Settling decides cars and money; closing is the bookkeeping that says the
    auction is finished — and an auction with a car still waiting on its owner's
    decision is *settled as far as it can be* but not finished. Merging them
    would mean either closing early or re-running the whole settlement every
    time an owner finally answers.
    """
    now = now or timezone.now()

    with single_instance("bidding.close_settled_auctions") as acquired:
        if not acquired:
            return {"skipped": "another instance holds the lock"}

        closed: list[int] = []
        waiting: list[int] = []

        for auction in Auction.objects.filter(state=AuctionState.ENDED).order_by(
            "ends_at"
        ):
            try:
                settlement.close_auction(auction, now=now)
                closed.append(auction.pk)
            except ValueError:
                # Still has an unresolved car. Normal, not an error: an owner
                # deciding on a car takes as long as it takes.
                waiting.append(auction.pk)

        result = {"closed": closed, "waiting": waiting}
        if closed:
            log.info("bidding.close_settled_auctions: %s", result)
        return result
