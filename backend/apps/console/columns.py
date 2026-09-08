"""أعمدةُ كل جدولٍ في اللوحة، مُعرَّفةً مرّةً واحدة. T869.

هذا هو نظيرُ `navigation.PAGES` للجداول: الجدولُ يُعرَّف صفّاً صفّاً هنا، ثم
يقرؤه القالبُ ومكوّنُ التخصيص **من المصدر نفسه**. ولولا ذلك لكانت قائمةُ
الأعمدة في القالب وقائمةٌ أخرى في نافذة التخصيص، فعمودٌ يُضاف لإحداهما ويُنسى
في الأخرى يظهر بلا خانةِ إخفاء، أو يُخفى ولا يُرسَم — وهو عطلُ v1 نفسُه في
`navigation` منقولاً إلى الأعمدة.

`layout_for(user, key)` تدمج تعريفَ الجدول باختيار الموظّف المحفوظ وتُعيد
الأعمدةَ **بترتيبها ورؤيتها النهائية** — فالقالبُ لا يقرّر، والـview لا يحسب.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Column:
    """عمودٌ واحد: مفتاحُه الثابت، وعنوانُه العربيّ، وهل يُقفَل من الإخفاء."""

    key: str
    label: str

    #: عمودٌ لا يُخفى: هويّةُ الصفّ (اللوت) وعمودُ التحكّم. إخفاءُ عمودِ اللوت
    #: يترك صفوفاً بلا ما يُنقَر لفتحها، وإخفاءُ التحكّم يُذهب أزرارَ الصفّ —
    #: وكلاهما ليس تخصيصاً بل تعطيل. فيُعرَض دائماً ولا خانةَ إخفاءٍ له.
    locked: bool = False


#: جداولُ اللوحة، كلٌّ بمفتاحه وأعمدته بترتيبها الافتراضيّ. المفتاحُ يُخزَّن في
#: `ColumnLayout.table_key`، فتغييرُه يفقد تخصيصَ من خصّص — لا يُغيَّر إلا بهجرة.
TABLES: dict[str, tuple[Column, ...]] = {
    "auction_vehicles": (
        Column("lot", "اللوت", locked=True),
        Column("car", "السيارة"),
        Column("year", "السنة"),
        Column("vin", "الشاصي"),
        Column("claim", "رقم المطالبة"),
        Column("plate", "اللوحة"),
        Column("plate_type", "نوع اللوحة"),
        Column("colour", "اللون"),
        Column("odometer", "العداد"),
        Column("insurance", "شركة التأمين"),
        Column("condition", "الحالة الفنية"),
        Column("runs", "حالة المحرّك"),
        Column("keys", "المفاتيح"),
        Column("transmission", "ناقل الحركة"),
        Column("fuel", "الوقود"),
        Column("images", "الصور"),
        Column("owner", "المالك"),
        Column("marketing", "التسويق"),
        Column("state", "الحالة"),
    ),
}


@dataclass(frozen=True)
class ResolvedColumn:
    """عمودٌ بعد دمج التعريف بالاختيار: يُعرَض أم لا، ومفتاحُه للقالب."""

    key: str
    label: str
    locked: bool
    visible: bool


def columns_of(table_key: str) -> tuple[Column, ...]:
    """أعمدةُ جدولٍ من السجلّ، أو خطأٌ صريحٌ إن كان المفتاح مجهولاً.

    الخطأ عند الاستيراد لا عند العرض: مكوّنٌ يُمرَّر مفتاحاً غيرَ مسجَّل خطأٌ
    برمجيّ، وأن يُكتشَف فارغاً في الشاشة أسوأ من أن يرفع `KeyError` هنا.
    """
    try:
        return TABLES[table_key]
    except KeyError as exc:  # pragma: no cover - خطأُ مبرمجٍ لا مسارُ مستخدم
        raise KeyError(
            f"جدولٌ غير مسجَّل: {table_key!r} — أضِفه إلى TABLES في columns.py"
        ) from exc


def layout_for(user, table_key: str) -> list[ResolvedColumn]:
    """أعمدةُ الجدول لهذا الموظّف: بترتيبه المحفوظ ورؤيته المحفوظة.

    الدمجُ يحرس ثلاثاً: عمودٌ جديدٌ في السجلّ لم يخصّصه أحدٌ **يظهر** (لا
    يختفي خلف ترتيبٍ قديم)، ومفتاحٌ في التخصيص لا وجود له في السجلّ **يُتجاهَل**
    (الجدولُ تغيّر)، والعمودُ المقفولُ **يظهر دائماً** مهما قال المحفوظ.
    """
    defined = columns_of(table_key)
    by_key = {col.key: col for col in defined}

    saved = _saved_layout(user, table_key)
    hidden = set(saved.get("hidden", ()))
    order = [key for key in saved.get("ordering", ()) if key in by_key]

    # الترتيب: المحفوظُ أولاً، ثم ما في السجلّ ولم يُذكَر — بترتيبه الأصليّ.
    seen = set(order)
    tail = [col.key for col in defined if col.key not in seen]
    final_order = order + tail

    resolved = []
    for key in final_order:
        col = by_key[key]
        resolved.append(
            ResolvedColumn(
                key=col.key,
                label=col.label,
                locked=col.locked,
                visible=col.locked or key not in hidden,
            )
        )
    return resolved


def hidden_keys(user, table_key: str) -> set[str]:
    """مفاتيحُ الأعمدة المخفيّة لهذا الموظّف — يقرؤها القالبُ بسرعة.

    المقفولُ لا يكون مخفياً أبداً، فيُطرَح هنا: قالبٌ يقرأ هذه المجموعة لا يحتاج
    أن يعرف قاعدةَ القفل.
    """
    return {col.key for col in layout_for(user, table_key) if not col.visible}


def save_layout(user, table_key: str, *, hidden, ordering) -> None:
    """احفظ اختيارَ الموظّف بعد تنقيته على السجلّ.

    لا يُحفظ إلا ما يعرفه السجلّ: مفتاحٌ مجهولٌ في المُدخَل يُطرَح هنا فلا يُخزَّن
    قمامةً تُقرأ لاحقاً. والمقفولُ لا يدخل `hidden` مهما أرسل المتصفّح.
    """
    defined = columns_of(table_key)
    valid = {col.key for col in defined}
    locked = {col.key for col in defined if col.locked}

    clean_hidden = [k for k in dict.fromkeys(hidden) if k in valid and k not in locked]
    clean_order = [k for k in dict.fromkeys(ordering) if k in valid]

    from .models import ColumnLayout

    ColumnLayout.objects.update_or_create(
        user=user,
        table_key=table_key,
        defaults={"hidden": clean_hidden, "ordering": clean_order},
    )


def _saved_layout(user, table_key: str) -> dict:
    """صفُّ الموظّف من القاعدة، أو فارغٌ إن لم يخصّص — أو لم يُصادَق أصلاً."""
    if not getattr(user, "is_authenticated", False):
        return {}
    from .models import ColumnLayout

    row = ColumnLayout.objects.filter(user=user, table_key=table_key).first()
    if row is None:
        return {}
    return {"hidden": row.hidden or [], "ordering": row.ordering or []}
