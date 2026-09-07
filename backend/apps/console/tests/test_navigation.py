"""T802 and T804 — one list, and no link written by hand.

**I2 is checked by walking, not by reading.** For each role this signs in, asks
the sidebar what it offers, then opens *every* page in the registry and records
which ones answer. The two sets must be equal. A page guarded by one capability
and listed under another fails here, and so does a page in the registry that
nobody can open.

That equivalence is what v1 lacked: the menu was one list and the access rules
were another, so a page added to the second and forgotten in the first was
invisible to the people allowed to use it, and a page added to the first and
forgotten in the second was a link everybody could see and nobody could open.
Both happened.
"""

from __future__ import annotations

import dataclasses
import importlib.util
import re
from pathlib import Path

import pytest
from django.urls import NoReverseMatch, reverse

from apps.accounts.models import StaffGrant, User
from apps.console.navigation import (
    PAGES,
    PLANNED,
    SECTIONS,
    Planned,
    capability_for,
    pages_for,
    sidebar_for,
)
from apps.core.permissions import Capability, Role

pytestmark = pytest.mark.django_db

CHECKS = Path(__file__).resolve().parents[4] / "ops" / "checks"
BACKEND = Path(__file__).resolve().parents[3]


def load(name: str):
    spec = importlib.util.spec_from_file_location(name, CHECKS / f"{name}.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def staff(role: str, phone: str = "966501111111") -> User:
    user = User.objects.create_user(
        phone=phone, full_name="موظف", password="console-pass"
    )
    user.is_staff = True
    user.console_role = role
    user.save(update_fields=["is_staff", "console_role"])
    return user


def signed_in(client, user: User):
    client.force_login(user)
    return client


# ---------------------------------------------------------------------------
# I2 — the sidebar and the guards are the same list
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "role", [Role.OWNER, Role.OPERATIONS, Role.FINANCE, Role.SUPPORT]
)
def test_the_sidebar_offers_exactly_what_the_role_can_open(client, role):
    """The acceptance criterion, walked rather than asserted from the registry."""
    user = staff(role)
    signed_in(client, user)

    offered = {page.url_name for page in pages_for(user)}

    opens = set()
    for page in PAGES:
        response = client.get(reverse(page.url_name))
        if response.status_code == 200:
            opens.add(page.url_name)

    assert offered == opens, (
        f"القائمة تعرض {sorted(offered)} والصفحات التي تفتح {sorted(opens)}"
    )


def test_a_page_the_role_cannot_open_is_a_403_not_a_blank_page(client):
    """Refused loudly. A page that renders empty is how v1 shipped a broken one."""
    user = staff(Role.OPERATIONS)
    StaffGrant.objects.create(
        user=user,
        capability=Capability.DIAGNOSTICS_VIEW,
        granted=False,
        reason="تحت المراجعة",
    )
    signed_in(client, user)

    response = client.get(reverse("console:why-no-bid"))

    assert response.status_code == 403


def test_a_customer_cannot_reach_the_console_at_all(client):
    customer = User.objects.create_user(
        phone="966509999999", full_name="عميل", password="x"
    )
    signed_in(client, customer)

    assert client.get(reverse("console:home")).status_code == 403


def test_an_anonymous_visitor_is_sent_to_sign_in(client):
    """Sent *to sign-in* — the name is the assertion, so it must be asserted.

    This test accepted `302` to anywhere for the whole of phase 009, and stayed
    green while the redirect landed on a 404: `LOGIN_URL` was unset, so Django
    aimed every guarded page at its own `/accounts/login/`, which this project
    has never routed (T821). A test whose name claims more than it checks is
    worse than a missing one — the missing test gets written, the claiming one
    gets believed.
    """
    response = client.get(reverse("console:home"), follow=True)

    assert response.status_code == 200
    landed = response.redirect_chain[-1][0]
    assert landed.startswith(reverse("admin-login"))
    assert f"next={reverse('console:home')}" in landed
    assert 'name="password"' in response.content.decode()


def test_every_page_in_the_registry_has_a_capability():
    """A page with no capability is a page with no guard."""
    for page in PAGES:
        assert page.capability, f"{page.url_name} بلا صلاحية"
        assert capability_for(page.url_name) == page.capability


def test_every_page_in_the_registry_actually_resolves():
    """A registry row naming a url that does not exist is a sidebar 500."""
    for page in PAGES:
        assert reverse(page.url_name)


