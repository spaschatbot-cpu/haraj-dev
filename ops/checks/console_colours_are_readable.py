"""كل زوج لون/خلفية في اللوحة يبلغ حدّ WCAG المطلوب له — في **كل** توليفة مظهر.

لماذا فحصٌ لا مراجعةٌ بالعين
============================
لأن العين لا تقيس. صُمّمت اللوحة (T819) بلوحة ألوان تبدو هادئة ومقروءة، وكان
فيها **زرّ تسجيل الدخول نفسه** راسباً: أبيض على ``#3d9bd6`` نسبته ٣٫٠٦ والحدّ
٤٫٥. ومعه ثلاثة أخرى، أخبثها أن الرابط كان **يفتحّ** عند مرور المؤشر — فإشارة
«هذا قابل للنقر» كانت تجعله أصعب قراءةً، وهو عكس ما أُريد بها بالضبط.

ولا شيء من ذلك يظهر في لقطة شاشة، ولا يقوله مراجعٌ ينظر إلى صفحةٍ على شاشةٍ
جيدة في غرفةٍ مضاءة. يظهر في رقم، فهذا الملف يحسب الرقم.

ولماذا صار يفحص توليفاتٍ لا لوحةً واحدة (T833)
===============================================
لأن المالك صار يختار: مظهرٌ فاتح أو داكن، ولونٌ أساسيٌّ من ستّة، وشريطٌ جانبيٌّ
يتبع المظهر أو يُختار له لونٌ من ثلاثة. أي **٤٨ لوحةَ ألوانٍ** تعمل بها اللوحة
فعلاً، لا واحدة.

ولوحةٌ يختارها المستخدم بلا حارسٍ هي بابٌ مفتوحٌ لاختيارٍ لا يُقرأ: الكهرماني
``#e39411`` مقروءٌ حدًّا لمكوّنٍ على أبيض وراسبٌ نصًّا عليه — فلو اختير لصار كل
رابطٍ في اللوحة رمادياً باهتاً، ولا أحد يقيس. فالفحص يركّب الطبقات كما يركّبها
المتصفّح ويقيس الأزواج في كل توليفة.

كيف تُركَّب الطبقات
===================
``app.css`` يعرّف اللون في أربع طبقاتٍ تتراكم:

1. ``:root`` — المحايدات وألوان الحالة (الحالة الفاتحة).
2. ``:root[data-accent="X"]`` — درجات اللون الأساسي وحدها.
3. ``:root[data-scheme="dark"]`` — يقلب المحايدات.
4. ``:root[data-sidebar="X"]`` — الشريط الجانبي وحده.

وهذا الملف يقرأ الكتل بمحدّداتها، ويدمجها بالترتيب نفسه، ثم **يفكّ**
``var(--x)`` — لأن الورقة تربط ``--brand-dark`` بـ``--a700`` في الفاتح
وبـ``--a300`` في الداكن، وقيمةٌ مكتوبةٌ مرّتين قيمتان تفترقان.

حدّان لا حدّ واحد
=================
* **٤٫٥** للنصّ العادي (WCAG 2.2 AA، معيار 1.4.3). كل ما في اللوحة نصٌّ عادي:
  أصغر مقاس فيها ``.68rem`` وأكبر عنوان ``1.45rem`` — ولا شيء يبلغ حدّ «النصّ
  الكبير» (18.66px غليظاً أو 24px عادياً)، فلا استثناء يُطلب هنا.
* **٣٫٠** لمكوّنات الواجهة وحدودها (معيار 1.4.11): إطار التركيز، وحدّ الحقل.

لماذا الأزواج مكتوبة بيدٍ هنا
=============================
لأن السؤال ليس «ما الألوان الموجودة» بل «ما الذي يُرسَم فوق ماذا» — وذلك لا
يُستخرج من ورقة أنماط بلا متصفّح يحسب التتالي. فكل زوجٍ هنا موضعٌ حقيقي في
``app.css``، ومعه اسمه بالعربية ليقول تقريرُ الفشل أين ينظر القارئ.

وحين يُضاف زوجٌ جديد إلى الورقة يجب أن يُضاف هنا. هذه هي كلفة الطريقة، وهي
أرخص من كلفة زرٍّ لا يُقرأ.
"""

from __future__ import annotations

import itertools
import re
import sys
from pathlib import Path

