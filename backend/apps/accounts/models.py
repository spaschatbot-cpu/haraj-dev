"""Who the platform deals with.

A person signs in with a Saudi mobile number, not an email address, so the
number is the username. Everything else about them — company details, tax
profile, national id — hangs off that.

وذلك **للعميل** وحده منذ T918: الموظّف يدخل اللوحة باسمٍ في `username` وكلمةِ
مرور، لا برقمه — بقرار المالك. و`USERNAME_FIELD` يبقى `phone` لأن تغييرَه يمسّ
`createsuperuser` وكلَّ هجرةٍ قائمةٍ ومسارَ العميل؛ المُبدَّلُ خلفيّةُ المصادقة
(`apps.accounts.backends`) لا حقلُ الهويّة.
"""

from __future__ import annotations

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models
from django.utils import timezone

from apps.core.uploads import customer_document_path

#: The single place the shape of a Saudi mobile number is written down. The same
#: expression backs the CHECK constraint on the table, so python and postgres can
#: never disagree about which numbers exist.
PHONE_PATTERN = r"^9665\d{8}$"
PHONE_ERROR = "الرقم لازم يكون بصيغة 9665XXXXXXXX"

saudi_mobile = RegexValidator(PHONE_PATTERN, PHONE_ERROR)

# ---------------------------------------------------------------------------
# اسمُ دخولِ الموظّف — بابٌ مستقلٌّ عن الجوّال. T918
# ---------------------------------------------------------------------------
#
# قرارُ المالك بالحرف: «عايز تسجيل دخول الادمن يكون بيوزر و باس، مش بالرقم.
# الرقم و الـOTP دا للمستخدمين». وv1 يفعلها بجدولٍ منفصلٍ اسمه `management`
# فيه `username` و`password` (`admin3/login/admin_login.php`) — و**البنيةُ لا
# تُنقل**: هويّةُ الموظّف في جدولٍ وهويّةُ العميل في آخر تعني شخصاً واحداً في
# مكانين يتفارقان، ومن غيّر جوّالَه في أحدهما لم يغيّره في الآخر. المنقولُ
# **المنطق**: اسمٌ يُعرَف به الموظّف لا يتعلّق برقمه.
#
#: الطولُ ٣٢ لا ١٥٠: الاسم يُكتب في خانةٍ ويُقرأ في جدول، وواحدٌ بمئةِ حرفٍ
#: يكسر عمودَ الجدول ولا يخدم أحداً.
USERNAME_MAX_LENGTH = 32

#: الحروفُ المسموحة. `A-Z` مقبولةٌ هنا **وتُطوى إلى صغيرةٍ في `save`**، لا
#: لأن `Ahmad` اسمٌ ثانٍ — بل لأنه العينُ نفسها، ورفضُه عند الكتابة رفضٌ بلا
#: فائدةٍ لمن كتب اسمَه بحرفٍ كبير. والطيُّ هو الحارس: `Ahmad` و`ahmad`
#: اسمان لعينٍ واحدة، واختلافُ الحالة بابُ انتحالٍ صامت.
USERNAME_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9._-]{2,31}$"
USERNAME_ERROR = (
    "اسم الدخول: من ٣ إلى ٣٢ محرفاً، حروفاً لاتينية وأرقاماً و. _ - "
    "ويُحفظ بحروفٍ صغيرة."
)

staff_username = RegexValidator(USERNAME_PATTERN, USERNAME_ERROR)


def not_a_phone_number(value: str) -> None:
    """اسمُ الدخول لا يكون رقماً — وإلا عاد البابُ الذي أُغلق من الخلف.

    لو جاز `966500000000` اسمَ دخول، لصار الموظّف يدخل برقمه فعلاً وإن كانت
    الخلفيّة تبحث في عمودٍ آخر — فيلتبس البابان على من يقرأ الشاشة وعلى من
    يقرأ الكود. والمنعُ على **كلّ ما هو أرقامٌ محضة** لا على صيغة `9665…`
    وحدها: `0500000000` رقمُ جوّالٍ أيضاً في عين من يكتبه.
    """
    if value and value.isdigit():
        raise ValidationError("اسم الدخول لا يكون أرقاماً وحدها — الرقم للعملاء.")


