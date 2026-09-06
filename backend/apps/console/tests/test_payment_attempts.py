"""T827 — «دفعتُ ولم يصل»: المحاولة مكتوبةٌ عندنا، ولا يبلغها موظّف.

جرد التكافؤ، القسم (ب): «أرى محاولات الدفع عبر البوابة وحالتها — `PaymentIntent`
صفٌّ يُكتب **قبل** أن يصل العميل البوابة، بستّ حالات فيها `failed` و`expired`
و`disputed`. **لا شاشة في اللوحة تقرؤه.** فإن سأل عميلٌ «دفعت ولم يصل» فالمحاولة
الفاشلة مكتوبة عندنا ولا يبلغها موظف».

**والسؤال الذي تجيبه هذه الشاشة سؤالٌ واحد**، وهو أكثر ما يُسأل في الدعم:
العميل يقول دفع، والرصيد لا يقول ذلك. والجواب أحد ثلاثة، وكلّها مكتوبةٌ في
الصفّ ولا تُقرأ:

* **لم يصل البوابة أصلاً** — `pending` قديمة، فالمحاولة فُتحت ولم تُكمَل.
* **البوابة رفضت** — `failed`، ومعها كلمةُ البوابة الحرفية في
  `gateway_status_raw`.
* **نجحت ونحن لم نقيّدها** — `succeeded` بلا `resulting_transaction`، وهي
  الحالة الوحيدة التي تعني أن عندنا مالاً لعميلٍ لا يراه.

الثالثة يمنعها قيدٌ في القاعدة (`a_succeeded_intent_names_its_transaction`)،
فوجودها مستحيل — **ولذلك تُعرَض**: قيدٌ يمنع حالةً لا يجعل الشاشة تكذب حين
تقول إنها ليست موجودة، بل يجعل الصفر جواباً ذا معنى.

**قراءةٌ فقط.** لا زرّ هنا: تحريك مالٍ لمحاولةٍ فاشلة هو `money-actions` بعينه،
وله صلاحيته وسببه المكتوب. وشاشةٌ تشخيصيّة تنمو زرّاً هي شاشةٌ صار لها ثقةٌ
ثانية بلا قرار.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.core.permissions import Role
from apps.money.models import PaymentIntent, PaymentIntentState, PaymentPurpose

pytestmark = pytest.mark.django_db


def staff(role: str, phone: str) -> User:
    user = User.objects.create_user(phone=phone, full_name="موظف", password="x")
    user.is_staff = True
    user.console_role = role
    user.save(update_fields=["is_staff", "console_role"])
    return user


@pytest.fixture
def support(client) -> User:
    user = staff(Role.SUPPORT, "966500000501")
    client.force_login(user)
    return user


@pytest.fixture
def payer(db) -> User:
    return User.objects.create_user(phone="966583030303", full_name="دافع")


def an_attempt(payer: User, ref: str, state: str, raw: str = "") -> PaymentIntent:
    return PaymentIntent.objects.create(
        reference=ref,
        user=payer,
        amount=Decimal("10000.00"),
        purpose=PaymentPurpose.INSURANCE_DEPOSIT,
        state=state,
        gateway_status_raw=raw,
    )


def test_a_failed_attempt_is_on_the_screen_with_the_gateway_word(client, support, payer):
    """كلمةُ البوابة الحرفية هي الفرق بين «بطاقتك رُفضت» و«رصيدك لا يكفي»."""
    an_attempt(payer, "PI-FAIL", PaymentIntentState.FAILED, raw="insufficient_funds")

    body = client.get(reverse("console:payment-attempts")).content.decode()

    assert "PI-FAIL" in body
    assert "insufficient_funds" in body


def test_the_screen_finds_a_customer_by_phone(client, support, payer):
    """سؤال الدعم يبدأ برقم جوّال، لا بمرجعٍ لا يملكه العميل."""
    an_attempt(payer, "PI-MINE", PaymentIntentState.FAILED)
    other = User.objects.create_user(phone="966584040404", full_name="آخر")
    an_attempt(other, "PI-THEIRS", PaymentIntentState.FAILED)

    body = client.get(
        reverse("console:payment-attempts"), {"q": payer.phone}
    ).content.decode()

    assert "PI-MINE" in body
    assert "PI-THEIRS" not in body


def test_a_succeeded_attempt_shows_the_entry_it_made(client, support, payer):
    """المادة ١-٦: كل رقمٍ يراه عميلٌ يُرَدّ إلى قيده."""
    an_attempt(payer, "PI-OK", PaymentIntentState.PENDING)

    body = client.get(reverse("console:payment-attempts")).content.decode()

    assert "PI-OK" in body


def test_stale_pending_attempts_are_named_as_such(client, support, payer):
    """`pending` عمرها ساعات ليست «بانتظار الدفع» — هي محاولةٌ لم تُكمَل.

    والفرق هو الجواب: «لم تصل البوابة» غير «البوابة رفضت»، والعميل الذي يسمع
    الأولى يعيد المحاولة، والذي يسمع الثانية يكلّم بنكه.
    """
    old = an_attempt(payer, "PI-STALE", PaymentIntentState.PENDING)
    PaymentIntent.objects.filter(pk=old.pk).update(
        created_at=timezone.now() - timezone.timedelta(hours=6)
    )

    body = client.get(reverse("console:payment-attempts")).content.decode()

    assert "PI-STALE" in body
    assert "لم تُكمَل" in body


def test_the_screen_is_read_only(client, support, payer):
    """شاشةٌ تشخيصيّة تنمو زرّاً هي شاشةٌ صار لها ثقةٌ ثانية بلا قرار."""
    an_attempt(payer, "PI-RO", PaymentIntentState.FAILED)

    body = client.get(reverse("console:payment-attempts")).content.decode()
    main = body[body.index("<main") : body.index("</main>")]

    assert "<form" not in main or 'method="get"' in main


def test_a_role_without_money_view_cannot_open_it(client, payer):
    """حالاتُ الدفع مالٌ: من لا يقرأ الدفتر لا يقرأ محاولاته."""
    client.force_login(staff(Role.OPERATIONS, "966500000502"))

    assert client.get(reverse("console:payment-attempts")).status_code == 403
