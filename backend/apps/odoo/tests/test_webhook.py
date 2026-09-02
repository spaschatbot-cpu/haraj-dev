"""T201–T205 — the inbound boundary.

The rule being tested throughout: **nothing is ever dropped**. Every path
through this view ends with a row in the table, including the paths that
answer with an error.
"""

import json
import time
from unittest import mock

import pytest
from django.core.cache import cache

from apps.odoo.models import InboundMessage, InboundState
from apps.odoo.tests.conftest import SECRET, WEBHOOK_URL

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def clear_rate_limit():
    cache.clear()
    yield
    cache.clear()


# ---------------------------------------------------------------------------
# T201 — store and answer, nothing else
# ---------------------------------------------------------------------------


class TestStoreAndAcknowledge:
    def test_a_signed_message_is_stored_and_acknowledged(self, post_webhook):
        response = post_webhook(
            {"event": "payment.posted", "db": "haraj_prod", "delivery_id": "D/1"}
        )

        assert response.status_code == 200
        message = InboundMessage.objects.get(delivery_id="D/1")
        assert message.state == InboundState.RECEIVED
        assert message.event == "payment.posted"

    def test_it_answers_200_even_when_every_processor_is_broken(self, post_webhook):
        """The test this task exists for.

        Odoo must never be told to retry because *our* interpretation failed.
        In v1 a parse error on arrival meant the message was gone; here the
        view does not call the processor at all, so a processor that raises on
        sight cannot affect the answer.
        """
        with mock.patch(
            "apps.odoo.views._store", wraps=InboundMessage.objects.create
        ) as store:
            with mock.patch.dict(
                "sys.modules",
                {"apps.odoo.processing": mock.Mock(side_effect=RuntimeError("boom"))},
            ):
                response = post_webhook({"event": "x", "delivery_id": "D/2"})

        assert response.status_code == 200
        assert store.called or InboundMessage.objects.filter(delivery_id="D/2").exists()

    def test_the_view_does_not_import_or_call_processing(self):
        """Enforced by reading the source, because a helpful refactor that adds
        `process(message)` here would pass every behavioural test above while
        undoing Article 2-1."""
        from pathlib import Path

        from apps.odoo import views

        source = Path(views.__file__).read_text(encoding="utf-8")
        assert "processing" not in source.replace(
            "no synchronous call into processing", ""
        ), "views.py must not reach into the processing layer"

    def test_the_raw_body_is_kept_verbatim(self, post_webhook):
        payload = {"event": "payment.posted", "delivery_id": "D/3", "amount": "10000.50"}

        post_webhook(payload)

        message = InboundMessage.objects.get(delivery_id="D/3")
        assert json.loads(message.raw_body) == payload

    def test_the_signature_is_not_stored_beside_the_body(self, post_webhook):
        """Keeping a verified digest next to the bytes it signs hands anyone
        who can read this table a working sample to attack the secret with."""
        post_webhook({"event": "x", "delivery_id": "D/4"})

        message = InboundMessage.objects.get(delivery_id="D/4")
        assert "X-Odoo-Signature" not in message.headers

    def test_a_get_request_is_refused(self, client):
        assert client.get(WEBHOOK_URL).status_code == 405


# ---------------------------------------------------------------------------
# T202 — signature and time window
# ---------------------------------------------------------------------------


class TestSignature:
    def test_a_valid_signature_is_accepted(self, post_webhook):
        assert post_webhook({"event": "x", "delivery_id": "S/1"}).status_code == 200

    def test_a_wrong_signature_is_401_and_still_stored(self, post_webhook):
        """C8. Rejecting is not enough — a burst of these is the only sign that
        a secret was rotated on one side, and there is nothing to look at if
        they were thrown away."""
        response = post_webhook(
            {"event": "x", "delivery_id": "S/2"}, secret="the-wrong-secret"
        )

        assert response.status_code == 401
        stored = InboundMessage.objects.filter(
            state=InboundState.REJECTED_SIGNATURE
        ).first()
        assert stored is not None
        assert "التوقيع لا يطابق" in stored.note

    def test_an_expired_timestamp_is_401_and_still_stored(self, post_webhook):
        response = post_webhook(
            {"event": "x", "delivery_id": "S/3"}, timestamp=str(time.time() - 3600)
        )

        assert response.status_code == 401
        stored = InboundMessage.objects.filter(
            state=InboundState.REJECTED_SIGNATURE
        ).first()
        assert stored is not None
        assert "خارج النافذة" in stored.note

    def test_a_missing_signature_is_401_and_still_stored(self, client):
        response = client.post(WEBHOOK_URL, data=b"{}", content_type="application/json")

        assert response.status_code == 401
        assert (
            InboundMessage.objects.filter(state=InboundState.REJECTED_SIGNATURE).count()
            == 1
        )

    def test_a_replayed_body_with_a_fresh_timestamp_fails(self, signed, client):
        """The timestamp is inside the signed material. Swapping it invalidates
        the digest, so a captured message cannot be given a new lease of life.
        """
        body, headers = signed({"event": "x", "delivery_id": "S/4"})
        headers["HTTP_X_ODOO_TIMESTAMP"] = str(time.time())
        content_type = headers.pop("content_type")

        response = client.post(
            WEBHOOK_URL, data=body, content_type=content_type, **headers
        )

        assert response.status_code == 401

    def test_an_environment_with_no_secret_refuses_everything(
        self, settings, post_webhook
    ):
        """A boundary with no secret that accepts anything is worse than one
        that is down."""
        settings.ODOO_WEBHOOK_SECRET = ""

        response = post_webhook({"event": "x", "delivery_id": "S/5"})

        assert response.status_code == 401
        assert "لا يوجد سرّ" in InboundMessage.objects.first().note


