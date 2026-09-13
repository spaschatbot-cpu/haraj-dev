"""Signing a member of staff in, at a rate a guessing script cannot use. T914.

Customers sign in with a one-time code and every path that sends or spends one
is metered (T602). Staff sign in with a **password**, at Django's admin login,
and that path had no limit at all — an oversight with a straight line from it
to `money.act` and `money.exception`, which are the capabilities that
confiscate a deposit and grant an exception.

Two counters, and neither is redundant — the reasoning is
`apps.accounts.throttling`'s, restated where it applies:

* **per address**, or one machine walks a password list against one account;
* **per account**, or the same machine sprays one likely password across every
  account and trips no per-address limit worth having.

The refusal is a 429 with an Arabic sentence and no hint about whether the
account exists. Django's own login already refuses to say that; a rate limiter
that answered differently for a known name would hand back what the login was
careful not to give.

Why a route rather than a decorator on `AdminSite.login`: `config.urls` mounts
this path *before* `admin.site.urls`, so the limit is visible where the route
is, and nothing monkey-patches an object Django owns. A reader of `urls.py` can
see that staff sign-in is metered without knowing this module exists.

الدخولُ باسمٍ لا برقم — T918
=============================
كان هذا المسار ينتهي إلى `admin.site.login`، وتلك شاشةُ جانغو: عنوانُ خانتها
يأتي من `USERNAME_FIELD` وهو `phone`، فكان الموظّف يدخل **برقم جوّاله**. وقرارُ
المالك بالحرف: «عايز تسجيل دخول الادمن يكون بيوزر و باس، مش بالرقم. الرقم و
الـOTP دا للمستخدمين». وسُئل عن عاملٍ ثانٍ فقال: لا.

فصار المسار `LoginView` من عندنا باستمارةٍ وقالبٍ لنا، والمصادقةُ في
`apps.accounts.backends.StaffUsernameBackend`. **والعدّاد لم يُمَسّ**: الحقلُ
المُرسَل ما زال اسمُه `username`، وهو ما يقرؤه `ACCOUNT_FIELD` — ولو تغيّر اسمُ
الحقل ولم يتغيّر الثابت لصار العدُّ كلُّه على `(anonymous)` والحدُّ بالحساب
ميّتاً بلا أن يشتكي أحد.
"""

from __future__ import annotations

import logging

from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.views import LoginView
from django.http import HttpRequest, HttpResponse
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect

from apps.accounts.models import USERNAME_MAX_LENGTH
from apps.core import ratelimit
from apps.core.net import client_ip

log = logging.getLogger(__name__)

#: The field the sign-in form posts the account under — and the name
#: `StaffSignInForm` posts it under too, which is the half that matters: a
#: renamed input with this constant left behind counts every attempt against
#: `(anonymous)` and the per-account limit dies without a word (T918).
ACCOUNT_FIELD = "username"

REFUSAL = "محاولات دخول كثيرة. انتظر قليلاً ثم أعد المحاولة، أو تواصل مع مسؤول النظام."

#: جملةُ الرفض — **واحدةٌ لكلّ الحالات**: اسمٌ غيرُ موجود، وكلمةٌ خاطئة، وحسابٌ
#: معطَّل، وعميلٌ يحاول. وثلاثتُها تكشف ما لا يُكشَف لو افترقت: «الاسم غير
#: موجود» تُحوّل تخمينَ زوجٍ إلى تخمينِ اسمٍ وحده، و«الحساب معطّل» تقول لمن
#: يخمّن إنه أصاب الاسم والكلمة معاً وإن الباب يُفتح بحسابٍ آخر.
BAD_CREDENTIALS = "اسم الدخول أو كلمة المرور غير صحيحة."


