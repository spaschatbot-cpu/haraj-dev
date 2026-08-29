"""Who the platform deals with.

A person signs in with a Saudi mobile number, not an email address, so the
number is the username. Everything else about them — company details, tax
profile, national id — hangs off that.
"""

from __future__ import annotations

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.core.validators import RegexValidator
from django.db import models
from django.utils import timezone

saudi_mobile = RegexValidator(
    r"^9665\d{8}$",
    "الرقم لازم يكون بصيغة 9665XXXXXXXX",
)


class UserManager(BaseUserManager):
    def create_user(self, phone: str, password: str | None = None, **extra):
        if not phone:
            raise ValueError("phone is required")
        user = self.model(phone=phone, **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, phone: str, password: str, **extra):
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        extra.setdefault("is_active", True)
        return self.create_user(phone, password, **extra)


class AccountType(models.TextChoices):
    INDIVIDUAL = "individual", "فرد"
    COMPANY = "company", "شركة"


class User(AbstractBaseUser, PermissionsMixin):
    phone = models.CharField(
        max_length=15, unique=True, validators=[saudi_mobile], db_index=True
    )
    full_name = models.CharField(max_length=200)
    email = models.EmailField(blank=True)

    account_type = models.CharField(
        max_length=16, choices=AccountType.choices, default=AccountType.INDIVIDUAL
    )

    #: Set once, and only once it is valid — so a customer who typed it wrong
    #: can still correct themselves, but a correct one cannot be swapped for
    #: somebody else's.
    national_id = models.CharField(max_length=20, blank=True, db_index=True)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    phone_verified_at = models.DateTimeField(null=True, blank=True)
    date_joined = models.DateTimeField(default=timezone.now)

    objects = UserManager()

    USERNAME_FIELD = "phone"
    REQUIRED_FIELDS = ["full_name"]

    class Meta:
        indexes = [models.Index(fields=["account_type"])]

    def __str__(self) -> str:
        return f"{self.full_name} ({self.phone})"


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

    def __str__(self) -> str:
        return self.name
