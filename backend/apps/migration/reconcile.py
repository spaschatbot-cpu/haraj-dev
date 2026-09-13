"""المطابقة عميلاً عميلاً — T312. رصيدُ v1، ورصيدُنا، والفرقُ وسببُه.

## ما تجيب عنه هذه الوحدة

معيارُ `D4`: «تقرير فروق يذكر كلَّ عميلٍ يختلف رصيدُه، **بالمبلغ والسبب
المرجَّح**». ومعيارُ قبول `T312`: «**ولا عميلَ بفرقٍ بلا سبب مصنَّف**».

والفرقُ **نتيجةٌ لا فشل** — بنصّ `spec.md`: «أرصدةُ v1 نفسها فيها أخطاءٌ معروفةٌ
وموثَّقة… نسخُ الرصيد ينقل الأخطاء ويجعلها رسميّة. إعادةُ البناء تكشفها». فمهمّةُ
هذا الملفّ أن يجعل كلَّ فرقٍ **مقروءاً ومصنَّفاً**، لا أن يجعله صفراً.

## ورصيدُ v1 يُحسب من دفتره لا من عموده

`userss.total_insurance_paid` عمودٌ مشتقٌّ فيه أخطاءٌ موثَّقة (انحرافُ ٥٤٨
عميلاً في `v1-wallet-logic.md` §٨)، و`spec.md` يقول «**تجاهله تماماً**». فالرصيدُ
هنا يُعاد اشتقاقُه من `insurance_deposits` بالقاعدة التي يكتبها v1 لنفسه:

    SUM(amount) WHERE status NOT IN ('refunded', 'confiscated')

أي أن المقارنةَ **دفترٌ بدفتر**، لا دفترُنا بعمودٍ مشتقٍّ عندهم — وإلا كان كلُّ
انحرافٍ في عمودهم فرقاً يُنسب إلينا.

## والتصنيف: لكلِّ فرقٍ سببٌ من قائمةٍ مغلقة

لا نصٌّ حرّ. القائمةُ المغلقة هي ما يجعل التقرير قابلاً للعدّ («٣١ عميلاً بسبب
كذا») بدل أن يكون سرداً يُقرأ مرّةً — وهي ما يجعل سبباً جديداً **إضافةً
مرئيّةً** لا جملةً تُكتب في حقل.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from django.db.models import Sum

from apps.migration.dumpfile import read_table
from apps.migration.models import LegacyRef
from apps.money.models import Account, AccountKind

ZERO = Decimal("0.00")

#: حالاتُ الوديعة التي **خرج مالُها** — فلا تُعدّ في رصيد v1.
GONE = frozenset({"refunded", "confiscated"})

#: الدلاءُ الثلاثة التي يقابل مجموعُها رصيدَ v1: المتاح والمحجوز والمرهون.
#: و**المصادَرُ والمستردُّ ليسا دلوَ عميل** عندنا أصلاً — خرجا من ملكيّته،
#: كما خرجا من مجموع v1.
OURS = (
    AccountKind.INSURANCE_FREE,
    AccountKind.INSURANCE_HELD,
    AccountKind.INSURANCE_LOCKED,
)


@dataclass(frozen=True)
class Difference:
    """فرقُ عميلٍ واحد، وسببُه المرجَّح. لا يُنشأ بلا سبب."""

    user_id: int | None
    legacy_id: str
    theirs: Decimal
    ours: Decimal
    reason: str

    @property
    def gap(self) -> Decimal:
        return (self.ours - self.theirs).quantize(Decimal("0.01"))


def v1_balances(dump: Path) -> dict[str, Decimal]:
    """رصيدُ كلِّ عميلٍ في v1، مُعاداً اشتقاقُه من دفتره لا من عموده."""
    balances: dict[str, Decimal] = defaultdict(lambda: ZERO)
    for row in read_table(dump, "insurance_deposits"):
        if str(row.get("status") or "") in GONE:
            continue
        try:
            amount = Decimal(str(row.get("amount") or "0"))
        except Exception:  # noqa: BLE001 — صفٌّ لا يُقرأ يُعدّ صفراً ويظهر فرقاً
            continue
        balances[str(row.get("user_id") or "")] += amount
    return dict(balances)


def our_balances(user_ids: set[int]) -> dict[int, Decimal]:
    """مجموعُ الدلاء الثلاثة لكلِّ عميل — استعلامٌ واحد لا واحدٌ لكلِّ عميل."""
    rows = (
        Account.objects.filter(owner_id__in=user_ids, kind__in=OURS)
        .values("owner_id")
        .annotate(total=Sum("balance"))
    )
    return {row["owner_id"]: row["total"] or ZERO for row in rows}


def _reason(theirs: Decimal, ours: Decimal, user_id: int | None) -> str:
    """السببُ المرجَّح، من قائمةٍ مغلقة.

    الترتيبُ مقصود: الأخصُّ أوّلاً. وعميلٌ لم يُرحَّل أصلاً سببٌ يسبق كلَّ حسابٍ
    في المبلغ — لأن المبلغَ عنده ليس «فرقاً» بل **غياباً**.
    """
    if user_id is None:
        return "حسابٌ لم يُرحَّل — الجوّال لا يُقرأ بصيغتنا"
    if ours == ZERO and theirs > ZERO:
        return "المال لم يُبنَ — حركةٌ رفضها قيدٌ أثناء البناء"
    if theirs == ZERO and ours > ZERO:
        return "مالٌ عندنا بلا مقابلٍ في دفتر v1"
    if abs(ours - theirs) < Decimal("1.00"):
        return "فرقُ تقريبٍ أقلُّ من ريال"
    if ours < theirs:
        return "نقصٌ: جزءٌ من ودائعه لم يُبنَ"
    return "زيادةٌ: بُني له أكثرُ مما يقوله دفتر v1"


def differences(dump: Path) -> list[Difference]:
    """كلُّ عميلٍ يختلف رصيدُه، مصنَّفاً. والمتطابقُ لا يُنشأ له صفّ.

    وتُقرأ الجسورُ لا الجوّالات: `LegacyRef` هو ما يقول إن `userss.id = 15034`
    صار هذا الحساب. والمطابقةُ بالجوّال تخلط حسابين (v1 فيه جوّالاتٌ مكرَّرة).
    """
    bridge = LegacyRef.resolve("accounts.user")
    theirs = v1_balances(dump)
    ours = our_balances({pk for pk in bridge.values() if pk})

    found: list[Difference] = []
    for legacy, their_balance in theirs.items():
        user_id = bridge.get(legacy)
        our_balance = ours.get(user_id, ZERO) if user_id else ZERO
        if our_balance == their_balance:
            continue
        found.append(
            Difference(
                user_id=user_id,
                legacy_id=legacy,
                theirs=their_balance.quantize(Decimal("0.01")),
                ours=our_balance.quantize(Decimal("0.01")),
                reason=_reason(their_balance, our_balance, user_id),
            )
        )

    # وعميلٌ عندنا رصيدٌ وليس في دفتر v1 صفٌّ أصلاً — الاتجاهُ الآخر، ولولاه
    # لكان «صفر فرق» يعني «لم أنظر في هذا الاتجاه».
    legacy_of = {pk: legacy for legacy, pk in bridge.items() if pk}
    for user_id, our_balance in ours.items():
        legacy = legacy_of.get(user_id, "")
        if our_balance != ZERO and legacy not in theirs:
            found.append(
                Difference(
                    user_id=user_id,
                    legacy_id=legacy,
                    theirs=ZERO,
                    ours=our_balance.quantize(Decimal("0.01")),
                    reason="مالٌ عندنا بلا مقابلٍ في دفتر v1",
                )
            )

    found.sort(key=lambda d: abs(d.gap), reverse=True)
    return found


def summary(found: list[Difference]) -> dict:
    """ما يحتاجه التقرير، محسوباً مرّةً واحدة."""
    by_reason: dict[str, dict] = defaultdict(lambda: {"count": 0, "gap": ZERO})
    total_gap = ZERO
    for difference in found:
        total_gap += difference.gap
        bucket = by_reason[difference.reason]
        bucket["count"] += 1
        bucket["gap"] += difference.gap
    return {
        "affected": len(found),
        "total_gap": total_gap.quantize(Decimal("0.01")),
        "by_reason": dict(by_reason),
        "largest": found[:10],
    }


__all__ = ["Difference", "differences", "our_balances", "summary", "v1_balances"]
