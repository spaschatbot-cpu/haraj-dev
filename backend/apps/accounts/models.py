"""Who the platform deals with.

A person signs in with a Saudi mobile number, not an email address, so the
number is the username. Everything else about them — company details, tax
profile, national id — hangs off that.
"""

from __future__ import annotations

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models
from django.utils import timezone

#: The single place the shape of a Saudi mobile number is written down. The same
#: expression backs the CHECK constraint on the table, so python and postgres can
#: never disagree about which numbers exist.
PHONE_PATTERN = r"^9665\d{8}$"
PHONE_ERROR = "الرقم لازم يكون بصيغة 9665XXXXXXXX"

saudi_mobile = RegexValidator(PHONE_PATTERN, PHONE_ERROR)


class UserManager(BaseUserManager):
    def create_user(self, phone: str, password: str | None = None, **extra):
        user = self.model(phone=phone, **extra)
        user.set_password(password)
        # The CHECK and UNIQUE constraints below refuse a bad row anyway, but an
        # IntegrityError reads as a crash and rolls back the whole transaction.
        # Validating first turns the same refusal into the arabic message a
        # caller can put in front of a person.
        user.full_clean()
        user.save(using=self._db)
        return user

    def create_superuser(self, phone: str, password: str, **extra):
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        extra.setdefault("is_active", True)
        # setdefault leaves an explicit is_staff=False in place; a "superuser"
        # that cannot open the admin is a silent lie, so say so instead.
        if not (extra["is_staff"] and extra["is_superuser"]):
            raise ValidationError("المدير لازم يكون is_staff و is_superuser")
        return self.create_user(phone, password, **extra)


class AccountType(models.TextChoices):
    INDIVIDUAL = "individual", "فرد"
    COMPANY = "company", "شركة"


class User(AbstractBaseUser, PermissionsMixin):
    # unique=True already indexes the column; a second db_index would only cost
    # writes. 12 is the exact length of 9665XXXXXXXX — the CHECK below is what
    # actually holds the shape.
    phone = models.CharField(max_length=12, unique=True, validators=[saudi_mobile])
    full_name = models.CharField(max_length=200)
    email = models.EmailField(blank=True)

    account_type = models.CharField(
        max_length=16, choices=AccountType.choices, default=AccountType.INDIVIDUAL
    )

    #: Set once, and only once it is valid — so a customer who typed it wrong
    #: can still correct themselves, but a correct one cannot be swapped for
    #: somebody else's. Blank until then; the partial unique index below indexes
    #: it and keeps one identity on one account.
    national_id = models.CharField(max_length=20, blank=True)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    phone_verified_at = models.DateTimeField(null=True, blank=True)
    date_joined = models.DateTimeField(default=timezone.now)

    objects = UserManager()

    USERNAME_FIELD = "phone"
    REQUIRED_FIELDS = ["full_name"]

    class Meta:
        verbose_name = "مستخدم"
        verbose_name_plural = "المستخدمون"
        # No index on account_type on purpose: two values over the whole table,
        # so postgres would scan instead of using it and we would pay for it on
        # every write.
        constraints = [
            models.CheckConstraint(
                condition=models.Q(phone__regex=PHONE_PATTERN),
                name="user_phone_is_saudi_mobile",
                violation_error_message=PHONE_ERROR,
            ),
            # One national id belongs to one person. Partial, because every
            # account starts with it blank and "" is not an identity.
            models.UniqueConstraint(
                fields=["national_id"],
                condition=~models.Q(national_id=""),
                name="user_national_id_unique_when_set",
                violation_error_message="رقم الهوية مسجَّل على حساب آخر",
            ),
        ]

    def __str__(self) -> str:
        # Imported here because services imports this module. The admin is a
        # screen like any other, so the name it shows comes from the one
        # function that decides names — never assembled a second time here.
        from apps.accounts.services import display_name

        return f"{display_name(self)} ({self.phone})"


class Company(models.Model):
    """A bidding company. The company's name is what everyone must see.

    v1 displayed the representative's name in some screens and the company's in
    others, and support could not tell which account had bid. Both are stored;
    only :attr:`name` is ever shown as the bidder.
    """

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="company")
    name = models.CharField(max_length=200)
    representative_name = models.CharField(max_length=200, blank=True)

    commercial_register = models.CharField(max_length=32, blank=True)
    vat_number = models.CharField(max_length=32, blank=True)

    # ZATCA national address
    building_number = models.CharField(max_length=8, blank=True)
    street = models.CharField(max_length=200, blank=True)
    district = models.CharField(max_length=200, blank=True)
    city = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=8, blank=True)

    class Meta:
        verbose_name = "شركة"
        verbose_name_plural = "الشركات"
        constraints = [
            # display_name() hands this straight to a screen, so an empty one
            # would show a bidder with no name at all.
            models.CheckConstraint(
                condition=~models.Q(name=""),
                name="company_name_not_blank",
                violation_error_message="اسم الشركة مطلوب",
            ),
        ]

    def __str__(self) -> str:
        return self.name