# ---------------------------------------------------------------------------
# T203 — unique on delivery, never on subject
# ---------------------------------------------------------------------------


class TestDeliveryIdentity:
    def test_three_messages_about_one_invoice_are_three_rows(self, post_webhook):
        """C2, and the exact v1 failure.

        A dedup rule keyed on the invoice swallowed the third webhook — the
        only one carrying the invoice link — so a settled deposit went on
        showing as refundable.
        """
        for delivery in ("D/10", "D/11", "D/12"):
            post_webhook(
                {
                    "event": "invoice.updated",
                    "delivery_id": delivery,
                    "invoice_id": "INV/2026/0001",
                }
            )

        rows = InboundMessage.objects.filter(subject_ref="INV/2026/0001")
        assert rows.count() == 3
        assert {r.delivery_id for r in rows} == {"D/10", "D/11", "D/12"}

    def test_the_same_delivery_twice_is_one_row_and_still_200(self, post_webhook):
        """Odoo retries when our acknowledgement is slow. That is ordinary
        traffic, not an error."""
        first = post_webhook({"event": "x", "delivery_id": "D/13"})
        second = post_webhook({"event": "x", "delivery_id": "D/13"})

        assert first.status_code == second.status_code == 200
        assert InboundMessage.objects.filter(delivery_id="D/13").count() == 1

    def test_a_delivery_id_is_derived_when_odoo_sends_none(self, post_webhook):
        post_webhook(
            {
                "event": "invoice.posted",
                "invoice_id": "INV/2026/0002",
                "timestamp": "2026-09-02T10:00:00",
            }
        )

        message = InboundMessage.objects.get(subject_ref="INV/2026/0002")
        assert message.delivery_id == "invoice.posted:INV/2026/0002:2026-09-02T10:00:00"

    def test_two_undeterminable_messages_are_kept_apart_not_collapsed(self, post_webhook):
        """When nothing identifies the delivery, the field stays blank and the
        partial unique index lets both rows exist. A duplicate row is a
        nuisance; a collapsed one loses a message."""
        post_webhook({"amount": "1"})
        post_webhook({"amount": "2"})

        assert InboundMessage.objects.filter(delivery_id="").count() == 2


# ---------------------------------------------------------------------------
# T204 — the staging database cannot reach production
# ---------------------------------------------------------------------------


class TestEnvironmentIsolation:
    def test_a_message_from_another_odoo_database_is_stored_and_ignored(
        self, post_webhook
    ):
        """In v1 two invented invoices from a test environment blocked a real
        bidder for three and a half hours."""
        response = post_webhook(
            {"event": "invoice.posted", "delivery_id": "D/20", "db": "haraj_staging"}
        )

        assert response.status_code == 200
        message = InboundMessage.objects.get(delivery_id="D/20")
        assert message.state == InboundState.IGNORED
        assert "haraj_staging" in message.note
        assert message.resulting_transaction is None

    def test_the_reason_is_always_written_down(self, post_webhook):
        post_webhook({"event": "x", "delivery_id": "D/21", "db": "haraj_staging"})

        assert InboundMessage.objects.get(delivery_id="D/21").note != ""

    def test_our_own_database_passes(self, post_webhook):
        post_webhook({"event": "x", "delivery_id": "D/22", "db": "haraj_prod"})

        assert (
            InboundMessage.objects.get(delivery_id="D/22").state == InboundState.RECEIVED
        )

    def test_a_message_without_a_database_field_is_not_rejected(self, post_webhook):
        """Not every sender labels its database. Absence is not evidence of a
        foreign origin (Article 2-4), and the signature already proved origin.
        """
        post_webhook({"event": "x", "delivery_id": "D/23"})

        assert (
            InboundMessage.objects.get(delivery_id="D/23").state == InboundState.RECEIVED
        )


# ---------------------------------------------------------------------------
# T205 — the rate ceiling
# ---------------------------------------------------------------------------


class TestRateLimit:
    def test_traffic_within_the_ceiling_is_never_dropped(self, post_webhook):
        for index in range(20):
            assert post_webhook({"delivery_id": f"R/{index}"}).status_code == 200

        assert InboundMessage.objects.count() == 20

    def test_going_over_the_ceiling_returns_429(self, post_webhook, settings):
        with mock.patch("apps.odoo.views.RATE_LIMIT_PER_MINUTE", 3):
            for index in range(3):
                assert post_webhook({"delivery_id": f"L/{index}"}).status_code == 200

            response = post_webhook({"delivery_id": "L/over"})

        assert response.status_code == 429
        assert not InboundMessage.objects.filter(delivery_id="L/over").exists()


# ---------------------------------------------------------------------------
# Unparseable bodies
# ---------------------------------------------------------------------------


class TestUnparseableBody:
    def test_a_signed_but_broken_body_is_stored_as_failed_and_answered_200(
        self, signed, client
    ):
        """Signed by someone holding our secret, so the fault is ours to fix.
        Stored as `failed` so it can be replayed once the parser is right —
        and answered 200, because retrying will not make it parseable."""
        from apps.odoo.signing import expected_signature

        body = b"{not json at all"
        stamp = str(time.time())
        response = client.post(
            WEBHOOK_URL,
            data=body,
            content_type="application/json",
            HTTP_X_ODOO_SIGNATURE=expected_signature(body, stamp, SECRET),
            HTTP_X_ODOO_TIMESTAMP=stamp,
        )

        assert response.status_code == 200
        message = InboundMessage.objects.get()
        assert message.state == InboundState.FAILED
        assert message.raw_body == "{not json at all"
        assert message.note != ""
