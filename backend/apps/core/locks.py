"""One instance of a scheduled job at a time (Article 5-1).

Built on PostgreSQL advisory locks rather than a key in a cache, for one
reason that matters more than any other: **the lock is held by the database
connection, so it is released when the process dies.** A cache-based lock with
a timeout has to guess how long the job might take, and every wrong guess is
either a job that cannot restart after a crash or two copies running at once.

The database is already a hard dependency of every task here, so this adds
nothing to deploy and nothing to keep alive.
"""

from __future__ import annotations

import hashlib
import logging
from contextlib import contextmanager

from django.db import connection

log = logging.getLogger(__name__)


def _lock_key(name: str) -> int:
    """A stable 63-bit key for a job name.

    Advisory locks are numbers, not strings, and the number has to be the same
    in every process and across restarts — so it is derived from the name
    rather than assigned by hand, where two jobs would eventually collide.
    """
    digest = hashlib.sha256(name.encode()).digest()
    return int.from_bytes(digest[:8], "big") & 0x7FFF_FFFF_FFFF_FFFF


@contextmanager
def single_instance(name: str):
    """Run the block only if no other process holds this job's lock.

    Yields True when the lock was taken and the caller should do the work, and
    False when another copy already has it. It does **not** raise on
    contention: a scheduled job finding its predecessor still running is
    normal, and a task that errors on a normal condition trains people to
    ignore its alerts.

    Scope is the database *session*, so the same connection can take the same
    lock again and will succeed. That is the right behaviour here — what is
    being prevented is a second worker process, not a nested call — but it
    means a test for contention has to hold the lock from another connection
    to prove anything.

        with single_instance("odoo.retry_failed") as acquired:
            if not acquired:
                return
            ...
    """
    key = _lock_key(name)
    with connection.cursor() as cursor:
        cursor.execute("SELECT pg_try_advisory_lock(%s)", [key])
        acquired = cursor.fetchone()[0]

    if not acquired:
        log.info("lock: %s is held elsewhere, standing down", name)
        yield False
        return

    try:
        yield True
    finally:
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_advisory_unlock(%s)", [key])
        log.debug("lock: released %s", name)