def test_an_empty_section_is_not_shown(client):
    """A heading with nothing under it is a promise the reader cannot use."""
    user = staff(Role.OPERATIONS)
    StaffGrant.objects.create(
        user=user,
        capability=Capability.DIAGNOSTICS_VIEW,
        granted=False,
        reason="لا يحتاجها",
    )

    labels = {section["label"] for section in sidebar_for(user)}

    assert "التشخيص" not in labels


def test_the_rendered_sidebar_shows_the_pages_the_person_has(client):
    """I6 in miniature: the page is read, not merely counted as a 200."""
    user = staff(Role.SUPPORT)
    signed_in(client, user)

    body = client.get(reverse("console:home")).content.decode()

    assert "ليه ما يقدرش يزايد؟" in body
    assert reverse("console:why-no-bid") in body


def test_the_environment_is_named_on_every_page(client, settings):
    """Article 5-6, so nobody acts on production thinking it is staging."""
    signed_in(client, staff(Role.OWNER))

    body = client.get(reverse("console:home")).content.decode()

    assert settings.ENVIRONMENT_NAME in body


# ---------------------------------------------------------------------------
# T804 — the prefix is a setting, so no link may be a literal
# ---------------------------------------------------------------------------


def test_the_console_lives_under_app_base(settings):
    assert reverse("console:home") == f"/{settings.APP_BASE}/"


def test_no_link_in_the_tree_is_written_by_hand():
    assert load("console_urls_are_named").violations() == []


def test_no_template_puts_unlocalize_before_its_default():
    """حارسٌ يعمل ولا يُشغَّل هو حارسٌ لا يعمل. T830د.

    `ops/checks/default_runs_before_unlocalize.py` كُتب في T836 ولم يُوصَل
    بالحزمة، فبقي يُشغَّل بـ`just lint` وحدها — و`just` هنا يبدأ كل أمرٍ
    بـ`uv run`، وهو غير مثبَّت (CLAUDE.md §7). فمرَّت الحزمةُ **خضراءَ على
    إحدى عشرة مخالفةً أُدخلت في هذه الجلسة نفسها**، ولم يُمسَك إلا بتشغيلٍ
    يدويّ صادف أن جرى.

    وهذا أسوأ من حارسٍ يمرّ دائماً (المادة ٤): ذاك لا يُميَّز من حارسٍ لا
    يعمل، وهذا **يظهر في قائمة الحرّاس كأنه يعمل** ولا يُنادى أصلاً.

    والعطل الذي يحرسه: `unlocalize` يحوّل `None` إلى السلسلة `"None"`، فلا
    يقع `default` بعدها — أي أن الخانة التي يُراد لها `—` تكتب **`None`**
    أمام موظّف.
    """
    check = load("default_runs_before_unlocalize")
    assert check.offenders() == []


def test_no_template_writes_a_class_nothing_styles():
    """حارسٌ يعمل ولا يُشغَّل هو حارسٌ لا يعمل — والدرسُ وقع هنا مرّتين. T852.

    والعطل الذي يحرسه وقع فعلاً: `class="stats"` كُتب على ثلاث شاشات و**لا
    قاعدةَ تصفه** — الاسمُ الصحيح `board-stats`، أربعةُ أحرفٍ بعيداً وموجودٌ في
    الورقة. فرُسمت الصفحات، ولم يخطئ شيء: صنفٌ بلا قاعدة ليس خطأً في أي طبقة.
    وكلُّ فحصٍ بقي أخضر، والبطاقات تنزل واحدةً تحت واحدةٍ على طول الصفحة.

    وهذا شكلُ العطل الذي يحرسه: لا انهيار، ولا رقمٌ خطأ — اسمٌ يبدو صحيحاً ولا
    يفعل شيئاً. ولا يُلاحَظ حتى يفتح أحدٌ الصفحة فتبدو **غريبةً** وحسب،
    و«غريبة» يحملها المراجع على الذوق لا على العطل.
    """
    check = load("every_class_is_styled")
    assert check.violations() == []


HAND_WRITTEN_HREF = """
<a href="/console/vehicles">المركبات</a>
"""

HAND_WRITTEN_ACTION = """
<form action="/admin2/save" method="post"></form>
"""

RELATIVE_PATH = """
<a href="/some/other/page">صفحة</a>
"""


