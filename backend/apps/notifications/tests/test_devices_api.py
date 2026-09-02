"""T620 — a handset is registered to the caller, never to a named account.

In v1 the client sent the account id alongside the push token, so pointing
somebody else's notifications at your own phone was a form field away. The
alerts that go out on this channel say what a person is bidding on and for how
much, so that hole was a live feed of somebody's business.
"""

from __future__ import annotations

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.accounts import tokens as token_service
from apps.accounts.models import User
from apps.notifications.models import Device

pytestmark = pytest.mark.django_db

TOKEN = "fcm-token-abcdef123456"


@pytest.fixture
def owner() -> User:
    return User.objects.create_user(phone="966501111111", full_name="صاحب الجهاز")


@pytest.fixture
def victim() -> User:
    return User.objects.create_user(phone="966502222222", full_name="ضحية")


def signed_in(user: User) -> APIClient:
    client = APIClient()
    pair = token_service.issue_pair(user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {pair['access']}")
    return client


def register(client: APIClient, **extra):
    return client.post(
        reverse("notifications_api:devices"),
        {"token": TOKEN, "platform": "android", **extra},
        format="json",
    )


def test_a_handset_is_registered_to_the_signed_in_account(owner):
    response = register(signed_in(owner))

    assert response.status_code == 201
    assert Device.objects.get().user_id == owner.pk


def test_naming_another_account_in_the_body_is_refused(owner, victim):
    """The acceptance criterion, and the v1 hole restated.

    Refused rather than silently ignored: a client that believes it set the
    owner and did not is a client whose author never learns the field is
    meaningless.
    """
    response = register(signed_in(owner), user=victim.pk)

    assert response.status_code == 400
    assert "user" in str(response.data["error"]["detail"])
    assert not Device.objects.exists()


def test_naming_another_account_by_a_second_name_is_also_refused(owner, victim):
    response = register(signed_in(owner), user_id=victim.pk)

    assert response.status_code == 400
    assert not Device.objects.exists()


def test_an_anonymous_caller_cannot_register_anything():
    assert register(APIClient()).status_code in (401, 403)
    assert not Device.objects.exists()


def test_a_handset_that_changed_hands_moves_instead_of_doubling(owner, victim):
    """The reason the token is unique across the table rather than per user.

    A phone sold on re-registers with the *same* provider token under a new
    account. If the old row survived, the previous owner would keep receiving
    the new owner's bid alerts — which is the same leak by a slower route.
    """
    register(signed_in(owner))
    register(signed_in(victim))

    assert Device.objects.count() == 1
    assert Device.objects.get().user_id == victim.pk


def test_registering_the_same_handset_twice_is_not_two_rows(owner):
    register(signed_in(owner))
    second = register(signed_in(owner))

    assert second.status_code == 200
    assert Device.objects.count() == 1


def test_the_push_token_never_comes_back_in_a_response(owner):
    """It is a credential for sending to that handset.

    A response that carries it puts it in a proxy cache, an access log and the
    client's own crash reports.
    """
    response = register(signed_in(owner))

    assert TOKEN not in str(response.data)
    assert response.data["token_tail"] == TOKEN[-6:]


def test_my_devices_lists_only_mine(owner, victim):
    register(signed_in(owner))
    Device.objects.create(user=victim, token="another-token", platform="ios")

    listed = signed_in(owner).get(reverse("notifications_api:devices")).data

    assert len(listed) == 1
    assert listed[0]["platform"] == "android"


def test_an_unknown_platform_is_refused(owner):
    response = signed_in(owner).post(
        reverse("notifications_api:devices"),
        {"token": TOKEN, "platform": "blackberry"},
        format="json",
    )

    assert response.status_code == 400