class UserManager(BaseUserManager["User"]):
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


class Gender(models.TextChoices):
    MALE = "male", "ذكر"
    FEMALE = "female", "أنثى"


class IdKind(models.TextChoices):
    NATIONAL_ID = "national_id", "هوية وطنية"
    IQAMA = "iqama", "إقامة"
    PASSPORT = "passport", "جواز سفر"


class User(AbstractBaseUser, PermissionsMixin):
    # unique=True already indexes the column; a second db_index would only cost
    # writes. 12 is the exact length of 9665XXXXXXXX — the CHECK below is what
    # actually holds the shape.
    phone = models.CharField(
        "الجوال", max_length=12, unique=True, validators=[saudi_mobile]
    )
    #: اسمُ دخولِ الموظّف. فارغٌ لكلّ عميل — و**الفراغُ ليس هويّة**: أربعةٌ
    #: وأربعون ألفَ عميلٍ يحملونه، فقيدُ التفرّد جزئيٌّ على غرار `national_id`
    #: تماماً، و`StaffUsernameBackend` يردّ الاسمَ الفارغ قبل أيّ استعلام.
    username = models.CharField(
        "اسم الدخول",
        max_length=USERNAME_MAX_LENGTH,
        blank=True,
        default="",
        validators=[staff_username, not_a_phone_number],
    )
    full_name = models.CharField("الاسم الكامل", max_length=200)
    name_ar = models.CharField("الاسم بالعربي", max_length=255, blank=True)
    name_en = models.CharField("الاسم بالإنجليزي", max_length=255, blank=True)
    email = models.EmailField("البريد", blank=True)
    birth_date = models.DateField("تاريخ الميلاد", null=True, blank=True)
    gender = models.CharField("الجنس", max_length=8, choices=Gender.choices, blank=True)
    id_kind = models.CharField(
        "نوع الهوية", max_length=16, choices=IdKind.choices, blank=True
    )

    account_type = models.CharField(
        "نوع الحساب",
        max_length=16,
        choices=AccountType.choices,
        default=AccountType.INDIVIDUAL,
    )

    #: Set once, and only once it is valid — so a customer who typed it wrong
    #: can still correct themselves, but a correct one cannot be swapped for
    #: somebody else's. Blank until then; the partial unique index below indexes
    #: it and keeps one identity on one account.
    national_id = models.CharField("رقم الهوية", max_length=20, blank=True)

    is_active = models.BooleanField("الحساب مفعّل", default=True)
    banned_until = models.DateTimeField("محظور حتى", null=True, blank=True)

    #: الآيبان: مسجَّل ومحميّ بصلاحية مالية (T850).
    iban = models.CharField("الآيبان", max_length=50, blank=True)

    #: كلمةُ مرورٍ كتبها **شخصٌ آخر**، فلا تصلح للاستمرار. T848.
    #:
    #: استمارةُ «إضافة مشرف» في v1 فيها خانةُ كلمة مرورٍ يملؤها موظّفٌ
    #: لموظّفٍ آخر — أي أن الأول يعرف كلمة الثاني ويستطيع الدخول باسمه،
    #: فيصير كلُّ قيدٍ يتركه الثاني في `AuditLog` **قابلاً للإنكار**:
    #: «لم أفعل، فلانٌ يعرف كلمتي». وذلك يُبطل السجلَّ كلَّه لا صفّاً منه.
    #:
    #: والعلمُ هنا يُنهي تلك المعرفة عند أوّل دخول: الحارس في
    #: `apps.console.views.console_page` يحوّل حاملَه إلى شاشة تغيير
    #: الكلمة قبل أيّ شاشةٍ أخرى، فما يعرفه المنشئ يصير باطلاً قبل أن
    #: يُفعل بالحساب شيء.
    must_change_password = models.BooleanField(
        "يغيّر كلمة المرور عند أوّل دخول", default=False
    )
    is_staff = models.BooleanField("موظّف", default=False)

    #: Which bundle of console capabilities this account starts with (T801).
    #:
    #: Blank for every customer, and blank is not a role — `capabilities_of`
    #: returns nothing for it. Nothing in the codebase reads this field to
    #: decide anything: it is an input to `apps.core.permissions`, and asking
    #: "is this person X?" anywhere else fails a CI check. That indirection is
    #: the whole lesson of v1's `hasRole()`.
    console_role = models.CharField("دور اللوحة", max_length=16, blank=True)

    phone_verified_at = models.DateTimeField("وقت توثيق الجوال", null=True, blank=True)
    date_joined = models.DateTimeField("تاريخ التسجيل", default=timezone.now)

    objects = UserManager()

    USERNAME_FIELD = "phone"
    # و`username` معهما — وهي ليست زينةً في القائمة (T918): `createsuperuser`
    # ينشئ حساباً `is_staff` وحقلُ اسم الدخول فارغ، و**الفارغُ لا يُصادِق**
    # (الحارس الأول في `StaffUsernameBackend`). أي أن الأمر الوحيد الذي يُنشئ
    # أوّلَ مديرٍ في قاعدةٍ جديدة كان سيُنشئه **مقفولاً خارج اللوحة**، بلا
    # رسالةٍ تقول لماذا. فالسؤال عنه صار جزءاً من الأمر.
    REQUIRED_FIELDS = ["full_name", "username"]

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
            # اسمُ دخولٍ واحدٌ لحسابٍ واحد — بالشكل نفسه وللسبب نفسه: كلُّ
            # عميلٍ يبدأ به فارغاً، و`""` ليست هويّة. وقيدٌ كامل (لا جزئيّ)
            # كان سيمنع المستخدمَ الثاني من الوجود أصلاً.
            models.UniqueConstraint(
                fields=["username"],
                condition=~models.Q(username=""),
                name="user_username_unique_when_set",
                violation_error_message="اسم الدخول مستعمَل لحسابٍ آخر",
            ),
        ]

    def save(self, *args, **kwargs):
        """الاسمُ يُطوى إلى حروفٍ صغيرة — هنا وحدَه، لا في كلّ من يكتبه.

        الطيُّ في الاستمارة وحدها يترك باباً مفتوحاً: صفٌّ يُكتب من `shell` أو
        من هجرةٍ بحرفٍ كبير يصير اسماً **لا يستطيع صاحبُه الدخول به** (الخلفيّة
        تبحث بالمصغَّر)، ولا رسالةَ تقول لماذا. وأسوأ منه: `Ahmad` و`ahmad`
        صفّان يمرّان من قيد التفرّد معاً — وذلك انتحالٌ صامت.

        و`update_fields` لا يُمَسّ: طيُّ خاصّيّةٍ لا تُحفَظ في هذا النداء لا
        يضرّ، وإضافتُها إلى القائمة كانت ستكتب عموداً لم يطلب أحدٌ كتابته.
        """
        self.username = (self.username or "").strip().lower()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        # Imported here because services imports this module. The admin is a
        # screen like any other, so the name it shows comes from the one
        # function that decides names — never assembled a second time here.
        from apps.accounts.services import display_name

        return f"{display_name(self)} ({self.phone})"


