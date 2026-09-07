"""T814/T219 — the inbox, and the button that is not allowed to be a shortcut.

The acceptance criterion is an equality: *a replay from the screen is exactly a
replay by the cron*. It is held here two ways, because either alone can pass
while the thing it protects is broken:

* **behaviourally** — two identical messages, one replayed through the button
  and one through `retry_failed`, must leave rows that agree field for field;
* **structurally** — `apps.console.inbox` may take exactly one name out of
  `apps.odoo.processing`, and that name is `process`. The behavioural test
  passes on the day somebody adds a screen-only branch for the one event they
  are debugging, as long as that branch happens to agree on the message the
  test uses. The import guard does not.

The rest of the file is about what the screen must *not* offer: editing a
payload until it parses, or setting a state by hand. Both turn a record of what
somebody sent us into a guess about what they meant.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.core.models import AuditLog
from apps.core.permissions import Capability, Role, can
from apps.money import services as money
from apps.money.models import AccountKind, Transaction
from apps.odoo.models import CustomerLink, InboundMessage, InboundState
from apps.odoo.tasks import retry_failed

pytestmark = pytest.mark.django_db

TEN_K = Decimal("10000.00")


@pytest.fixture
def operator(client) -> User:
    """Finance holds `odoo.inbox`; a replay can credit a customer's account."""
    user = User.objects.create_user(
        phone="966500000061", full_name="موظف مالية", password="x"
    )
    user.is_staff = True
    user.console_role = Role.FINANCE
    user.save(update_fields=["is_staff", "console_role"])
    client.force_login(user)
    return user


@pytest.fixture
def linked_customer(db) -> User:
    customer = User.objects.create_user(
        phone="966555555701", full_name="عميل مربوط", password="x"
    )
    CustomerLink.objects.create(
        user=customer, odoo_customer_id="ODOO-701", is_primary=True
    )
    return customer


def failing_message(delivery_id: str) -> InboundMessage:
    """A payment message with no payment id. Fails now and on every retry.

    Its note carries no identifier of its own, which is what lets two clones of
    it be compared for exact equality after travelling different paths.
    """
    return InboundMessage.objects.create(
        source="odoo",
        event="payment.posted",
        odoo_database="haraj_prod",
        delivery_id=delivery_id,
        subject_ref="",
        payload={"amount": "10000.00", "customer_id": "ODOO-701"},
        raw_body='{"amount": "10000.00", "customer_id": "ODOO-701"}',
        state=InboundState.FAILED,
        note="أول محاولة فشلت",
        attempts=1,
        processed_at=timezone.now() - timezone.timedelta(days=1),
    )


def valid_payment(delivery_id: str, payment_id: str) -> InboundMessage:
    """A payment that will credit a linked customer once it is re-interpreted."""
    payload = {
        "payment_id": payment_id,
        "amount": "10000.00",
        "customer_id": "ODOO-701",
    }
    return InboundMessage.objects.create(
        source="odoo",
        event="payment.posted",
        odoo_database="haraj_prod",
        delivery_id=delivery_id,
        subject_ref=payment_id,
        payload=payload,
        raw_body=str(payload),
        state=InboundState.FAILED,
        note="أودو لم تكن متاحة",
        attempts=1,
        processed_at=timezone.now() - timezone.timedelta(days=1),
    )


def press_replay(client, message: InboundMessage):
    return client.post(reverse("console:odoo-replay", args=[message.pk]))


# ---------------------------------------------------------------------------
# The acceptance criterion, both halves
# ---------------------------------------------------------------------------


def test_the_button_and_the_cron_leave_identical_rows(client, operator):
    """One message down each path. The rows they leave must agree, field by field."""
    # One at a time, and the cron first: `retry_failed` sweeps every due
    # message, so a hand-replayed row that is still failed would be picked up by
    # the same sweep and counted twice. Each message here travels exactly one
    # path, which is what the comparison is about.
    by_cron = failing_message("D-cron")
    retry_failed()

    by_hand = failing_message("D-hand")
    press_replay(client, by_hand)

    by_hand.refresh_from_db()
    by_cron.refresh_from_db()

    compared = ("state", "note", "attempts", "resulting_transaction_id")
    assert {f: getattr(by_hand, f) for f in compared} == {
        f: getattr(by_cron, f) for f in compared
    }
    assert by_hand.state == InboundState.FAILED
    assert by_hand.attempts == 2


def test_the_screen_borrows_the_processor_and_writes_no_interpretation(operator):
    """Exactly one name out of `apps.odoo.processing`, and it is `process`.

    The behavioural test above passes on the day somebody adds a screen-only
    branch for the event they happen to be debugging. This one does not.
    """
    import ast
    import pathlib

    source = pathlib.Path("apps/console/inbox.py").read_text(encoding="utf-8")
    tree = ast.parse(source)

    imported = [
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module == "apps.odoo.processing"
        for alias in node.names
    ]
    assert imported == ["process"], imported

    # And no handler of its own hiding under another name.
    forbidden = ("_interpret", "_handle_payment", "_handle_invoice", "_handle_refund")
    assert not [name for name in forbidden if name in source]