@pytest.mark.parametrize(
    "markup",
    [
        pytest.param(HAND_WRITTEN_HREF, id="an href to a console path"),
        pytest.param(HAND_WRITTEN_ACTION, id="a form posting to a v1 panel path"),
        pytest.param(RELATIVE_PATH, id="any absolute path at all"),
    ],
)
def test_the_check_speaks_on_a_hand_written_link(tmp_path: Path, markup):
    (tmp_path / "page.html").write_text(markup, encoding="utf-8")

    found = load("console_urls_are_named").violations(templates=tmp_path, python=[])

    assert found, "الفحص سكت عن رابط مكتوب بيده"


PYTHON_PATH_LITERAL = """
def go():
    return redirect("/console/home")
"""


def test_the_check_speaks_on_a_python_path_literal(tmp_path: Path):
    (tmp_path / "views.py").write_text(PYTHON_PATH_LITERAL, encoding="utf-8")

    found = load("console_urls_are_named").violations(
        templates=tmp_path / "nothing", python=[tmp_path]
    )

    assert found


@pytest.mark.parametrize(
    "markup",
    [
        pytest.param("<a href=\"{% url 'console:home' %}\">x</a>", id="a url tag"),
        pytest.param('<a href="{{ next }}">x</a>', id="a variable"),
        pytest.param('<a href="#top">x</a>', id="a fragment"),
        pytest.param('<a href="https://example.com">x</a>', id="an external link"),
    ],
)
def test_the_check_is_quiet_on_a_link_that_follows_the_prefix(tmp_path: Path, markup):
    """A check that fires on correct code is one people switch off."""
    (tmp_path / "page.html").write_text(markup, encoding="utf-8")

    assert load("console_urls_are_named").violations(templates=tmp_path, python=[]) == []


def test_every_sidebar_page_says_what_it_does():
    """اسمٌ بلا سطرٍ يشرحه أسوأ من لا شيء — ولا استثناء.

    الاسم يقول أين تذهب، والسطر يقول لماذا؛ والفرق بينهما هو كلُّ ما يضيفه
    الشرح. وصفٌّ يُضاف إلى السجلّ بلا سطر يصير في الشريط اسماً مجرَّداً،
    فتعود الشاشة نسخةً من جارتها في نظر من يقرأ.

    وكان `console:home` مستثنى حين كان شبكةَ كروتٍ لا تُرسم فيها نفسُها. صار
    الجذرُ لوحةَ التحليلات، والسطرُ يُقرأ من الشريط — فلا استثناء بقي.
    """
    missing = [page.url_name for page in PAGES if not page.blurb.strip()]

    assert missing == [], f"شاشات بلا سطر يشرحها: {missing}"


def test_the_sidebar_carries_the_line_that_says_what_each_screen_does(client):
    """السطر يصل الصفحة المرسومة، لا السجلَّ وحده.

    وهذا هو قارئ `Page.blurb` الوحيد بعد أن حلّت لوحةُ التحليلات محلَّ شبكة
    الكروت في الجذر. وبلا هذا الاختبار يصير الحقلُ أعلاه حقلاً مطلوباً لا
    يقرؤه أحد — وحارسٌ يحرس ما لا يُعرض ليس حارساً (المادة ٤).

    ويُقرأ من صفحةٍ ليست الجذر: الشريط في كل صفحة، وذلك بعينه ما تغيّر —
    الشرحُ كان يُقرأ مرّةً عند الدخول، وصار مقروءاً حين يُحتاج.
    """
    signed_in(client, staff(Role.OWNER))

    body = client.get(reverse("console:vehicles")).content.decode()

    for page in PAGES:
        assert page.blurb in body, f"سطر {page.url_name} لم يصل الشريط"


def test_the_root_is_the_analytics_board_itself(client):
    """جذرُ اللوحة هو اللوحة، كما هو في v1 — لا صفحةٌ تسبقها.

    كان الجذر شبكةَ كروتٍ و«لوحة التحليلات» مدخلاً ثانياً تحته في القسم نفسه،
    فيُفتح الجذرُ كلَّ صباح ويُغادَر فوراً إلى الرابط الذي تحته مباشرة.

    ويُقاس برقمٍ من اللوحة لا بالحالة 200: صفحةٌ فارغة تُرجع 200 أيضاً.
    """
    signed_in(client, staff(Role.OWNER))

    response = client.get(reverse("console:home"))

    assert response.status_code == 200
    assert "إجمالي التأمين" in response.content.decode()