#: أسماءُ الحقول الموروثة من جانغو — عربيّةً كبقيّتها. T849.
#:
#: `id` و`last_login` و`is_superuser` تأتي من `AbstractBaseUser` و
#: `PermissionsMixin` بأسمائها الإنجليزية، وشاشةُ ملفّ العميل تقرأ
#: `verbose_name` من النموذج — فتخرج ثلاثةُ أسطرٍ إنجليزية وسط جدولٍ عربيّ
#: («superuser status: لا»). وتُضبَط هنا لا في العرض: الاسمُ صفةٌ للحقل،
#: ووضعُه في شاشةٍ يعني قائمةَ ترجمةٍ ثانيةً تفترق عن النموذج.
#:
#: ولا هجرةَ لها: `verbose_name` بيانٌ وصفيّ لا يمسّ القاعدة، وجانغو لا يرصده
#: على حقلٍ موروثٍ يُعدَّل بعد بناء الصنف.
for _field, _label in (
    ("id", "المعرّف"),
    ("last_login", "آخر دخول"),
    ("is_superuser", "مدير النظام"),
):
    User._meta.get_field(_field).verbose_name = _label


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

    # العنوان الوطنيّ انتقل إلى `NationalAddress` (T850)، وهذه خصائصُ **قراءة**
    # تُبقي القرّاء القدامى يعملون بلا عمودٍ مكرَّر.
    #
    # **والكتابة تصرخ ولا تصمت.** كانت أجسامُ الـsetters `pass`، أي أن
    # `company.city = "الرياض"` يُهمَل بلا كلمة — والاستمارة تقول «حُفظت» وهو
    # لم يُحفظ. وذلك عطل T808 بعينه في شكلٍ جديد: الموظّف يكتب، ويُبلَّغ
    # بالنجاح، ولا شيء يُخزَّن. فالإسنادُ الآن يرفع `AttributeError` يقول أين
    # يُكتب العنوان فعلاً.
    def _national_address(self):
        """عنوانُ صاحب الشركة، أو `None` إن لم يُكتب له عنوانٌ بعد.

        و`ObjectDoesNotExist` وحدها تُلتقَط لا `Exception`: الثانيةُ تبتلع
        خطأ الاتّصال وخطأ البرمجة معاً فتُرجع `None`، فتُقرأ الشاشة «لا عنوان»
        وهي لا تعرف. وذلك هو `safeRows` في v1 حرفياً — يُرجع `[]` بصمت فيقرأ
        الموظّف «لا مزايدات» وهي موجودة.
        """
        from django.core.exceptions import ObjectDoesNotExist

        try:
            return self.user.national_address
        except ObjectDoesNotExist:
            return None

    @property
    def building_number(self) -> str:
        addr = self._national_address()
        return addr.building_number if addr else ""

    @building_number.setter
    def building_number(self, val: str) -> None:
        raise AttributeError(
            "العنوان الوطنيّ يُكتب في `accounts.NationalAddress` لا على الشركة. "
            f"أُسنِد «{val}» إلى `Company.building_number` وهو خاصّةُ قراءة."
        )

    @property
    def street(self) -> str:
        addr = self._national_address()
        return addr.street if addr else ""

    @street.setter
    def street(self, val: str) -> None:
        raise AttributeError(
            "العنوان الوطنيّ يُكتب في `accounts.NationalAddress` لا على الشركة. "
            f"أُسنِد «{val}» إلى `Company.street` وهو خاصّةُ قراءة."
        )

    @property
    def district(self) -> str:
        addr = self._national_address()
        return addr.district if addr else ""

    @district.setter
    def district(self, val: str) -> None:
        raise AttributeError(
            "العنوان الوطنيّ يُكتب في `accounts.NationalAddress` لا على الشركة. "
            f"أُسنِد «{val}» إلى `Company.district` وهو خاصّةُ قراءة."
        )

    @property
    def city(self) -> str:
        addr = self._national_address()
        return addr.city if addr else ""

    @city.setter
    def city(self, val: str) -> None:
        raise AttributeError(
            "العنوان الوطنيّ يُكتب في `accounts.NationalAddress` لا على الشركة. "
            f"أُسنِد «{val}» إلى `Company.city` وهو خاصّةُ قراءة."
        )

    @property
    def postal_code(self) -> str:
        addr = self._national_address()
        return addr.postal_code if addr else ""

    @postal_code.setter
    def postal_code(self, val: str) -> None:
        raise AttributeError(
            "العنوان الوطنيّ يُكتب في `accounts.NationalAddress` لا على الشركة. "
            f"أُسنِد «{val}» إلى `Company.postal_code` وهو خاصّةُ قراءة."
        )


