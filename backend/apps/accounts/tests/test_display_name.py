"""The name a human sees, and the single function that decides it."""

from __future__ import annotations

import pytest
from django.db import IntegrityError

from apps.accounts.models import AccountType, Company, User
from apps.accounts.services import display_name

pytestmark = pytest.mark.django_db


@pytest.fixture
def individual():
    return User.objects.create_user(phone="966501234567", full_name="زايد الحربي")


@pytest.fixture
def company_account():
    user = User.objects.create_user(
        phone="966507654321",
        full_name="سالم القحطاني",
        account_type=AccountType.COMPANY,
    )
    Company.objects.create(
        user=user,
        name="مؤسسة النور للسيارات",
        representative_name="سالم القحطاني",
    )
    return user


def test_an_individual_is_shown_by_their_own_name(individual):
    assert display_name(individual) == "زايد الحربي"


def test_a_company_is_shown_by_the_company_name_not_the_representative(
    company_account,
):
    assert display_name(company_account) == "مؤسسة النور للسيارات"
    assert display_name(company_account) != company_account.company.representative_name
    assert display_name(company_account) != company_account.full_name


def test_the_admin_label_goes_through_the_same_decision(company_account):
    # str(user) is a screen too. If it ever computed the name itself we would be
    # back to v1, where support could not tell which account had bid.
    assert "مؤسسة النور للسيارات" in str(company_account)
    assert "سالم القحطاني" not in str(company_account)


def test_a_company_account_with_no_company_row_falls_back_to_the_person():
    half_registered = User.objects.create_user(
        phone="966500000000",
        full_name="فهد العتيبي",
        account_type=AccountType.COMPANY,
    )

    assert display_name(half_registered) == "فهد العتيبي"


def test_a_company_may_not_be_saved_without_a_name(individual):
    with pytest.raises(IntegrityError):
        Company(user=individual, name="", representative_name="زايد").save()