class StaffSignInForm(AuthenticationForm):
    """اسمُ دخولٍ وكلمةُ مرور. ولا عاملَ ثانٍ — سُئل المالك فقال لا."""

    username = forms.CharField(
        label="اسم المستخدم",
        max_length=USERNAME_MAX_LENGTH,
        widget=forms.TextInput(
            attrs={"autofocus": True, "autocomplete": "username", "dir": "ltr"}
        ),
    )

    error_messages = {
        **AuthenticationForm.error_messages,
        "invalid_login": BAD_CREDENTIALS,
        # لا تُقرأ عملياً — `StaffUsernameBackend` يردّ المعطَّل فيصير الخطأ
        # `invalid_login` — ومكتوبةٌ بالجملة نفسها لأن الافتراقَ هنا يوماً ما
        # هو تسريبٌ كامل، ولا يصحّ أن يتوقّف منعُه على مسارٍ لا يمرّ به أحد.
        "inactive": BAD_CREDENTIALS,
    }

    def __init__(self, request=None, *args, **kwargs):
        super().__init__(request, *args, **kwargs)
        # ‏`AuthenticationForm.__init__` تفرض على الخانة طولَ `USERNAME_FIELD`
        # — أي **١٢** (طولُ `9665XXXXXXXX`) — بعد أن أعلنّا ٣٢. فاسمٌ من ١٤
        # حرفاً كان سيُرفض في الاستمارة بجملةٍ عن طولٍ لا معنى له هنا. تُعاد
        # بعد `super()` لا قبله، لأنها تُكتب هناك لا تُقرأ.
        field = self.fields["username"]
        field.max_length = USERNAME_MAX_LENGTH
        field.widget.attrs["maxlength"] = USERNAME_MAX_LENGTH


class StaffSignInView(LoginView):
    """شاشةُ دخول اللوحة. قالبُنا، واستمارتُنا، وخلفيّتُنا."""

    template_name = "console/sign_in.html"
    authentication_form = StaffSignInForm
    # ‏`redirect_authenticated_user` يبقى مطفأً: تشغيلُه يجعل الصفحة تعيد
    # توجيهَ من هو داخلٌ أصلاً، وهي قناةُ كشفٍ صغيرة (يُعرف من ردّ الصفحة أنّ
    # الجلسة قائمة) مقابل راحةٍ لا يطلبها أحد.


_sign_in = StaffSignInView.as_view()


@never_cache
@csrf_protect
def throttled_staff_login(request: HttpRequest) -> HttpResponse:
    """The staff sign-in page, behind a counter on POST only.

    `GET` is not metered: it renders a form, and metering it would let anybody
    lock the login page for a whole office by loading it in a loop — a
    denial-of-service switch dressed as a security control.
    """
    if request.method == "POST":
        refusal = _refuse(request)
        if refusal is not None:
            return refusal

    return _sign_in(request)


def _refuse(request: HttpRequest) -> HttpResponse | None:
    """A 429 when either counter is spent, or ``None`` to let the attempt through.

    Both counters are spent on *every* attempt, right or wrong. Refunding a
    correct one would make the limit meterable — try until it stops counting
    and the password is known — and a staff member who signs in ten times an
    hour has a different problem.
    """
    address = client_ip(request)
    # يُصغَّر كما تُصغّره الخلفيّة: `Ahmad` و`ahmad` حسابٌ واحد، فلو عُدّا
    # مفتاحين لصار الحدُّ بالحساب يُتجاوَز بقلب حرفٍ واحد.
    account = str(request.POST.get(ACCOUNT_FIELD, ""))[:64].strip().lower()

    by_address = ratelimit.consume("staff_login_ip", address)
    # Counted even when the form named no account, under a key of its own: a
    # script posting empty forms must not be free, and must not spend the
    # budget of an account it did not name.
    by_account = ratelimit.consume("staff_login_account", account or "(anonymous)")

    if by_address.allowed and by_account.allowed:
        return None

    log.warning(
        "staff login rate limited: address=%s account=%r "
        "(%s/%s by address, %s/%s by account)",
        address,
        account,
        by_address.count,
        by_address.limit,
        by_account.count,
        by_account.limit,
    )
    response = HttpResponse(REFUSAL, status=429, content_type="text/plain; charset=utf-8")
    response["Retry-After"] = str(max(by_address.retry_after, by_account.retry_after))
    return response


__all__ = ["BAD_CREDENTIALS", "REFUSAL", "StaffSignInForm", "throttled_staff_login"]