def test_no_second_url_shows_the_board(client):
    """عنوانان لصفحةٍ واحدة يعنيان إشارتين محفوظتين ومسارين لزيارةٍ واحدة."""
    with pytest.raises(NoReverseMatch):
        reverse("console:dashboard")


# ---------------------------------------------------------------------------
# I2-ب — المدخل المحجوز: يُعرض ولا يُفتح (T831)
# ---------------------------------------------------------------------------


def test_nothing_is_promised_and_built_at_once():
    """صفٌّ في `PLANNED` وشاشتُه تعمل هو الكذبة التي يخلقها هذا التصميم.

    الخطأ المتوقَّع حرفياً: تُبنى الشاشة، ويُضاف صفُّها في `PAGES`، ويُنسى
    حذفُ صفِّها من `PLANNED` — فيرى الموظّف الاسم مرّتين، إحداهما تقول
    «قريباً» وهو يستطيع فتحها من السطر الذي فوقها. ولا شيء يسقط بغير هذا:
    الصفحة تُرسَم، والحارس يمرّ، والشريط يعرض الاثنين بلا شكوى.
    """
    built = {page.label for page in PAGES}
    promised = {row.label for row in PLANNED}
    both = built & promised
    assert not both, f"مبنيٌّ وموعودٌ به معاً: {sorted(both)}"


def test_a_planned_row_names_a_section_that_exists():
    """قسمٌ لا وجود له يعني صفّاً لا يظهر في أي مكان — غيابٌ صامت."""
    keys = {section.key for section in SECTIONS}
    astray = [row.label for row in PLANNED if row.section not in keys]
    assert not astray, f"مدخلاتٌ في أقسامٍ لا وجود لها: {astray}"


def test_the_sidebar_shows_every_section_now(client):
    """القائمة كاملةٌ لمن يفتحها — وهو الطلب الذي أنشأ `PLANNED` أصلاً.

    كان `sidebar_for` يُسقط القسم الفارغ، فكان المالك يرى أربعةَ أقسامٍ من
    أحدَ عشر ويقرأ ذلك «اللوحة فقدت صفحاتي».
    """
    user = staff(Role.OWNER)
    signed_in(client, user)
    shown = {section["label"] for section in sidebar_for(user)}
    assert shown == {section.label for section in SECTIONS}


def test_a_planned_entry_is_not_a_link(client):
    """`<span>` لا `<a>` معطّل: المعطّل يبقى في ترتيب المفاتيح ويُفتح بالنقر
    الأوسط في تبويبٍ فارغ، ويُنسَخ رابطُه فيُرسَل إلى زميل.

    ويُقرأ من الصفحة المرسومة لا من الشجرة: القالب هو ما قد يتغيّر.
    """
    signed_in(client, staff(Role.OWNER))
    body = client.get(reverse("console:home")).content.decode()

    for row in PLANNED:
        assert row.label in body, f"«{row.label}» لا تظهر في الشريط"

    for match in re.findall(r"<span class=\"nav__soon\"[^>]*>", body):
        assert "href" not in match, f"مدخلٌ محجوزٌ يحمل رابطاً: {match}"


def test_a_planned_entry_says_so_in_words_not_only_in_colour(client):
    """الحالة محمولةٌ على نصّ: من لا يميّز التخفيت يقرأ «قريباً» كما يراها."""
    signed_in(client, staff(Role.OWNER))
    body = client.get(reverse("console:home")).content.decode()
    assert body.count("nav__tag") == len(PLANNED)
    assert "قريباً" in body
    # و«تُبنى غيرها» للأربع التي قرارُها ألّا تُنقل كما هي (نظام الكروت).
    assert "تُبنى غيرها" in body
    assert body.count("تُبنى غيرها") == sum(1 for row in PLANNED if row.rebuilt)


def test_planned_rows_carry_no_url_and_no_capability():
    """لا `url_name` ولا `capability` **في بنية الصنف** لا بشرطٍ يُنسى.

    مكتوبٌ صراحةً كي يسقط من يضيف أحدهما لاحقاً «تسهيلاً»: الحقل الأول يجعل
    `reverse()` ممكناً فيصير الصفُّ رابطاً، والثاني يخترع قدرةً لا تحرس
    شيئاً — و`every_capability_guards_something` يرفضها.
    """
    fields = {field.name for field in dataclasses.fields(Planned)}
    assert "url_name" not in fields
    assert "capability" not in fields
