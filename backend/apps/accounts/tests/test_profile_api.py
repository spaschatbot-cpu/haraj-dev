"""T605–T607 — the account a customer owns, and the two rules that guard it.

* **T605** an unknown field is a clear 400, never a 500. v1's profile endpoint
  fed the request body into `.update(**body)`, so a typo was a database error
  and a well-chosen key was a privilege escalation.
* **T606** a *correct* national id is pinned forever; a *wrong* one can still be
  corrected. Both halves matter: v1 pinned the first value written, so fixing a
  mistyped digit meant asking support to edit the database.
* **T607** a new company must carry what a tax invoice needs; companies that
  predate ZATCA's national address are exempt until a date the owner sets.
"""

from __future__ import annotations

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.accounts import services
from apps.accounts import tokens as token_service
from apps.accounts.errors import NationalIdAlreadyVerified
from apps.accounts.models import AccountType, Company, User

pytestmark = pytest.mark.django_db

#: Two well-formed identities (leading 1 or 2, ten digits, checksum holds).
VALID_ID = "1000000008"
ANOTHER_VALID_ID = "2000000006"
#: Right length, wrong checksum — the typo case T606 must let through once.
MISTYPED_ID = "1000000001"


@pytest.fixture
def user() -> User:
    return User.objects.create_user(phone="966501111111", full_name="عميل")


