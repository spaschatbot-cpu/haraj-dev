"""درج المظهر: القوائم الأربع التي يجب ألّا تفترق. T833.

لماذا هذه الاختبارات موجودة
===========================
لأن اختيار المظهر يعيش في **أربعة أماكن** لا واحد، ولا شيء يربطها إلا الاتفاق:

1. ``theme.js`` — ``ALLOWED``: ما يُقبل ويُكتب على ``<html>``.
2. ``app.css`` — كتلةٌ لكل قيمة: ما يعنيه أن تُكتب.
3. ``base.html`` — زرٌّ لكل قيمة: ما يستطيع القارئ اختياره.
4. ``ops/checks/console_colours_are_readable.py`` — ما يُقاس تباينه.

وكل افتراقٍ بينها **صامت**: لونٌ في القالب بلا كتلةٍ في الورقة زرٌّ يُنقر ولا
يحدث شيء؛ ولونٌ في الورقة بلا صفٍّ في الحارس لونٌ لا أحد قاسه — وهو الباب
الذي فُتح أصلاً لأجل إغلاقه (زرّ الدخول الراسب في T819).

ولا شيء من ذلك يسقط الحزمة بغير هذه الاختبارات: الصفحة تُرسم، والزرّ يُرسم،
ولا استثناء يُرمى.
"""

from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[2]
SHEET = ROOT / "backend" / "apps" / "console" / "static" / "console" / "app.css"
SCRIPT = ROOT / "backend" / "apps" / "console" / "static" / "console" / "theme.js"
FRAME = ROOT / "backend" / "templates" / "console" / "base.html"
CHECK_PATH = ROOT / "ops" / "checks" / "console_colours_are_readable.py"