class NationalAddress(models.Model):
    """العنوان الوطني الموحد للعميل (فرد أو شركة). T850.

    العنوان الوطني كان على Company وحدها، والأفراد في v1 يملكون عناوين على userss.
    القاعدة الواحدة في مكان واحد: يملكه User، وتُنقل إليه عناوين الشركات بهجرة بيانات،
    ويشمل صيغ العنوان الوطني السعودي النظامية.
    """

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="national_address",
        verbose_name="المستخدم",
    )
    country = models.CharField(
        "الدولة", max_length=255, default="المملكة العربية السعودية", blank=True
    )
    region = models.CharField("المنطقة", max_length=255, blank=True)
    city = models.CharField("المدينة", max_length=100, blank=True)
    district = models.CharField("الحي", max_length=255, blank=True)
    street = models.CharField("الشارع", max_length=255, blank=True)
    building_number = models.CharField("رقم المبنى", max_length=4, blank=True)
    postal_code = models.CharField("الرمز البريدي", max_length=5, blank=True)
    additional_number = models.CharField("الرقم الإضافي", max_length=4, blank=True)
    plot_number = models.CharField("رقم القطعة", max_length=255, blank=True)

    class Meta:
        verbose_name = "عنوان وطني"
        verbose_name_plural = "العناوين الوطنية"

    def __str__(self) -> str:
        parts = [self.city, self.district, self.street]
        return " · ".join(p for p in parts if p) or f"عنوان {self.user_id}"

    def clean(self) -> None:
        errors: dict[str, str] = {}
        if self.postal_code and (
            len(self.postal_code) != 5 or not self.postal_code.isdigit()
        ):
            errors["postal_code"] = "الرمز البريدي يجب أن يتكون من 5 أرقام"
        if self.building_number and (
            len(self.building_number) != 4 or not self.building_number.isdigit()
        ):
            errors["building_number"] = "رقم المبنى يجب أن يتكون من 4 أرقام"
        if self.additional_number and (
            len(self.additional_number) != 4 or not self.additional_number.isdigit()
        ):
            errors["additional_number"] = "الرقم الإضافي يجب أن يتكون من 4 أرقام"
        if errors:
            raise ValidationError(errors)


