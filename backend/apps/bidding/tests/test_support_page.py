"""T503 — the page that answers «ليه ما يقدرش يزايد؟».

The acceptance criterion is a person: a support agent answers a real case in
under a minute. What that means in a test is that one request, carrying only
what the customer says on the phone — their number — returns the reason and the
money as it stood, with nothing else to look up and nothing to reconstruct.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from django.urls import reverse

from apps.bidding import services
from apps.bidding.models import RefusalReason

pytestmark = pytest.mark.django_db

PAGE = "/support/why-no-bid/"


@pytest.fixture
def refused(verified, vehicle):
    """One real refusal to look up: a bidder with no deposit."""
    with pytest.raises(services.BidRefused):
        services.place_bid(user=verified, vehicle=vehicle, amount=Decimal("30000.00"))
    return verified


def test_the_page_is_where_the_url_says(client, staff):
    assert reverse("bidding:why-no-bid") == PAGE


def test_a_stranger_cannot_read_a_customers_money(client, refused):
    response = client.get(PAGE, {"phone": refused.phone})

    assert response.status_code == 302
    assert "insurance" not in response.content.decode(errors="ignore")


def test_a_customer_cannot_read_the_support_page(client, refused):
    client.force_login(refused)

    assert client.get(PAGE).status_code == 302


def test_one_phone_number_gives_support_the_whole_answer(client, staff, refused):
    client.force_login(staff)

    body = client.get(PAGE, {"phone": refused.phone}).content.decode()

    assert RefusalReason.NO_DEPOSIT.label in body
    assert "تحتاج تأميناً متاحاً قدره 10000.00 ريال" in body
    assert refused.full_name in body


def test_the_number_can_be_typed_the_way_a_customer_says_it(client, staff, refused):
    """`0501000001` and `+966501000001` are the same person to everyone but a
    regex, and a support box that only accepts the stored format is a support
    box that gets used once."""
    client.force_login(staff)
    local = "0" + refused.phone[3:]

    body = client.get(PAGE, {"phone": local}).content.decode()

    assert RefusalReason.NO_DEPOSIT.label in body


def test_an_unknown_number_says_so_rather_than_showing_nothing(client, staff):
    client.force_login(staff)

    body = client.get(PAGE, {"phone": "966599999999"}).content.decode()

    assert "لا يوجد عميل بهذا الرقم" in body


def test_the_page_shows_the_money_of_the_moment_not_of_now(client, staff, refused):
    """The whole point of the snapshot: the balance moved, the answer did not."""
    from apps.money import services as money

    money.deposit_insurance(
        user=refused, amount=Decimal("10000.00"), source="cash", reference="dep/late"
    )
    client.force_login(staff)

    body = client.get(PAGE, {"phone": refused.phone}).content.decode()

    assert "وقت الرفض" in body
    assert '<td class="money">0.00</td>' in body