@pytest.fixture
def api(user: User) -> APIClient:
    client = APIClient()
    pair = token_service.issue_pair(user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {pair['access']}")
    return client


COMPLETE_COMPANY = {
    "name": "شركة الاختبار",
    "commercial_register": "1010101010",
    "vat_number": "300000000000003",
    "building_number": "1234",
    "street": "طريق الملك فهد",
    "district": "العليا",
    "city": "الرياض",
    "postal_code": "12345",
}


# ---------------------------------------------------------------------------
# T605 — reading and editing
# ---------------------------------------------------------------------------


def test_the_profile_is_the_callers_own(api, user):
    body = api.get(reverse("accounts_api:profile")).data

    assert body["id"] == user.pk
    assert body["phone"] == user.phone


def test_an_anonymous_caller_gets_nothing():
    assert APIClient().get(reverse("accounts_api:profile")).status_code in (401, 403)


def test_the_two_fields_a_customer_owns_can_be_edited(api, user):
    response = api.patch(
        reverse("accounts_api:profile"),
        {"full_name": "الاسم الجديد", "email": "a@b.com"},
        format="json",
    )

    assert response.status_code == 200
    user.refresh_from_db()
    assert user.full_name == "الاسم الجديد"
    assert user.email == "a@b.com"


@pytest.mark.parametrize(
    "field",
    [
        pytest.param("phone", id="the phone, which needs two codes (T604)"),
        pytest.param("account_type", id="becoming a company by asking"),
        pytest.param("is_staff", id="the obvious escalation"),
        pytest.param("national_id", id="the id, which has its own rule (T606)"),
        pytest.param("fullname", id="a plain typo"),
    ],
)
def test_a_field_the_customer_does_not_own_is_a_400_not_a_500(api, user, field):
    """T605's acceptance criterion, one case per way it goes wrong."""
    before = {
        "phone": user.phone,
        "account_type": user.account_type,
        "is_staff": user.is_staff,
    }

    response = api.patch(
        reverse("accounts_api:profile"), {field: "966509999999"}, format="json"
    )

    assert response.status_code == 400
    assert response.data["error"]["code"] == "validation_error"
    assert field in str(response.data["error"]["detail"])

    user.refresh_from_db()
    assert user.phone == before["phone"]
    assert user.account_type == before["account_type"]
    assert user.is_staff == before["is_staff"]


def test_an_unknown_field_alongside_a_known_one_still_refuses(api, user):
    """Otherwise the good half saves and the customer never learns of the bad."""
    response = api.patch(
        reverse("accounts_api:profile"),
        {"full_name": "اسم", "is_staff": True},
        format="json",
    )

    assert response.status_code == 400
    user.refresh_from_db()
    assert user.full_name == "عميل"


def test_an_empty_edit_is_refused_rather_than_answered_with_success(api):
    """A PATCH that changes nothing is a client bug; 200 would hide it."""
    assert (
        api.patch(reverse("accounts_api:profile"), {}, format="json").status_code == 400
    )


# ---------------------------------------------------------------------------
# T606 — set once, on the correct value
# ---------------------------------------------------------------------------


def test_a_valid_id_is_accepted_and_marked_verified(api, user):
    response = api.put(
        reverse("accounts_api:profile-national-id"),
        {"national_id": VALID_ID},
        format="json",
    )

    assert response.status_code == 200
    assert response.data["national_id"] == VALID_ID
    assert response.data["national_id_verified"] is True


def test_a_mistyped_id_can_be_corrected(api, user):
    """The half v1 got wrong: the first value written was final."""
    user.national_id = MISTYPED_ID
    user.save(update_fields=["national_id"])

    response = api.put(
        reverse("accounts_api:profile-national-id"),
        {"national_id": VALID_ID},
        format="json",
    )

    assert response.status_code == 200
    user.refresh_from_db()
    assert user.national_id == VALID_ID


def test_a_valid_id_cannot_be_swapped_for_another(api, user):
    """The account carries obligations that belong to the person it names."""
    api.put(
        reverse("accounts_api:profile-national-id"),
        {"national_id": VALID_ID},
        format="json",
    )

    response = api.put(
        reverse("accounts_api:profile-national-id"),
        {"national_id": ANOTHER_VALID_ID},
        format="json",
    )

    assert response.status_code == 409
    assert response.data["error"]["code"] == "national_id_already_verified"
    user.refresh_from_db()
    assert user.national_id == VALID_ID


def test_correcting_a_typo_with_another_typo_is_refused(api, user):
    """The exit from the correctable state is one-way, or it is not an exit."""
    user.national_id = MISTYPED_ID
    user.save(update_fields=["national_id"])

    response = api.put(
        reverse("accounts_api:profile-national-id"),
        {"national_id": "1111111111"},
        format="json",
    )

    assert response.status_code == 409
    assert response.data["error"]["code"] == "national_id_invalid"


@pytest.mark.parametrize(
    "value",
    [
        pytest.param("123456789", id="nine digits"),
        pytest.param("12345678901", id="eleven digits"),
        pytest.param("abcdefghij", id="letters"),
    ],
)
def test_a_malformed_id_is_a_field_error(api, value):
    response = api.put(
        reverse("accounts_api:profile-national-id"),
        {"national_id": value},
        format="json",
    )

    assert response.status_code == 400


def test_an_id_that_names_no_identity_type_is_refused(api):
    """Ten digits starting with 3 is not an identity, whatever its checksum."""
    response = api.put(
        reverse("accounts_api:profile-national-id"),
        {"national_id": "3000000000"},
        format="json",
    )

    assert response.status_code == 409
    assert response.data["error"]["code"] == "national_id_invalid"


# ---------------------------------------------------------------------------
# T607 — the company and its ZATCA address
# ---------------------------------------------------------------------------


def test_an_account_with_no_company_says_so_rather_than_returning_blanks(api):
    """ "No company" and "a company with empty fields" are different answers."""
    assert api.get(reverse("accounts_api:profile-company")).status_code == 404


def test_a_complete_new_company_is_saved(api, user):
    response = api.put(
        reverse("accounts_api:profile-company"), COMPLETE_COMPANY, format="json"
    )

    assert response.status_code == 200
    assert response.data["is_complete"] is True

    user.refresh_from_db()
    # The account becomes a company account by *having* one — never by claiming
    # it in a request body.
    assert user.account_type == AccountType.COMPANY


@pytest.mark.parametrize("missing", sorted(COMPLETE_COMPANY))
def test_a_new_company_missing_any_required_field_is_refused(api, missing):
    """A company that bids without these wins a car we cannot legally invoice."""
    fields = {key: value for key, value in COMPLETE_COMPANY.items() if key != missing}

    response = api.put(reverse("accounts_api:profile-company"), fields, format="json")

    assert response.status_code == 409
    assert response.data["error"]["code"] == "company_profile_incomplete"
    assert missing in response.data["error"]["detail"]["missing"]
    assert not Company.objects.filter(user__isnull=False).exists()


def test_a_company_that_predates_the_address_rule_can_still_edit_itself(api, user):
    """The exemption, and the reason it exists.

    A third of v1's companies have no postal code. Refusing to let them save a
    corrected representative name until they produce a district would lock
    working accounts out of their own profile.
    """
    Company.objects.create(user=user, name="شركة قديمة")

    response = api.put(
        reverse("accounts_api:profile-company"),
        {"representative_name": "الممثل الجديد"},
        format="json",
    )

    assert response.status_code == 200
    assert response.data["representative_name"] == "الممثل الجديد"
    # Still not invoiceable, and the response says so rather than pretending.
    assert response.data["is_complete"] is False


def test_the_exempt_company_becomes_complete_when_it_fills_the_gaps(api, user):
    Company.objects.create(user=user, name="شركة قديمة")

    response = api.put(
        reverse("accounts_api:profile-company"), COMPLETE_COMPANY, format="json"
    )

    assert response.data["is_complete"] is True


def test_an_unknown_company_field_is_refused(api):
    response = api.put(
        reverse("accounts_api:profile-company"),
        {**COMPLETE_COMPANY, "tax_exempt": True},
        format="json",
    )

    assert response.status_code == 400


def test_one_customer_never_sees_anothers_company(api, user):
    """No path parameter names a user here, so there is nothing to tamper with."""
    stranger = User.objects.create_user(phone="966502222222", full_name="غريب")
    Company.objects.create(user=stranger, **COMPLETE_COMPANY)

    assert api.get(reverse("accounts_api:profile-company")).status_code == 404


# ---------------------------------------------------------------------------
# The locked fields, and why each one is locked
# ---------------------------------------------------------------------------
#
# The Flutter profile screen (T715) must show a locked field *with its reason*.
# The reason is sent from here rather than written in the client, because a
# client that phrases the rule itself owns a second copy of it — and the copy
# drifts the first time the rule changes here.


def test_the_phone_is_locked_with_a_reason_that_points_at_its_own_path(api):
    body = api.get(reverse("accounts_api:profile")).data

    phone_lock = next(item for item in body["locked_fields"] if item["field"] == "phone")
    assert phone_lock["reason"] == services.PHONE_LOCK_REASON
    assert phone_lock["reason"].strip()


def test_a_correctable_national_id_is_not_listed_as_locked(api, user):
    user.national_id = MISTYPED_ID
    user.save(update_fields=["national_id"])

    body = api.get(reverse("accounts_api:profile")).data

    # T606's first half: a customer who mistyped a digit finds an open field.
    assert [item["field"] for item in body["locked_fields"]] == ["phone"]


def test_a_verified_national_id_is_locked_with_the_refusals_own_sentence(api, user):
    user.national_id = VALID_ID
    user.save(update_fields=["national_id"])

    body = api.get(reverse("accounts_api:profile")).data

    lock = next(item for item in body["locked_fields"] if item["field"] == "national_id")
    # The same sentence the PUT would refuse with. Two wordings for one rule is
    # how a customer gets two different answers to the same question.
    assert lock["reason"] == NationalIdAlreadyVerified.default_message
