"""التسليم إلى بوابة الدفع — ثغرة عقدٍ كانت تُوقف القناتين معاً.

`start_topup` كتب النيّة وأعادها، ولم يقل شيئاً عن **أين يذهب العميل ليدفع**.
فالويب يستطيع إنشاء نيّة ولا يرسل أحداً إلى أي مكان، والفيز 008 كانت ستصطدم
بالجدار نفسه — ثغرةٌ في العقد لا في قناة.

وما تُثبته هذه الاختبارات هو الشكل الذي سُدَّت به، لا مجرّد أنها سُدَّت:

* **العنوان على خادمنا لا على البوابة.** لو كان حقلاً يحمل عنوان البوابة لتغيّر
  معناه يوم تتغيّر البوابة — وكان **على القناتين أن تتغيّرا معه**. هنا التبديل
  تعديلٌ في `apps/money/gateway.py` وحده: لا بناءَ تطبيق، ولا نشرَ موقع.
* **غير المُهيَّأ يرفض ولا يخمّن.** عميلٌ يُرسَل إلى صفحة معطوبة ومعه فلوس أسوأ
  من زرٍّ لا يظهر.
* **ولا شيء يتحرّك هنا.** هذه لافتة طريق؛ الدفتر يتحرّك في `PaymentCallbackView`
  وحدها.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from django.urls import reverse

from apps.money import gateway, services
from apps.money.models import PaymentIntent, PaymentIntentState, Transaction

pytestmark = pytest.mark.django_db

TEMPLATE = "https://pay.example.com/checkout/{reference}?amount={amount}&cur={currency}"


@pytest.fixture
def intent(customer) -> PaymentIntent:
    return services.start_topup(user=customer, client_key="one")


@pytest.fixture
def gateway_on(settings):
    settings.PAYMENT_CHECKOUT_TEMPLATE = TEMPLATE
    return settings


def checkout_url(intent: PaymentIntent) -> str:
    return reverse("money:topup-checkout", args=[intent.reference])


# ---------------------------------------------------------------------------
# The hand-off
# ---------------------------------------------------------------------------


def test_the_intent_tells_the_client_where_to_send_the_customer(
    api_client, customer, intent, gateway_on
):
    """The hole this closes: an intent that said nothing about paying it."""
    api_client.force_authenticate(customer)

    body = api_client.get(reverse("money:topup-detail", args=[intent.reference])).json()

    assert body["checkout_url"].endswith(checkout_url(intent))


def test_the_client_never_sees_the_gateways_address(
    api_client, customer, intent, gateway_on
):
    """A url on our server, always the same shape, whatever the gateway is.

    This is the whole design. A field holding the gateway's own address is a
    field whose meaning changes when the gateway does, and both clients would
    have to change with it — and each would grow a branch for "how do we hand
    off to Moyasar", which is one rule living in three places.
    """
    api_client.force_authenticate(customer)

    body = api_client.get(reverse("money:topup-detail", args=[intent.reference])).json()

    assert "pay.example.com" not in body["checkout_url"]
    assert "/wallet/topups/" in body["checkout_url"]


def test_following_it_redirects_to_the_gateway(api_client, customer, intent, gateway_on):
    api_client.force_authenticate(customer)

    response = api_client.get(checkout_url(intent))

    assert response.status_code == 302
    assert response["Location"].startswith("https://pay.example.com/checkout/")
    assert intent.reference in response["Location"]


def test_the_amount_crosses_as_the_ledgers_own_digits(
    api_client, customer, intent, gateway_on
):
    """Article 3-2 all the way to the gateway.

    The figure is `deposit_amount_for`'s, as a decimal string. Nothing on this
    path turns it into a float — not even on its way out of the platform.
    """
    api_client.force_authenticate(customer)

    location = api_client.get(checkout_url(intent))["Location"]

    assert f"amount={intent.amount}" in location
    assert intent.amount == Decimal("10000.00")


def test_only_the_reference_identifies_the_customer(
    api_client, customer, intent, gateway_on
):
    """The gateway never learns a user id, which is why the intent exists.

    v1 tried to recover the customer from what came back in the return url and
    lost payments doing it. The reference is ours, opaque, and written before
    the customer leaves.
    """
    api_client.force_authenticate(customer)

    location = api_client.get(checkout_url(intent))["Location"]

    assert str(customer.pk) not in location.split(intent.reference)[-1]
    assert customer.phone not in location


# ---------------------------------------------------------------------------
# Refusals — and each is a refusal, not a guess
# ---------------------------------------------------------------------------


def test_an_unconfigured_gateway_refuses_in_arabic(api_client, customer, intent):
    """Off by default, like every other integration in this codebase.

    A customer sent to a broken page with money in their hand is worse than a
    button that is not there.
    """
    api_client.force_authenticate(customer)

    response = api_client.get(checkout_url(intent))

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "checkout_unavailable"
    assert "غير مفعّل" in response.json()["error"]["message"]


def test_an_unconfigured_gateway_offers_no_url_at_all(api_client, customer, intent):
    api_client.force_authenticate(customer)

    body = api_client.get(reverse("money:topup-detail", args=[intent.reference])).json()

    assert body["checkout_url"] == ""


@pytest.mark.parametrize(
    "state",
    [
        PaymentIntentState.SUCCEEDED,
        PaymentIntentState.FAILED,
        PaymentIntentState.CANCELLED,
        PaymentIntentState.EXPIRED,
    ],
)
def test_an_intent_that_is_done_offers_nothing(
    api_client, customer, intent, gateway_on, state
):
    """A button for a succeeded top-up offers to take a second deposit.

    The absence of the control is the correct interface for every one of these,
    and the absence is produced by the server rather than by each client
    remembering to check a state.
    """
    if state == PaymentIntentState.SUCCEEDED:
        # The schema refuses a succeeded intent that names no transaction
        # (`a_succeeded_intent_names_its_transaction`), so the row has to be
        # made the way the real path makes it. A test that worked around the
        # constraint would be testing a state the database cannot hold.
        txn = services.deposit_insurance(
            user=customer, amount=intent.amount, source="card", reference="done"
        )
        PaymentIntent.objects.filter(pk=intent.pk).update(
            state=state, resulting_transaction=txn
        )
    else:
        PaymentIntent.objects.filter(pk=intent.pk).update(state=state)
    api_client.force_authenticate(customer)

    body = api_client.get(reverse("money:topup-detail", args=[intent.reference])).json()
    assert body["checkout_url"] == ""

    response = api_client.get(checkout_url(intent))
    assert response.status_code == 409
    assert "لم تعد قابلة للدفع" in response.json()["error"]["message"]


def test_a_stranger_cannot_reach_another_customers_checkout(
    api_client, customer, other_customer, intent, gateway_on
):
    """Ownership is the queryset's, not a branch in the view."""
    api_client.force_authenticate(other_customer)

    assert api_client.get(checkout_url(intent)).status_code == 404


def test_signing_out_closes_it(api_client, intent, gateway_on):
    assert api_client.get(checkout_url(intent)).status_code in (401, 403)


# ---------------------------------------------------------------------------
# It is a signpost, not a payment
# ---------------------------------------------------------------------------


def test_the_hand_off_moves_no_money(api_client, customer, intent, gateway_on):
    """The ledger is touched by the callback and by nothing else."""
    before = Transaction.objects.count()
    api_client.force_authenticate(customer)

    api_client.get(checkout_url(intent))
    api_client.get(checkout_url(intent))

    assert Transaction.objects.count() == before
    intent.refresh_from_db()
    assert intent.state == PaymentIntentState.PENDING


def test_the_template_is_the_only_place_a_gateway_is_described(
    customer, intent, settings
):
    """Switching gateway is a setting, not a deployment.

    The point of the whole arrangement: neither client is rebuilt, neither is
    redeployed, and neither ever learns what a Moyasar is.
    """
    settings.PAYMENT_CHECKOUT_TEMPLATE = "https://other-gateway.test/{reference}"

    assert gateway.checkout_target(intent) == (
        f"https://other-gateway.test/{intent.reference}"
    )
