"""T210, T215 — retrying failures, and never twice at once.

Neither task in `apps.odoo.tasks` is on a schedule, and the last test here
asserts that. Article 5-2: a scheduled job that writes to a real accounting
system needs explicit permission *before* it is scheduled, and in v1 the cron
that issued 38 unintended invoices was itself correct — what was missing was
anyone deciding it should run.
"""

import threading
from datetime import timedelta
from decimal import Decimal

import pytest
from django.conf import settings
from django.db import connections
from django.utils import timezone

from apps.core.locks import single_instance
from apps.money import services
from apps.money.models import AccountKind
from apps.odoo.models import CustomerLink, InboundMessage, InboundState
from apps.odoo.tasks import (
    MAX_ATTEMPTS,
    abandon_exhausted,
    due_messages,
    next_attempt_after,
    retry_failed,
)

pytestmark = pytest.mark.django_db(transaction=True)

TEN_K = Decimal("10000.00")


@pytest.fixture
def customer(django_user_model):
    return django_user_model.objects.create_user(
        phone="966500000001", full_name="عميل", password="x"
    )


def failed_message(payload: dict, *, attempts: int = 0, age_minutes: int = 60):
    message = InboundMessage.objects.create(
        source="odoo",
        event=payload.get("event", "payment.posted"),
        delivery_id=payload.get("delivery_id", ""),
        payload=payload,
        state=InboundState.FAILED,
        note="فشلت سابقاً",
        attempts=attempts,
    )
    old = timezone.now() - timedelta(minutes=age_minutes)
    InboundMessage.objects.filter(pk=message.pk).update(received_at=old, processed_at=old)
    message.refresh_from_db()
    return message


# ---------------------------------------------------------------------------
# T210 — retry with backoff
# ---------------------------------------------------------------------------


class TestRetry:
    def test_a_message_fixed_in_the_meantime_processes_without_a_person(self, customer):
        """The point of the whole retry path: the message was stored, the bug
        that stopped it was fixed, and it goes through on its own."""
        message = failed_message(
            {
                "event": "payment.posted",
                "payment_id": "P1",
                "amount": "10000.00",
                "customer_id": "ODOO-1",
            }
        )
        # What was missing: the customer link. Adding it is the "fix".
        CustomerLink.objects.create(
            user=customer, odoo_customer_id="ODOO-1", is_primary=True
        )

        result = retry_failed()

        message.refresh_from_db()
        assert message.state == InboundState.PROCESSED
        assert result["processed"] == 1
        assert services.account_for(customer, AccountKind.INSURANCE_FREE).balance == TEN_K

    def test_a_message_still_broken_stays_failed_and_counts_its_attempt(self):
        message = failed_message(
            {"event": "payment.posted", "amount": "10000.00"}, attempts=1
        )

        retry_failed()

        message.refresh_from_db()
        assert message.state == InboundState.FAILED
        assert message.attempts == 2

    def test_a_message_still_inside_its_backoff_is_not_touched(self):
        """Retrying every minute forever is how a broken integration turns
        into a denial of service against the system it is broken with."""
        message = failed_message(
            {"event": "payment.posted", "amount": "1.00"},
            attempts=3,
            age_minutes=1,
        )

        result = retry_failed()

        message.refresh_from_db()
        assert result["attempted"] == 0
        assert message.attempts == 3

    def test_the_backoff_grows(self):
        assert next_attempt_after(0) < next_attempt_after(1) < next_attempt_after(3)
        assert next_attempt_after(99) == next_attempt_after(len([1, 5, 25, 125, 625]))

    def test_a_message_out_of_attempts_leaves_the_automatic_queue(self):
        exhausted = failed_message(
            {"event": "payment.posted", "amount": "1.00"}, attempts=MAX_ATTEMPTS
        )

        assert exhausted not in due_messages()

    def test_an_exhausted_message_is_flagged_for_a_person_not_marked_ignored(self):
        """It stays `failed`. Nobody decided to ignore it — we ran out of
        automatic attempts, and the note is what tells those two apart."""
        message = failed_message(
            {"event": "payment.posted", "amount": "1.00"}, attempts=MAX_ATTEMPTS
        )

        abandon_exhausted()

        message.refresh_from_db()
        assert message.state == InboundState.FAILED
        assert "مراجعة بشرية" in message.note

    def test_flagging_twice_does_not_repeat_the_note(self):
        message = failed_message(
            {"event": "payment.posted", "amount": "1.00"}, attempts=MAX_ATTEMPTS
        )

        abandon_exhausted()
        abandon_exhausted()

        message.refresh_from_db()
        assert message.note.count("مراجعة بشرية") == 1

    def test_processed_messages_are_never_retried(self, customer):
        message = InboundMessage.objects.create(
            source="odoo",
            event="payment.posted",
            payload={"payment_id": "P9", "amount": "1.00"},
            state=InboundState.PROCESSED,
            note="تمت",
        )

        retry_failed()

        message.refresh_from_db()
        assert message.attempts == 0