# ويندوز: cp1252 لا يمثّل العربية، فجملة النجاح نفسها ترمي `UnicodeEncodeError`
# ويخرج الحارس بـ1 وهو ناجح. وحارسٌ يُبلَّغ عنه فاشلاً وهو ناجح يُطفَأ بعد
# ثالث مرة — وهذا أسوأ من حارسٍ لا يعمل، لأنه يُطفأ عن قناعة.
#
# و`hasattr` ليست حذراً زائداً: `tests/test_no_float_check.py` يستورد هذا
# الملف، وpytest يكون قد استبدل `sys.stdout` بكائن التقاطٍ بلا `reconfigure`.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[2]
SHEET = ROOT / "backend" / "apps" / "console" / "static" / "console" / "app.css"

#: النصّ العادي، ومكوّنات الواجهة. لا ثالث لهما في هذه اللوحة.
TEXT = 4.5
UI = 3.0

SCHEMES = ("light", "dark")
SIDEBARS = ("auto", "light", "dark", "gradient")


def accents() -> tuple[str, ...]:
    """الألوان الأساسية **مقروءةً من الورقة** لا مكتوبةً هنا.

    كانت قائمةً منسوخة، فأُضيف لونٌ سابع إلى `app.css` و`theme.js` وبقيت هي
    ستّةً — **فصار لونٌ يُختار من الدرج ولا يُقاس تباينُه أبداً**، وهو بالضبط
    ما وُجد هذا الملفّ ليمنعه. وحارسٌ يحرس قائمةً منسوخة يحرس أمسَ لا اليوم.

    والاشتقاقُ من `[data-accent="…"]` لأنه المصدر الذي يقرؤه المتصفّح فعلاً:
    لونٌ في `theme.js` بلا كتلةٍ هنا لا يغيّر شيئاً، وكتلةٌ هنا بلا زرٍّ في
    الدرج تبقى مقيسةً بلا ضرر.
    """
    found = ACCENT_BLOCK.findall(SHEET.read_text(encoding="utf-8"))
    if not found:
        raise SystemExit(f"لم يُعثر على لونٍ أساسيٍّ واحد في {SHEET}")
    # `dict.fromkeys` لا `set`: الترتيب يبقى ترتيبَ الورقة فتُقرأ الرسالة كما
    # يقرأ المطوّرُ ملفَّه.
    return tuple(dict.fromkeys(found))


#: كتلةُ لونٍ أساسيّ: `:root[data-accent="NAME"]`.
ACCENT_BLOCK = re.compile(r':root\[data-accent="([\w-]+)"\]')

#: كتلةُ أنماطٍ: محدّدها ثم ما بين قوسيها. `[^{}]*` لأن كتل اللون لا تتداخل.
BLOCK = re.compile(r"(:root[^{]*)\{([^{}]*)\}")
DECLARATION = re.compile(r"--([\w-]+):\s*([^;]+);")
VAR = re.compile(r"var\(\s*--([\w-]+)\s*\)")


#: تعليقات CSS. تُحذف **قبل** قراءة المحدّدات، لأن تعليق الورقة نفسه يشرح
#: الطبقات ويذكر `[data-scheme="dark"]` بالحرف — فبقاؤه يجعل الكتلة الأساسية
#: تبدو كأنها للمظهر الداكن وحده، وتخرج اللوحة الفاتحة من الفحص كلّه بلا صوت.
#: (وهذا ما حدث بالفعل عند أول تشغيل: `KeyError: 'ink'` لا رسالةَ فشلٍ مفهومة.)
COMMENT = re.compile(r"/\*.*?\*/", re.DOTALL)


def _blocks() -> list[tuple[str, dict[str, str]]]:
    """(المحدّد, تصريحاته) لكل كتلة `:root` في الورقة، بترتيب الورقة."""
    text = COMMENT.sub(" ", SHEET.read_text(encoding="utf-8"))
    found = [
        (selector.strip(), dict(DECLARATION.findall(body)))
        for selector, body in BLOCK.findall(text)
    ]
    if not found:
        raise SystemExit(
            "لا كتلة :root في app.css — إن أُعيدت بنيتها فحدّث هذا الفحص. "
            "حارسٌ لا يجد ما يحرسه يجب أن يصرخ لا أن يمرّ."
        )
    return found


def _matches(selector: str, scheme: str, accent: str, sidebar: str) -> bool:
    """هل تنطبق هذه الكتلة على هذه التوليفة؟

    المحدّد قد يجمع أكثر من `:root` بفاصلة (`:root, :root[data-accent="azure"]`)
    فتكفي مطابقة واحدٍ منها — كما يفعل المتصفّح.
    """
    chosen = {"scheme": scheme, "accent": accent, "sidebar": sidebar}
    for one in selector.split(","):
        wanted = dict(re.findall(r'\[data-(\w+)="([^"]+)"\]', one))
        if all(chosen.get(key) == value for key, value in wanted.items()):
            return True
    return False


