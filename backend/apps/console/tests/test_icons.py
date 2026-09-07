"""كل صفحةٍ لها أيقونة، وكل أيقونةٍ لها صفحة. T837.

الاتجاهان مقصودان، ولكلٍّ عطلُه:

* **صفحةٌ باسمِ أيقونةٍ لا وجود له** تُرسَم مربّعاً فارغاً في الشريط المطويّ —
  وهو الوضع الذي لا يبقى فيه اسمٌ يُقرأ. والصفحة تُرسم بنجاح، ولا استثناء
  يُرمى: `path_of` تُرجع الفراغ عمداً حتى لا ينهار الشريط أمام موظّف.
* **أيقونةٌ بلا صفحة** رسمٌ يُصان بلا سبب، أو بقيّةُ صفحةٍ حُذفت.

ولا شيء من الاثنين يظهر في اختبارٍ آخر: `test_navigation.py` يفتح الصفحات
ويثبت أنها محروسة، ولا يعرف شيئاً عمّا يُرسم بجوار أسمائها.
"""

from __future__ import annotations

import re

import pytest

from apps.console.dashboard import STAT_ICONS
from apps.console.icons import ICONS, path_of
from apps.console.navigation import DETAIL_PAGES, PAGES, PLANNED
from apps.console.people import CARD_ICONS as CUSTOMER_CARD_ICONS
from apps.console.staff import CARD_ICONS as STAFF_CARD_ICONS

#: أوامر مسارات SVG المسموحة. الأحرف الكبيرة مطلقة والصغيرة نسبية.
#: `Z` تغلق، و`A` قوس، و`M/L/H/V/C/S/Q/T` خطوط ومنحنيات.
COMMANDS = set("MmLlHhVvCcSsQqTtAaZz")


def test_every_sidebar_page_has_an_icon() -> None:
    """صفحةٌ في الشريط بلا أيقونة مربّعٌ فارغ حين يُطوى."""
    naked = [page.url_name for page in PAGES if not page.icon]
    assert not naked, f"صفحاتٌ بلا اسم أيقونة: {naked}"


def test_every_icon_name_resolves_to_a_path() -> None:
    """الاسم الخطأ يُمسَك هنا لا على الشاشة."""
    unknown = [page.url_name for page in PAGES if not page.icon_path]
    assert not unknown, f"أسماءُ أيقوناتٍ لا وجود لها في ICONS: {unknown}"


#: رسومٌ لا يقرؤها صفٌّ في سجلّ — يقرؤها معالجُ السياق مباشرةً.
#:
#: و`exit-door` هي الوحيدة اليوم: سطرُ الخروج في ذيل الشريط **نموذجٌ لا رابط**
#: (`LogoutView` ترفض `GET` منذ جانغو ٥٫٠، ورابطٌ ينهي الجلسة على `GET` ينهيها
#: من أي `<img src>`)، ولذلك لا صفَّ له في `PAGES` — و`test_entry_points.py`
#: يشترط غيابه — ويأتي رسمُه من `context.navigation`.
#:
#: ومكتوبةٌ هنا **صراحةً** كي لا يُوسَّع الحارس فيصمت: من يضيف رسماً ولا يستعمله
#: يجد الحلَّ السهل في إضافة اسمه إلى هذه المجموعة، وسطرُ التعليق هذا هو ما
#: يجعله يتوقّف — لا يدخل هنا إلا رسمٌ **يُقرأ من موضعٍ يُسمّى**.
#: رسومٌ يقرؤها قالبٌ من متغيّرٍ في السياق لا من صفٍّ في السجلّ: بابُ الخروج
#: (لا صفحةَ له)، وتاجُ المالك في صفِّ «إدارة المشرفين». وكلاهما يُقرأ عبر
#: `path_of`، فيسقط `test_the_sign_out_row_gets_its_drawing_from_the_registry`
#: لو حُذف أحدُها من هناك.
DRAWN_OUTSIDE_THE_REGISTRY = {"exit-door", "crown"}

#: ورسومُ بطاقاتِ الشاشات — مُعلَنةٌ في وحداتها لأن هذا الملفّ لا يستطيع بناءها
#: (تحتاج قاعدة بيانات)، وكلُّ واحدةٍ يحرسها اختبارٌ في ملفّ شاشتها.
CARD_ICONS = set(STAFF_CARD_ICONS) | set(CUSTOMER_CARD_ICONS)