# --------------------------------------------------------------------------
# Authentication — a one-time code, then two tokens.
#
# Neither the code nor the tokens are stored as the customer sees them. What is
# in these tables is a SHA-256 digest, so a dump of the database — a backup on a
# laptop, a support query pasted into a chat — hands nobody a working key.
# --------------------------------------------------------------------------


class OtpPurpose(models.TextChoices):
    """Why a code was sent.

    A code is scoped to its purpose so one sent to confirm a phone change can
    never be typed into the login screen instead.
    """

    LOGIN = "login", "دخول أو تسجيل"
    CHANGE_PHONE = "change_phone", "تغيير رقم الجوال"
    RECOVER = "recover", "استعادة الحساب"


class PhoneVerification(models.Model):
    """One code, sent to one number, for one purpose.

    Rows are kept after use rather than deleted: "was a code ever sent to this
    number, and what happened to it" is the first question support asks, and in
    v1 there was no table that answered it.
    """

    phone = models.CharField(max_length=12, validators=[saudi_mobile])
    purpose = models.CharField(
        max_length=16, choices=OtpPurpose.choices, default=OtpPurpose.LOGIN
    )

    #: SHA-256 of the digits. The digits themselves exist in one place only —
    #: the SMS — and never come back in any response (T601's hardest rule).
    code_hash = models.CharField(max_length=64)

    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    expires_at = models.DateTimeField()

    #: Counted per code, not per request: the wall is the number of guesses this
    #: particular code will tolerate.
    attempts = models.PositiveSmallIntegerField(default=0)

    consumed_at = models.DateTimeField(null=True, blank=True)

    #: Set when the whole code is written off — attempts spent, or superseded by
    #: a newer send. Distinct from `consumed_at`, which means it worked.
    voided_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(
                fields=["phone", "purpose", "-created_at"],
                name="otp_phone_purpose_recent",
            ),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(expires_at__gt=models.F("created_at")),
                name="otp_expires_after_creation",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.phone} · {self.purpose}"

    @property
    def is_live(self) -> bool:
        """Neither used, nor written off, nor past its expiry."""
        return (
            self.consumed_at is None
            and self.voided_at is None
            and self.expires_at > timezone.now()
        )


class TokenKind(models.TextChoices):
    ACCESS = "access", "رمز وصول"
    REFRESH = "refresh", "رمز تحديث"