def _load_check() -> ModuleType:
    """Import the check from ops/, which is outside any Python package."""
    spec = importlib.util.spec_from_file_location("console_colours", CHECK_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


check = _load_check()


def allowed_in_script() -> dict[str, list[str]]:
    """قوائم `ALLOWED` كما كتبها `theme.js` — تُقرأ ولا تُكرَّر هنا."""
    source = SCRIPT.read_text(encoding="utf-8")
    block = re.search(r"var ALLOWED = \{(.*?)\n  \};", source, re.DOTALL)
    assert block, "لم تُوجد `ALLOWED` في theme.js — إن أُعيدت بنيتها فحدّث هذا الاختبار"
    return {
        name: re.findall(r'"([^"]+)"', values)
        for name, values in re.findall(r"(\w+):\s*\[([^\]]*)\]", block.group(1))
    }


def buttons_in_frame() -> dict[str, set[str]]:
    """ما يستطيع القارئ اختياره فعلاً: `data-look` و`data-value` في القالب."""
    frame = FRAME.read_text(encoding="utf-8")
    found: dict[str, set[str]] = {}
    for name, value in re.findall(r'data-look="(\w+)"\s+data-value="([\w-]+)"', frame):
        found.setdefault(name, set()).add(value)
    return found


# ---------------------------------------------------------------------------
# ١ — الزرّ الذي يُنقر لا بدّ أن يكون مقبولاً


def test_every_button_offers_a_value_the_script_accepts() -> None:
    """زرٌّ بقيمةٍ ليست في `ALLOWED` زرٌّ يُنقر ولا يحدث شيء — بلا خطأ."""
    allowed = allowed_in_script()
    for name, values in buttons_in_frame().items():
        assert name in allowed, f"القالب يعرض `{name}` ولا وجود له في ALLOWED"
        unknown = values - set(allowed[name])
        assert not unknown, f"قيمٌ في القالب يرفضها theme.js: {name}={unknown}"


def test_every_accepted_value_has_a_button() -> None:
    """قيمةٌ مقبولةٌ بلا زرّ خيارٌ لا يصل إليه أحد.

    الاستثناءان مقصودان: `nav` يُبدَّل بمفتاح الطيّ في الشريط العلوي **وله**
    أزراره أيضاً، و`scheme=auto` له زرّه. فما يبقى بلا زرٍّ هو خطأ.
    """
    allowed = allowed_in_script()
    offered = buttons_in_frame()
    for name, values in allowed.items():
        missing = set(values) - offered.get(name, set())
        assert not missing, f"قيمٌ مقبولةٌ بلا زرّ في الدرج: {name}={missing}"


# ---------------------------------------------------------------------------
# ٢ — القيمة المقبولة لا بدّ أن تعني شيئاً في الورقة


def test_every_accent_has_its_own_block_in_the_sheet() -> None:
    """لونٌ أساسيٌّ بلا كتلةٍ في `app.css` يرث درجات سابقه صامتاً."""
    sheet = SHEET.read_text(encoding="utf-8")
    for accent in allowed_in_script()["accent"]:
        pattern = rf':root(?:,\s*:root)?\[data-accent="{accent}"\]'
        assert re.search(pattern, sheet), f"اللون `{accent}` بلا كتلة في app.css"


def test_every_accent_defines_the_same_stops() -> None:
    """درجةٌ ناقصةٌ في لونٍ تعني أن ذلك اللون يستعير درجةَ لونٍ آخر."""
    stops = {"a050", "a300", "a500", "a700", "a-dim"}
    for accent in allowed_in_script()["accent"]:
        tokens = check.palette("light", accent, "auto")
        missing = stops - tokens.keys()
        assert not missing, f"اللون `{accent}` ينقصه: {missing}"


def test_the_breakpoint_is_the_same_number_in_both_files() -> None:
    """نقطة الانكسار مكتوبةٌ في `app.css` و`theme.js` — وافتراقُهما صامت.

    الورقة تجعل الشريط درجاً منزلقاً تحت حدٍّ ما، والسكربت يقرّر تحت الحدّ
    نفسه أن الافتراضي «مغلق». فلو تحرّك أحدهما وحده صار على شاشةٍ بينهما
    شريطٌ ثابتٌ يغطّي المحتوى — أو درجٌ مفتوحٌ لا حجاب له. ولا استثناء يُرمى
    في الحالتين.

    ولماذا لا تُقرأ من مكانٍ واحد: قراءةُ CSS من JS تعني طلباً وتحليلاً عند
    كل إقلاع لأجل رقمٍ واحد. فالثمن اختبارٌ يطابقهما — وهو أرخص.
    """
    sheet = SHEET.read_text(encoding="utf-8")
    script = SCRIPT.read_text(encoding="utf-8")

    in_sheet = set(re.findall(r"@media \(max-width:\s*([\d.]+rem)\)", sheet))
    in_script = set(re.findall(r'matchMedia\("\(max-width:\s*([\d.]+rem)\)"\)', script))

    assert in_script, "لم يعد theme.js يستعلم عن عرض الشاشة — حدّث هذا الاختبار"
    assert in_script <= in_sheet, (
        f"نقطة انكسارٍ في theme.js لا تقابلها قاعدة في app.css: "
        f"{sorted(in_script - in_sheet)}"
    )


# ---------------------------------------------------------------------------
# ٣ — القيمة التي تعني شيئاً لا بدّ أن تُقاس


def test_the_guard_measures_every_combination_the_script_allows() -> None:
    """توليفةٌ تعمل ولا تُقاس هي التوليفة التي يقع فيها اللون الراسب."""
    allowed = allowed_in_script()
    # `accents()` تُشتقّ من الورقة لا تُنسَخ (T855): كانت قائمةً مكتوبةً
    # باليد، فأُضيف لونٌ سابع إلى الورقة والدرج وبقيت هي ستّةً — ولونٌ
    # يُختار ولا يُقاس هو ما وُجد هذا الحارس ليمنعه. وهذا التوكيد هو ما يُبقي
    # الطرفين متساويين: الورقةُ والدرج.
    assert set(check.accents()) == set(allowed["accent"])
    assert set(check.SIDEBARS) == set(allowed["sidebar"])
    # `scheme` وحده يُحَلّ في theme.js: `auto` تصير `light` أو `dark` قبل أن
    # تُكتب على `<html>`، فالورقة لا تعرف إلا اثنتين — والحارس يقيسهما.
    assert set(check.SCHEMES) == set(allowed["scheme"]) - {"auto"}


@pytest.mark.parametrize(
    ("token", "replacement", "expected"),
    [
        # نصٌّ ثانويٌّ فاتح: يسقط على البطاقة والأرضية ورأس الجدول.
        ("  --muted: #5a6b85;", "  --muted: #9aa8bf;", "النصّ الثانوي"),
        # إطار تركيزٍ غامق في المظهر الداكن: العطل الحقيقي الذي كشفه الحارس
        # أول مرّة، ولا يظهر في لقطة شاشة لأنه لا يُرسم إلا مع لوحة المفاتيح.
        ("  --focus: var(--a300);", "  --focus: var(--a700);", "إطار التركيز"),
    ],
)
def test_the_colour_guard_refuses_a_planted_violation(
    tmp_path: Path, token: str, replacement: str, expected: str
) -> None:
    """حارسٌ يمرّ دائماً لا يُميَّز من حارسٍ لا يعمل (المادة ٤).

    فتُزرع المخالفة في نسخةٍ من الورقة — لا في الورقة نفسها، فاختبارٌ يعدّل
    ملفاً في المستودع يترك المستودع مكسوراً إن سقط في منتصفه.
    """
    original = SHEET.read_text(encoding="utf-8")
    assert token in original, f"لم يعد `{token.strip()}` في الورقة — حدّث الاختبار"

    planted = tmp_path / "app.css"
    planted.write_text(original.replace(token, replacement), encoding="utf-8")

    was, check.SHEET = check.SHEET, planted
    try:
        assert check.main() == 1, f"الحارس قبل مخالفة `{expected}`"
    finally:
        check.SHEET = was

    # وبعد الإرجاع يعود نظيفاً — وإلا كان الفشل أعلاه من الورقة لا من الزرع.
    assert check.main() == 0


# ---------------------------------------------------------------------------
# الاستجابة للمقاسات — T842، وما يمكن إثباته بلا متصفّح
# ---------------------------------------------------------------------------
#
# قِيست اللوحة في متصفّح على ٢٦ شاشة وسبعة عروض (2026-09-07)، فوُجد عطلان:
#
#   ٩٠٠ بكسل  · `/console/bids/accepted/` تفيض أفقياً بـ١٤٣ بكسل
#              · `/console/vehicles/catalog/` بـ١٠٥ · `/console/after-sales/` بـ٩٢
#   ٣٢٠ بكسل  · **كل** صفحة تفيض بـ٣٢ بالضبط — رقمٌ ثابت، أي عنصرٌ في الإطار
#
# والقياس نفسه لا يعيش هنا: لا متصفّح في هذه الحزمة، ورندرةُ القالب إلى نصّ
# لا تقول شيئاً عن عرضٍ محسوب. فالمحفوظ هنا هو **السبب** في الورقة — والعرَض
# يُعاد قياسه في متصفّح عند كل تغيير شكلٍ كبير. وهذا حدّ الأداة، ويُقال.

SCROLL_GUARD = ROOT / "ops" / "checks" / "console_tables_scroll.py"


def test_the_sheet_no_longer_flattens_tables_to_blocks() -> None:
    """`display: block` على جدول يُخرج صفوفه من شجرة الوصول.

    كانت الحيلة الوحيدة التي تمرّر الجداول، وتسري تحت ٥٦rem وحدها. حلّ محلّها
    غلافٌ يمرّر في كل مقاس — فكسبنا التمرير فوق ٨٩٦ بكسل، **و**بقاءَ الجدول
    جدولاً، **و**رأساً لاصقاً لا يعتمد على حظّ المحرّك مع كتلةٍ مُمرَّرة.
    """
    #: التعليقات تُفرَّغ أولاً: هذا الملفّ **يشرح** الحيلة المحذوفة عند
    #: تعريف الغلاف، فبحثٌ ساذج يجدها في شرحها ويسقط على نصٍّ صحيح.
    sheet = re.sub(r"/\*.*?\*/", " ", SHEET.read_text(encoding="utf-8"), flags=re.S)

    assert "display: block" not in sheet or "main table" not in sheet
    assert ".scroller {" in sheet
    assert "overflow-x: auto" in sheet


def test_no_auto_fit_track_wider_than_its_container() -> None:
    """`repeat(auto-fit, minmax(21rem, 1fr))` تعني «لا أقلّ من ٢١rem مهما ضاقت».

    وهي سبب الـ٣٢ بكسل الثابتة على ٣٢٠: العمود يصير ٣٣٦ ويدفع الصفحة كلّها.
    والصواب `minmax(min(21rem, 100%), 1fr)` — وهو ما يُقصد دائماً من
    `auto-fit`: «اقسمها ما دامت تتّسع».

    و`auto-fit`/`auto-fill` وحدهما المفحوصان. الشبكةُ ذات المسارات المسمّاة
    (`minmax(17rem, 22rem)` في شاشة الدخول) تعرف عدد أعمدتها وتنهار بقاعدةٍ
    مكتوبة عند ٤٦rem — واختبارٌ يرفضها يرفض شيئاً قِيس أنه لا يفيض.
    """
    sheet = re.sub(r"/\*.*?\*/", " ", SHEET.read_text(encoding="utf-8"), flags=re.S)

    bare = re.findall(
        r"repeat\(\s*auto-(?:fit|fill)\s*,\s*minmax\(\s*(\d+(?:\.\d+)?(?:rem|px|em))\s*,",
        sheet,
    )

    assert bare == [], f"مسارٌ مرن بحدٍّ أدنى مطلق: {bare} — لُفّه بـmin(…, 100%)"


def test_the_top_bar_name_shrinks_instead_of_pushing_the_page() -> None:
    """ابنُ المرن لا ينكمش دون محتواه، فاسمٌ طويل يدفع الشريط خارج الشاشة."""
    sheet = SHEET.read_text(encoding="utf-8")

    user = sheet[sheet.index(".user {") : sheet.index(".user__mark")]

    assert "min-inline-size: 0" in user
    assert "text-overflow: ellipsis" in user


def test_every_console_table_is_wrapped() -> None:
    """الحارس نفسه، مُشغَّلاً — فالقالب الذي يُكتب غداً لا ينسى الغلاف."""
    spec = importlib.util.spec_from_file_location("console_tables", SCROLL_GUARD)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    found, tables = module.offences()

    assert tables > 0, "لا جدول — الحارس يفحص العدم"
    assert found == []