def test_no_icon_is_drawn_for_nobody() -> None:
    """رسمٌ لا يستعمله شريطٌ ولا بطاقةٌ ولا مدخلٌ محجوز يُصان بلا سبب."""
    used = (
        {page.icon for page in PAGES}
        | set(STAT_ICONS)
        | {row.icon for row in PLANNED}
        | DRAWN_OUTSIDE_THE_REGISTRY
        | CARD_ICONS
    )
    assert set(ICONS) == used, f"أيقوناتٌ بلا مستعمل: {sorted(set(ICONS) - used)}"


def test_the_sign_out_row_gets_its_drawing_from_the_registry() -> None:
    """سطرٌ يُرسَم خارج السجلّ لا يعني رسماً مكتوباً بيده في قالب.

    و`context.navigation` هي التي تقرأ، فالرسمُ يبقى في `icons.py` مع بقيّة
    الرسوم — ويسقط هذا الاختبار لو حُذف من هناك.
    """
    for name in DRAWN_OUTSIDE_THE_REGISTRY:
        assert path_of(name), f"رسمٌ يقرؤه القالب ولا وجود له: {name}"


def test_no_two_sidebar_pages_carry_the_same_drawing() -> None:
    """رسمان متطابقان في شريطٍ مطويّ يجعلان الصفحتين واحدةً.

    والشريط المطويّ هو الحالة التي تُقاس: هناك لا يبقى إلا الرسم، فصفحتان
    برسمٍ واحد صفّان لا يُميَّز أحدهما من الآخر إلا بالتحويم. وقد وقع فعلاً —
    «لوحة التحليلات» و«لوحة التقارير» كلتاهما `chart` عند إضافة الثانية.
    """
    drawn = [page.icon for page in PAGES if page.icon]
    doubled = {name for name in drawn if drawn.count(name) > 1}
    assert not doubled, f"رسمٌ على أكثر من صفحة: {sorted(doubled)}"


def test_every_planned_entry_resolves_to_a_path() -> None:
    """مدخلٌ محجوزٌ باسمٍ خطأ يُرسَم فراغاً بجوار نصٍّ — صفٌّ نصفُه مفقود."""
    unknown = [row.label for row in PLANNED if not row.icon_path]
    assert not unknown, f"مدخلاتٌ محجوزةٌ بلا رسم: {unknown}"


def test_every_stat_icon_name_resolves_to_a_path() -> None:
    """اسمٌ مصرَّحٌ به في `STAT_ICONS` بلا رسمٍ يُرسَم مربّعاً ملوّناً فارغاً."""
    unknown = [name for name in STAT_ICONS if not path_of(name)]
    assert not unknown, f"أسماءٌ في STAT_ICONS لا وجود لها في ICONS: {unknown}"


#: ومقابلةُ `STAT_ICONS` بلوحةٍ حقيقية في `test_dashboard.py` — هناك يعيش
#: فيكستشر المالك، والمالك وحده يرى كلّ بطاقة.


def test_detail_pages_need_no_icon() -> None:
    """صفحات التفصيل لا تظهر في شريطٍ أصلاً، فلا يُطلب منها رسم.

    مكتوبٌ صراحةً كي لا يُضاف حارسٌ يطلبه منها لاحقاً: `DETAIL_PAGES` صفوفٌ
    للحراسة لا للعرض، وإلزامُها بأيقونةٍ عملٌ بلا قارئ.
    """
    assert all(page.icon == "" for page in DETAIL_PAGES)


@pytest.mark.parametrize("name", sorted(ICONS))
def test_each_path_is_shaped_like_a_path(name: str) -> None:
    """رسمٌ بمسارٍ مشوَّه يُرسَم فراغاً في المتصفّح بلا شكوى.

    ليس تحليلاً كاملاً لـSVG — ذلك يحتاج مكتبة. ثلاثة شروطٍ تمسك الخطأ
    المطبعيّ الواقعي: أن يبدأ بـ`M` (وإلا فلا نقطة بداية)، وألّا يحوي حرفاً
    ليس أمراً ولا رقماً، وأن يحمل رقماً واحداً على الأقل.
    """
    path = ICONS[name]
    assert path.startswith("M"), f"«{name}» لا يبدأ بنقطة بداية"
    assert re.search(r"\d", path), f"«{name}» بلا إحداثيات"

    letters = {character for character in path if character.isalpha()}
    strange = letters - COMMANDS
    assert not strange, f"«{name}» فيه حروفٌ ليست أوامر مسار: {sorted(strange)}"


def test_an_unknown_name_is_empty_not_a_crash() -> None:
    """شريطٌ ينهار لأن اسماً أُخطئ فيه أسوأ من أيقونةٍ غائبة."""
    assert path_of("لا-أيقونة-كهذه") == ""
    assert path_of("") == ""
    assert path_of(None) == ""  # type: ignore[arg-type]