class AuthToken(models.Model):
    """An issued token, revocable the moment support needs it revoked.

    Opaque and stored, not self-describing and signed. A JWT cannot be taken
    back before it expires; this platform moves money and v1 had an account
    takeover path, so "log this session out now" has to be a row update rather
    than a wait.
    """

    user = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE, related_name="auth_tokens"
    )
    kind = models.CharField(max_length=8, choices=TokenKind.choices)

    #: SHA-256 of the token string. Unique, so a lookup is one indexed read and
    #: a collision is impossible rather than merely unlikely.
    token_hash = models.CharField(max_length=64, unique=True)

    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    expires_at = models.DateTimeField()
    revoked_at = models.DateTimeField(null=True, blank=True)
    last_used_at = models.DateTimeField(null=True, blank=True)

    #: The refresh token this one was minted from. The chain is what makes reuse
    #: detectable: presenting a spent link means someone else holds it too.
    rotated_from = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="rotated_to",
    )

    class Meta:
        indexes = [
            models.Index(fields=["user", "kind"], name="authtoken_user_kind"),
        ]

    def __str__(self) -> str:
        return f"{self.kind} · {self.user_id}"

    @property
    def is_live(self) -> bool:
        return self.revoked_at is None and self.expires_at > timezone.now()


class SmsFailure(models.Model):
    """A message the provider would not carry, kept so nobody diagnoses it twice.

    In v1 "تعذّر إرسال رمز التحقق" was the only visible symptom of an SMS
    balance running out, and it was traced from scratch every time — the
    provider's dashboard on one screen, the application log on another, and no
    row anywhere saying *when it started*. This table is that row.

    Written **after** the transaction that tried to send has rolled back, never
    inside it: `send_verification_code` sends inside its atomic block on purpose,
    so a failure takes the unsent code's row with it. A failure record written in
    the same block would be taken with it too — the evidence would vanish at
    exactly the moment it was worth having. See `services.send_verification_code`.
    """

    #: The dotted path that was configured, not a friendly name: when two
    #: providers are being A/B'd, the setting is the thing that identifies which.
    provider = models.CharField(max_length=200)

    #: Which number the message was for. Support's first question is whether one
    #: customer is affected or everybody.
    phone = models.CharField(max_length=12, validators=[saudi_mobile])

    purpose = models.CharField(
        max_length=16, choices=OtpPurpose.choices, default=OtpPurpose.LOGIN
    )

    #: The provider's own words, as given. Never parsed into a status enum: the
    #: reason a provider refuses is its vocabulary, not ours (Article 2-3).
    reason = models.TextField(blank=True)

    created_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        indexes = [
            models.Index(fields=["-created_at"], name="sms_failure_recent"),
        ]

    def __str__(self) -> str:
        return f"{self.phone} · {self.provider}"


class StaffGrant(models.Model):
    """One capability given to — or taken from — one person, above their role.

    Two reasons this exists rather than "just make another role":

    * **Adding.** One operations person also handles refunds while a colleague
      is away. Creating a fifth role for a fortnight leaves a fifth role behind
      forever, and v1 accumulated eleven of them that way.
    * **Taking away.** Somebody's access to one screen has to stop *today*,
      without editing a role a dozen others share.

    A revoke beats a grant and a grant beats the role — the order is in
    `apps.core.permissions.capabilities_of`, which is the only thing that reads
    this table.
    """

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="grants")

    #: A `Capability` value. Deliberately a plain CharField and not a choices
    #: field: `apps.core` may not import a domain enum into a model that
    #: `apps.core` itself reads, and a grant naming a capability that no longer
    #: exists must remain readable rather than break every query on the table.
    capability = models.CharField(max_length=64)

    #: True grants, False revokes. One row shape for both, so "what has been
    #: done to this person's access" is one query and one screen.
    granted = models.BooleanField(default=True)

    #: Why, and who. An access change with no reason is the row nobody can
    #: explain six months later — and access changes are exactly what an audit
    #: asks about first.
    reason = models.TextField()
    granted_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="grants_given",
    )

    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = "منح صلاحية"
        verbose_name_plural = "منح الصلاحيات"
        constraints = [
            # One row per (person, capability). Granting twice is the same
            # grant; granting and then revoking must *replace* the row rather
            # than leave two contradicting each other for the reader to resolve.
            models.UniqueConstraint(
                fields=["user", "capability"], name="one_grant_per_user_capability"
            ),
            models.CheckConstraint(
                condition=~models.Q(reason=""),
                name="grant_reason_not_blank",
                violation_error_message="سبب المنح أو السحب مطلوب",
            ),
        ]

    def __str__(self) -> str:
        verb = "منح" if self.granted else "سحب"
        return f"{verb} {self.capability} → {self.user_id}"