# ---------------------------------------------------------------------------
# T215 — one instance at a time
# ---------------------------------------------------------------------------


class TestSingleInstance:
    def test_a_second_caller_stands_down_quietly(self):
        """It returns False rather than raising. A scheduled job finding its
        predecessor still running is normal, and a task that errors on a
        normal condition teaches people to ignore its alerts."""
        outcomes = {}
        started = threading.Event()
        release = threading.Event()

        def holder():
            try:
                with single_instance("test.job") as acquired:
                    outcomes["first"] = acquired
                    started.set()
                    release.wait(timeout=10)
            finally:
                connections.close_all()

        thread = threading.Thread(target=holder)
        thread.start()
        started.wait(timeout=10)

        try:
            with single_instance("test.job") as acquired:
                outcomes["second"] = acquired
        finally:
            release.set()
            thread.join(timeout=10)

        assert outcomes["first"] is True
        assert outcomes["second"] is False

    def test_the_lock_is_released_when_the_block_ends(self):
        with single_instance("test.sequential") as first:
            assert first is True

        with single_instance("test.sequential") as second:
            assert second is True

    def test_the_lock_is_released_even_when_the_block_raises(self):
        with pytest.raises(RuntimeError):
            with single_instance("test.raising") as acquired:
                assert acquired is True
                raise RuntimeError("boom")

        with single_instance("test.raising") as after:
            assert after is True

    def test_different_jobs_do_not_block_each_other(self):
        with single_instance("test.job.a") as a:
            with single_instance("test.job.b") as b:
                assert a is True
                assert b is True

    def test_the_retry_task_stands_down_when_another_process_holds_its_lock(self):
        """The task itself, not just the helper.

        The holder has to be a *different connection*: advisory locks are
        session-scoped and re-entrant, so a call from the same connection
        would take the lock again and prove nothing. Which is the correct
        behaviour — the thing being prevented is a second worker, not a
        nested call.
        """
        outcome = {}
        holding = threading.Event()
        release = threading.Event()

        def holder():
            try:
                with single_instance("odoo.retry_failed") as acquired:
                    outcome["holder_got_it"] = acquired
                    holding.set()
                    release.wait(timeout=10)
            finally:
                connections.close_all()

        thread = threading.Thread(target=holder)
        thread.start()
        holding.wait(timeout=10)

        try:
            result = retry_failed()
        finally:
            release.set()
            thread.join(timeout=10)

        assert outcome["holder_got_it"] is True
        assert "skipped" in result


# ---------------------------------------------------------------------------
# Article 5-2 — nothing here is scheduled
# ---------------------------------------------------------------------------


def test_no_odoo_task_is_on_a_schedule():
    """A defined task is a capability; a scheduled one is a decision.

    In v1 one cron issued 38 unintended invoices. The task was correct — what
    was missing was anyone choosing to run it. This test fails the moment
    somebody adds a beat entry without also removing this assertion, which is
    exactly the moment a person should be asked.
    """
    beat = getattr(settings, "CELERY_BEAT_SCHEDULE", {})
    scheduled = [
        name
        for name, entry in beat.items()
        if "odoo" in str(entry.get("task", "")).lower()
    ]
    assert scheduled == [], (
        f"tasks scheduled without explicit permission: {scheduled}. "
        f"Article 5-2 requires a per-environment decision first."
    )


def test_odoo_is_disabled_by_default():
    """Article 2-6. Nothing reaches a real accounting system unless someone
    turned it on for that environment, deliberately."""
    assert settings.ODOO_ENABLED is False