def palette(scheme: str, accent: str, sidebar: str) -> dict[str, str]:
    """اللوحة كما يراها المتصفّح: الكتل المنطبقة مدموجةً، و`var()` مفكوكة."""
    merged: dict[str, str] = {}
    for selector, declarations in _blocks():
        if _matches(selector, scheme, accent, sidebar):
            merged.update(declarations)

    # فكّ `var()` بالتكرار: `--brand-soft: var(--a-dim)` قد يشير إلى قيمةٍ
    # أُعلنت في كتلةٍ لاحقة. سبع دوراتٍ أكثر من كافيةٍ لسلسلةٍ عمقُها اثنان،
    # والخروج بعدها يمنع حلقةً لا تنتهي عند `--a: var(--a)`.
    for _ in range(7):
        changed = False
        for name, value in list(merged.items()):
            reference = VAR.search(value)
            if reference and reference.group(1) in merged:
                merged[name] = merged[reference.group(1)]
                changed = True
        if not changed:
            break

    return {name: value.strip() for name, value in merged.items()}


def _relative_luminance(colour: str) -> float:
    raw = [int(colour.lstrip("#")[i : i + 2], 16) / 255 for i in (0, 2, 4)]
    linear = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in raw]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def over(foreground: str, background: str, alpha: float) -> str:
    """اللون الناتج حين يُرسم ``foreground`` بشفافيّة ``alpha`` فوق خلفيّته.

    موجودٌ لأن الشفافيّة تكذب على العين ولا تكذب على الحساب: أبيضُ بـ٠٫٨٢ فوق
    `--a700` يبدو أبيض وهو `#d0dde5`، ونسبته ٤٫٢٣ لا ٥٫٤٨ — أي **راسب**. وقع
    ذلك في لوحة صفحة الدخول (T827) وكُشف بهذه الدالّة لا بالنظر.
    """
    front = [int(foreground.lstrip("#")[i : i + 2], 16) for i in (0, 2, 4)]
    back = [int(background.lstrip("#")[i : i + 2], 16) for i in (0, 2, 4)]
    mixed = (round(front[i] * alpha + back[i] * (1 - alpha)) for i in range(3))
    return "#" + "".join(f"{value:02x}" for value in mixed)


def contrast(foreground: str, background: str) -> float:
    a, b = _relative_luminance(foreground), _relative_luminance(background)
    high, low = max(a, b), min(a, b)
    return (high + 0.05) / (low + 0.05)


