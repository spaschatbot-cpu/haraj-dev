"""The user model, and the two layers that guard the mobile number.

Each rule is asserted twice on purpose: once through the manager, which owes the
caller an arabic message, and once by writing straight to the table, which is
where the rule actually lives (constitution 3-3). A test that only exercises the
python side would still pass on the day someone deletes the constraint.
"""

from __future__ import annotations

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from apps.accounts.models import AccountType, User

pytestmark = pytest.mark.django_db


def test_creates_a_user_identified_by_their_mobile():
    user = User.objects.create_user(phone="966501234567", full_name="زايد الحربي")

    assert user.pk is not None
    assert User.objects.get(phone="966501234567") == user
    assert user.get_username() == "966501234567"
    assert user.account_type == AccountType.INDIVIDUAL


@pytest.mark.parametrize(
    "phone",
    [
        "0501234567",  # local form, not the stored one
        "+966501234567",  # with the plus
        "96650123456",  # one digit short
        "9665012345678",  # one digit long
        "96650123456a",  # not all digits
        " 966501234567",  # padded
        "",
    ],
)
def test_manager_refuses_a_malformed_number(phone):
    with pytest.raises(ValidationError) as caught:
        User.objects.create_user(phone=phone, full_name="زايد")

    assert "phone" in caught.value.error_dict
    assert not User.objects.exists()


def test_the_table_itself_refuses_a_malformed_number():
    # Bypassing the manager on purpose: .save() runs no validation, so this
    # reaches postgres and only the CHECK constraint can stop it.
    with pytest.raises(IntegrityError):
        User(phone="0501234567", full_name="زايد").save()


def test_manager_refuses_a_repeated_number():
    User.objects.create_user(phone="966501234567", full_name="زايد")

    with pytest.raises(ValidationError) as caught:
        User.objects.create_user(phone="966501234567", full_name="شخص آخر")

    assert "phone" in caught.value.error_dict
    assert User.objects.count() == 1


def test_the_table_itself_refuses_a_repeated_number():
    User.objects.create_user(phone="966501234567", full_name="زايد")

    with pytest.raises(IntegrityError):
        User(phone="966501234567", full_name="شخص آخر").save()


def test_one_national_id_belongs_to_one_account():
    User.objects.create_user(
        phone="966501234567", full_name="زايد", national_id="1234567890"
    )

    with pytest.raises(ValidationError):
        User.objects.create_user(
            phone="966507654321", full_name="شخص آخر", national_id="1234567890"
        )

    with transaction.atomic(), pytest.raises(IntegrityError):
        User(phone="966507654321", full_name="شخص آخر", national_id="1234567890").save()


def test_accounts_without_a_national_id_do_not_collide():
    # The unique index is partial; "" is not an identity, so any number of
    # accounts may be waiting to verify theirs.
    User.objects.create_user(phone="966501234567", full_name="زايد")
    User.objects.create_user(phone="966507654321", full_name="شخص آخر")

    assert User.objects.filter(national_id="").count() == 2


def test_a_superuser_can_actually_administer():
    admin = User.objects.create_superuser(
        phone="966500000000", password="v3ry-l0ng-passphrase", full_name="مدير"
    )

    assert admin.is_staff and admin.is_superuser and admin.is_active

    with pytest.raises(ValidationError):
        User.objects.create_superuser(
            phone="966500000001",
            password="v3ry-l0ng-passphrase",
            full_name="مدير بلا صلاحية",
            is_staff=False,
        )