def test_a_replay_that_succeeds_credits_exactly_what_the_processor_would(
    client, operator, linked_customer
):
    money.account_for(linked_customer, AccountKind.INSURANCE_FREE)
    message = valid_payment("D-ok", "PAY-701")

    press_replay(client, message)
    message.refresh_from_db()

    assert message.state == InboundState.PROCESSED
    assert message.resulting_transaction is not None
    assert money.account_for(linked_customer, AccountKind.INSURANCE_FREE).balance == TEN_K


def test_pressing_it_twice_credits_once(client, operator, linked_customer):
    """Idempotency survives the button, because the button is the same code.

    The key is derived from the payment's identity in Odoo, so a second pass
    posts nothing. An operator who does not see the first click land presses
    again — that is not a hypothetical, it is what people do.
    """
    message = valid_payment("D-twice", "PAY-702")

    press_replay(client, message)
    press_replay(client, message)

    assert Transaction.objects.filter(idempotency_key__contains="PAY-702").count() == 1
    assert money.account_for(linked_customer, AccountKind.INSURANCE_FREE).balance == TEN_K


def test_a_replay_records_who_pressed_it_and_what_the_row_was(
    client, operator, linked_customer
):
    """A replay can credit money, so what the row looked like before is part of it."""
    message = valid_payment("D-audit", "PAY-703")

    press_replay(client, message)

    entry = AuditLog.objects.get(action="console.replay_odoo_message")
    assert entry.actor_id == operator.pk
    assert entry.entity_id == str(message.pk)
    assert entry.before["state"] == InboundState.FAILED
    assert entry.after["state"] == InboundState.PROCESSED
    assert entry.before["resulting_transaction_id"] is None
    assert entry.after["resulting_transaction_id"] is not None


# ---------------------------------------------------------------------------
# What the screen refuses to be
# ---------------------------------------------------------------------------


def test_a_get_does_not_replay(client, operator, linked_customer):
    """A link that credits money is a link a crawler or a back button can press."""
    message = valid_payment("D-get", "PAY-704")

    client.get(reverse("console:odoo-replay", args=[message.pk]))
    message.refresh_from_db()

    assert message.state == InboundState.FAILED
    assert Transaction.objects.filter(idempotency_key__contains="PAY-704").count() == 0


def test_the_message_page_offers_no_way_to_edit_or_relabel_it(client, operator):
    """Editing a payload until it parses turns evidence into a guess."""
    message = failing_message("D-readonly")

    body = client.get(reverse("console:odoo-message", args=[message.pk])).content.decode()

    assert "إعادة تشغيل هذه الرسالة" in body
    assert "<textarea" not in body
    assert 'name="payload"' not in body
    assert 'name="state"' not in body


def test_the_raw_body_is_shown_exactly_as_it_arrived(client, operator):
    message = failing_message("D-raw")

    body = client.get(reverse("console:odoo-message", args=[message.pk])).content.decode()

    assert "النصّ كما وصل" in body
    assert "10000.00" in body


def test_a_processed_message_offers_no_replay_button(client, operator, linked_customer):
    """Nothing to retry, and a button that says otherwise invites a double credit."""
    message = valid_payment("D-done", "PAY-705")
    press_replay(client, message)

    body = client.get(reverse("console:odoo-message", args=[message.pk])).content.decode()

    assert "إعادة تشغيل هذه الرسالة" not in body


# ---------------------------------------------------------------------------
# The list
# ---------------------------------------------------------------------------


def test_the_list_shows_every_state_and_filters_to_the_failed(client, operator):
    failing_message("D-list-1")
    processed = failing_message("D-list-2")
    InboundMessage.objects.filter(pk=processed.pk).update(
        state=InboundState.PROCESSED, note="تمّت"
    )

    everything = client.get(reverse("console:odoo-inbox")).content.decode()
    assert everything.count("payment.posted") == 2

    only_failed = client.get(
        reverse("console:odoo-inbox"), {"state": InboundState.FAILED}
    ).content.decode()
    assert only_failed.count("payment.posted") == 1


def test_the_list_finds_a_message_by_its_subject(client, operator, linked_customer):
    valid_payment("D-search", "PAY-706")
    failing_message("D-search-other")

    body = client.get(reverse("console:odoo-inbox"), {"q": "PAY-706"}).content.decode()

    assert body.count("payment.posted") == 1
    assert "PAY-706" in body


# ---------------------------------------------------------------------------
# Who may open it
# ---------------------------------------------------------------------------


def test_the_inbox_needs_its_own_capability(client, operator, linked_customer):
    """Support may read a customer's ledger and still not replay a message.

    Replaying moves money; reading does not. v1 collapsed both into one
    "finance" flag, so whoever could read a balance could also move it.
    """
    agent = User.objects.create_user(phone="966500000062", full_name="دعم", password="x")
    agent.is_staff = True
    agent.console_role = Role.SUPPORT
    agent.save(update_fields=["is_staff", "console_role"])

    assert can(agent, Capability.MONEY_VIEW)
    assert not can(agent, Capability.ODOO_INBOX)

    message = valid_payment("D-guard", "PAY-707")
    client.force_login(agent)

    assert client.get(reverse("console:odoo-inbox")).status_code == 403
    assert press_replay(client, message).status_code == 403

    message.refresh_from_db()
    assert message.state == InboundState.FAILED