def pairs_for(t: dict[str, str]) -> list[tuple[str, str, str, float]]:
    """(الوصف, المقدمة, الخلفية, الحدّ) — كل ما يُرسَم فوق شيءٍ في اللوحة."""
    white = "#ffffff"
    return [
        ("النصّ الأساسي على الأرضية", t["ink"], t["ground"], TEXT),
        ("النصّ الأساسي على البطاقة", t["ink"], t["panel"], TEXT),
        ("النصّ الثانوي على البطاقة", t["muted"], t["panel"], TEXT),
        ("النصّ الثانوي على الأرضية", t["muted"], t["ground"], TEXT),
        ("رأس الجدول", t["muted"], t["raised"], TEXT),
        ("صفٌّ عند المرور", t["ink"], t["raised"], TEXT),
        ("شارة البيئة (غير الإنتاج)", t["muted"], t["raised"], TEXT),
        ("شارة التطوير", t["info"], t["info-soft"], TEXT),
        ("شارة الإنتاج", white, t["danger-strong"], TEXT),
        # الشريط الجانبي: لونه يُختار مستقلاً عن المظهر، فأزواجه تُقاس بلونه هو.
        ("وصف الشريط الجانبي", t["side-dim"], t["side"], TEXT),
        ("اسم اللوحة في الشريط", t["side-ink"], t["side"], TEXT),
        ("مربّع الهويّة في الشريط", "#ffffff", t["a700"], TEXT),
        ("رابط القائمة", t["side-ink"], t["side"], TEXT),
        ("رابط القائمة عند المرور", t["side-ink"], t["side-hover"], TEXT),
        ("القسم الحالي في القائمة", t["side-accent"], t["side-hover"], TEXT),
        ("شريط القسم الحالي", t["side-accent"], t["side"], UI),
        ("عنوان القسم في الشريط", t["side-dim"], t["side"], TEXT),
        ("زرّ الإرسال", white, t["brand-solid"], TEXT),
        ("رابط في المحتوى", t["brand-dark"], t["panel"], TEXT),
        ("رابط في المحتوى عند المرور", t["ink"], t["panel"], TEXT),
        ("إطار التركيز على البطاقة", t["focus"], t["panel"], UI),
        ("إطار التركيز على الأرضية", t["focus"], t["ground"], UI),
        ("حدّ الحقل", t["field-border"], t["panel"], UI),
        # `--brand` دورُه الثالث المكتوب في رأس الورقة: «ما ليس نصّاً — حدٌّ،
        # إطار، تدرّج. الحدّ ٣:١». وكان **بلا زوجٍ يقيسه**، فالورقةُ تُعلن
        # قاعدةً لا يحرسها أحد. وأُضيف حين كُشف: لونٌ أساسيٌّ فاتح يمرّ في كل
        # الفحوص ثم لا تُرى حدودُ البطاقات على الشاشة.
        ("حدُّ اللون الأساسي على البطاقة", t["brand"], t["panel"], UI),
        ("حدُّ اللون الأساسي على الأرضية", t["brand"], t["ground"], UI),
        # الرسائل الموسومة — لونها هو لون حالتها على خلفية حالتها.
        ("رسالة نجاح", t["ok"], t["ok-soft"], TEXT),
        ("رسالة رفض", t["danger"], t["danger-soft"], TEXT),
        ("رسالة تحذير", t["warn"], t["warn-soft"], TEXT),
        ("رسالة معلومة", t["info"], t["info-soft"], TEXT),
        # لوحة التحليلات — لونٌ بلا زوجٍ هنا لونٌ بلا ضمان.
        ("رقم المال على البطاقة", t["money"], t["panel"], TEXT),
        ("رقم المزاد على البطاقة", t["auction"], t["panel"], TEXT),
        ("رقم الناس على البطاقة", t["people"], t["panel"], TEXT),
        ("تفصيل البطاقة", t["ink-soft"], t["panel"], TEXT),
        ("رقم التنبيه على خلفيته", t["warn"], t["warn-soft"], TEXT),
        ("رقم الإنذار على خلفيته", t["danger"], t["danger-soft"], TEXT),
        ("حافة بطاقة المال", t["money"], t["panel"], UI),
        ("حافة بطاقة المزاد", t["auction"], t["panel"], UI),
        # صفحة الدخول: لوحةُ الهويّة متدرّجةٌ من `--a700` إلى كحليّ ثابت،
        # وطرفُ `--a700` هو الأفتح — أي الحالة الأسوأ لنصٍّ أبيض فوقه.
        ("لوحة الدخول: العنوان", white, t["a700"], TEXT),
        ("لوحة الدخول: السطر الوصفي", over(white, t["a700"], 0.9), t["a700"], TEXT),
        ("لوحة الدخول: الحبّة", white, over("#000000", t["a700"], 0.18), TEXT),
        ("لوحة الدخول: مربّع الحرف", white, t["a700"], TEXT),
        # درج المظهر.
        ("خيار المظهر غير المختار", t["muted"], t["panel"], TEXT),
        ("خيار المظهر المختار", t["brand-dark"], t["brand-soft"], TEXT),
        ("زرّ الشريط العلوي عند المرور", t["brand-dark"], t["brand-soft"], TEXT),
        ("حرف المستخدم في دائرته", t["brand-dark"], t["brand-soft"], TEXT),
    ]


def main() -> int:
    combinations = list(itertools.product(SCHEMES, accents(), SIDEBARS))
    failures = []
    measured = 0

    for scheme, accent, sidebar in combinations:
        t = palette(scheme, accent, sidebar)
        for name, fg, bg, floor in pairs_for(t):
            measured += 1
            got = contrast(fg, bg)
            if got < floor:
                where = f"{scheme}/{accent}/شريط {sidebar}"
                failures.append((where, name, fg, bg, got, floor))

    if failures:
        print("ألوان لا تُقرأ في لوحة الإدارة:\n")
        for where, name, fg, bg, got, floor in failures:
            print(f"  [{where}] {name}")
            print(f"    {fg} على {bg} — النسبة {got:.2f} والحدّ {floor}")
        print()
        print("الحدّ ٤٫٥ للنصّ و٣ لمكوّنات الواجهة (WCAG 2.2 AA).")
        print("لا تُخفَّض الأرقام هنا؛ يُغمَّق اللون في app.css.")
        return 1

    print(
        f"ألوان اللوحة مقروءة — {measured} قياساً "
        f"على {len(combinations)} توليفة مظهر."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
