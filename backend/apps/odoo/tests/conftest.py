"""Fixtures for the Odoo boundary tests."""

import json
import time

import pytest

WEBHOOK_URL = "/webhooks/odoo/"
SECRET = "test-webhook-secret"


@pytest.fixture(autouse=True)
def odoo_settings(settings):
    settings.ODOO_WEBHOOK_SECRET = SECRET
    settings.ODOO_DB = "haraj_prod"
    settings.ODOO_ENABLED = False
    return settings


@pytest.fixture
def signed():
    """Build a correctly signed request body and its headers."""

    # The stamp is a string on the wire, and it stays a string here: the
    # no-float guard reads this tree, and a `float` in a signature it cannot
    # tell from a riyal is a guard people learn to route around.
    def build(payload: dict, *, secret: str = SECRET, timestamp: str | None = None):
        from apps.odoo.signing import expected_signature

        body = json.dumps(payload).encode()
        stamp = timestamp if timestamp is not None else str(time.time())
        return body, {
            "HTTP_X_ODOO_SIGNATURE": expected_signature(body, stamp, secret),
            "HTTP_X_ODOO_TIMESTAMP": stamp,
            "content_type": "application/json",
        }

    return build


@pytest.fixture
def post_webhook(client, signed):
    """POST a correctly signed payload to the webhook."""

    def send(payload: dict, **kwargs):
        body, headers = signed(payload, **kwargs)
        content_type = headers.pop("content_type")
        return client.post(WEBHOOK_URL, data=body, content_type=content_type, **headers)

    return send