class ConsoleRole(models.Model):
    """دورٌ يُنشئه المالك — حزمةُ قدراتٍ لها اسم. T847.

    الأدوار الأربعة الأولى مكتوبةٌ في الشيفرة
    (`apps.core.permissions.ROLE_CAPABILITIES`) وتبقى هناك: صفٌّ في قاعدةٍ يمكن
    حذفُه، وحذفُ «المالك» يُقفل اللوحة على الجميع بلا طريقٍ للعودة. فالمكتوبُ
    أرضيّة، وهذا الجدولُ ما يُضاف فوقها.

    **ولماذا صار الدورُ صفّاً أصلاً:** v1 عنده أحدَ عشرَ دوراً في قائمةٍ
    منسدلة، ومنها ما يكرّر غيرَه بأسماءٍ مختلفة («Admin (مدير)» و«مدير (كل شيء
    عدا الإحصائيات)»، و«Data Entry» و«مدخل بيانات المزادات»). وهي ليست خطأً في
    التسمية — هي أثرُ أن كلَّ حاجةٍ جديدة كانت تُحلّ بدورٍ جديدٍ في الشيفرة،
    فلا أحد يجرؤ على حذف القديم لأنه لا يعرف من يحمله. والصفُّ هنا **يقول من
    يحمله**، فيُحذف حين لا يحمله أحد.

    والقدرات نصوصٌ في `JSONField` لا مفاتيحُ أجنبية: `Capability` تعدادٌ في
    الشيفرة لا جدول، وهو الصواب — قدرةٌ لا تحرس شيئاً يرفضها
    `ops/checks/every_capability_guards_something.py`، وذلك فحصٌ على الشيفرة
    لا على صفوف. فالدورُ يشير إلى القدرات بالاسم، وقدرةٌ اختفت من التعداد
    تُقرأ هنا وتُهمَل عند الحساب بدل أن تكسر كلَّ استعلامٍ على الجدول.
    """

    #: المعرّف الذي يُكتب في `User.console_role`. لاتينيٌّ لأنه يدخل عناوين
    #: ومرشّحات، والاسمُ المعروض عربيٌّ في `label`.
    slug = models.SlugField(max_length=32, unique=True)
    label = models.CharField(max_length=100)

    #: قيمُ `Capability` التي يحملها هذا الدور. يتحقّق منها `clean()`.
    capabilities = models.JSONField(default=list, blank=True)

    #: لماذا وُجد هذا الدور. دورٌ بلا سبب هو الدور الذي لا أحد يعرف بعد سنةٍ
    #: هل يجوز حذفه — وذلك بعينه سببُ أحدَ عشرَ دوراً في v1.
    reason = models.TextField()

    created_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="roles_created",
    )
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "دور لوحة"
        verbose_name_plural = "أدوار اللوحة"
        ordering = ("label",)
        constraints = [
            models.CheckConstraint(
                condition=~models.Q(reason=""),
                name="console_role_reason_not_blank",
                violation_error_message="سبب إنشاء الدور مطلوب",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.label} ({self.slug})"

    def clean(self) -> None:
        """قدرةٌ لا وجود لها تُرفض عند الحفظ لا عند القراءة.

        دورٌ يحمل `"users.delet"` يبدو صحيحاً في الشاشة ولا يمنح شيئاً — وهو
        أسوأ من الرفض: من منحه يظنّ أنه منح.
        """
        from apps.core.permissions import Capability

        known = set(Capability.values)
        unknown = sorted(set(self.capabilities or []) - known)
        if unknown:
            raise ValidationError({"capabilities": f"قدراتٌ لا وجود لها: {unknown}"})


# ---------------------------------------------------------------------------
# وثائقُ العميل — أربعةُ مرفوعاتٍ كانت غائبةً كلُّها
# ---------------------------------------------------------------------------
#
# في v1 أربعةُ أعمدةٍ على `userss`: `cr_file_path` (السجل التجاري) و
# `tax_file_path` (الشهادة الضريبية) و`identity_file_path` (صورة الهوية)،
# و`refunds_requests.iban_image` (صورة الآيبان، **إلزاميّة** على كل طلب استرداد).
# وفي v2 **لا واحدَ منها**: `FileField` في المستودع كلِّه كان أربعةً — ثلاثُ صورِ
# مركبةٍ وإيصالُ تحويل.
#
# والنقصُ ليس تجميليّاً. شركةٌ تسجّل بلا سجلٍّ تجاريٍّ مرفوع لا يستطيع أحدٌ
# التحقّق منها، وفاتورةٌ ضريبيّةٌ بلا شهادةٍ محفوظةٍ لا سند لها عند مراجعةٍ
# زكويّة، و**استردادٌ إلى آيبانٍ بلا صورةٍ تُثبته** هو تحويلُ عشرةِ آلافٍ إلى رقمٍ
# كتبه أحدٌ في خانة — وهو بالضبط ما جعل v1 يفرض الصورة.
#
# ## جدولٌ واحدٌ لا أربعةُ أعمدة
#
# v1 يضعها أعمدةً نصّيّةً على صفّ المستخدم، فلا تاريخَ لها ولا يُعرف من رفعها
# ولا متى، ورفعُ نسخةٍ جديدةٍ **يمحو القديمة** — والقديمةُ هي التي صدرت بها
# فاتورةُ العام الماضي. وهنا صفٌّ لكل رفعة، والأحدثُ هو الساري، والقديمُ باقٍ
# مقروءاً. ولذلك لا قيدَ تفرّدٍ على (المستخدم، النوع): التاريخُ لا يُحذف.


class DocumentKind(models.TextChoices):
    """أنواعُ الوثائق. مُعدَّدةٌ لأن كلَّ نوعٍ له من يطلبه ومن يقرؤه."""

    COMMERCIAL_REGISTER = "cr", "السجل التجاري"
    TAX_CERTIFICATE = "tax", "الشهادة الضريبية"
    NATIONAL_ID = "id", "صورة الهوية"
    IBAN = "iban", "صورة الآيبان"


class CustomerDocument(models.Model):
    """وثيقةٌ رفعها عميلٌ أو رُفعت عنه. صفٌّ لكل رفعة، ولا حذف.

    `uploaded_by` قد يكون العميلَ نفسه أو موظّفاً رفعها عنه على الهاتف. وفارقُ
    الاثنين يُقرأ من الصفّ لا يُخمَّن — «من رفع صورة هوية هذا العميل؟» سؤالُ
    تدقيقٍ حقيقيّ، وجوابُه في v1 غيرُ موجود.
    """

    user = models.ForeignKey(
        "accounts.User", on_delete=models.PROTECT, related_name="documents"
    )
    kind = models.CharField(max_length=8, choices=DocumentKind.choices)

    #: المسارُ مولَّدٌ في `customer_document_path` ولا يحمل اسمَ الرافع ولا نوعَ
    #: الوثيقة: رابطٌ مسرَّبٌ لا يقول لمن هو، ولا يُخمَّن جارُه.
    file = models.FileField(upload_to=customer_document_path)

    note = models.CharField(max_length=200, blank=True)
    uploaded_by = models.ForeignKey(
        "accounts.User",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="+",
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "وثيقة عميل"
        verbose_name_plural = "وثائق العملاء"
        ordering = ("-uploaded_at",)
        indexes = [models.Index(fields=["user", "kind", "-uploaded_at"])]

    def __str__(self) -> str:
        return f"{self.get_kind_display()} — {self.user_id}"

    @classmethod
    def current(cls, user, kind: str):
        """الساريةُ من هذا النوع: الأحدثُ رفعاً، أو لا شيء.

        دالّةٌ لا خاصّةٌ محسوبةٌ على المستخدم، لأن «الأحدث» تعريفٌ يجب أن يكون
        في **موضعٍ واحد**: شاشةُ اللوحة وواجهةُ العميل وأيُّ فحصٍ يسأل عن وجود
        الوثيقة، ثلاثتُها تسأل هنا. وثلاثُ نسخٍ من `order_by("-uploaded_at")`
        هي ثلاثةُ مواضعَ تختلف يومَ يتغيّر معنى «الساري».
        """
        return cls.objects.filter(user=user, kind=kind).first()
