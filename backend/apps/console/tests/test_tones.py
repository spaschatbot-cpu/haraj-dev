"""كل حالةٍ في اللوحة لها نغمة، ولا نغمة بلا حالة. T828.

الادّعاء الذي يحرسه هذا الملف واحد: **حالةٌ تُضاف غداً إلى أي تعداد تُسقط
الحزمة**، بدل أن تُرسَم حبّةً رمادية بلا أن ينتبه أحد. وهو النوع الذي لا يظهر
في مراجعة: الصفحة تُرسم، والحالة مكتوبة، واللون وحده هو الغائب — ولا أحد يفتح
شاشةً بحثاً عن لونٍ ناقص.

والاتجاه الثاني مقصود بالقدر نفسه: صفٌّ في `TONES` لا يقابل حالةً هو قيمةٌ
مكتوبةٌ بالخطأ أو بقيّةُ حالةٍ حُذفت — وكلاهما يعني أن أحداً يظنّ أنه لوّن
شيئاً وهو لم يفعل.
"""

from __future__ import annotations

import pytest

from apps.auctions.states import AuctionState, VehicleState
from apps.console.tones import TONES, tone_of, with_tones
from apps.money.models import InvoiceState, PaymentIntentState
from apps.notifications.models import DeliveryState
from apps.odoo.models import InboundState

#: كل تعدادٍ تُعرض حالاته في جدولٍ من جداول اللوحة. تعدادٌ جديد يُضاف هنا،
#: وإلا كان غيابُه هو الثغرة نفسها التي يغلقها هذا الملف.
ENUMS = (
    AuctionState,
    VehicleState,
    InvoiceState,
    PaymentIntentState,
    DeliveryState,
    InboundState,
)

#: النغمات التي تعرفها `app.css` في `.pill[data-tone="…"]`. نغمةٌ هنا بلا قاعدةٍ
#: هناك حبّةٌ بلا لون — والفراغ محايدٌ مقصود.
KNOWN = {"", "ok", "bad", "warn", "info", "money", "auction"}


def every_state() -> set[str]:
    return {choice.value for enum in ENUMS for choice in enum}


def test_every_state_has_a_tone() -> None:
    """حالةٌ بلا صفّ تُرسَم رمادية صامتةً — وهذا ما يمنعه."""
    missing = every_state() - TONES.keys()
    assert not missing, f"حالاتٌ بلا نغمة: {sorted(missing)}"


def test_no_tone_without_a_state() -> None:
    """صفٌّ لا يقابل حالةً قيمةٌ مكتوبةٌ بالخطأ أو بقيّةُ حالةٍ حُذفت."""
    extra = TONES.keys() - every_state()
    assert not extra, f"نغماتٌ لا حالةَ لها: {sorted(extra)}"


def test_every_tone_is_one_the_sheet_can_draw() -> None:
    """`.pill[data-tone="X"]` لا وجود لها في الورقة تعني حبّةً بلا لون."""
    unknown = set(TONES.values()) - KNOWN
    assert not unknown, f"نغماتٌ لا تعرفها app.css: {sorted(unknown)}"


@pytest.mark.parametrize(
    ("state", "tone"),
    [
        (InvoiceState.PAID, "ok"),
        (InvoiceState.OPEN, "warn"),
        (PaymentIntentState.FAILED, "bad"),
        (DeliveryState.DELIVERED, "ok"),
        (AuctionState.LIVE, "info"),
        (AuctionState.DRAFT, ""),
    ],
)
def test_the_tones_say_what_they_mean(state: str, tone: str) -> None:
    """عيّنةٌ صريحة: خريطةٌ تمرّ الفحوص أعلاه وهي معكوسةٌ كلّها ممكنة."""
    assert tone_of(state) == tone


def test_an_unknown_state_is_grey_not_a_crash() -> None:
    """شاشةٌ تنهار لأن حالةً جديدة أُضيفت أسوأ من حبّةٍ رمادية.

    الحزمة تمنع المجهول من الوصول (الاختبار الأول)؛ وهذا يضمن أن وصولَه —
    من بياناتٍ قديمة، أو من ترحيلٍ لم يكتمل — لا يُسقط صفحة.
    """
    assert tone_of("لا-حالة-كهذه") == ""
    assert tone_of("") == ""
    assert tone_of(None) == ""  # type: ignore[arg-type]


def test_with_tones_marks_the_rows_it_is_given() -> None:
    """تُنادى من العرض على صفوف الصفحة، فتعلّق `tone` عليها."""

    class Row:
        def __init__(self, state):
            self.state = state

    rows = with_tones([Row(InvoiceState.PAID), Row(PaymentIntentState.FAILED)])
    assert [row.tone for row in rows] == ["ok", "bad"]
