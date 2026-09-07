"""يرسم `console/dashboard.html` الحقيقي بلا قاعدة بيانات، لأجل الفحص البصري.

    python ops/preview_console.py && just console-preview

لماذا يوجد
==========
لأن الشكل لا يُفحص نصّاً. `test_dashboard.py` يثبت أن البطاقة تحمل الرقم الصحيح
ويفتح الشاشة الصحيحة؛ ولا يقول ولا يستطيع أن يقول إن الرقم يُقرأ على الخلفية
التي وقع عليها، أو إن الشريط انطوى إلى أيقوناتٍ يُميَّز بعضها من بعض. ذلك
يُرى — ورؤيتُه كانت تعني تشغيل PostgreSQL وبذرةَ عرضٍ وخادماً، وهو ثمنٌ يُدفع
عند كل تعديل لونٍ في CSS.

وليس بديلاً عن شيء: يملأ `Board` بأرقامٍ **مصنوعة** ويمرّرها إلى القالب نفسه
الذي يستعمله الخادم. فما يُرى في المتصفّح هو مخرَج القالب والورقة الحقيقيّين —
لا صفحةٌ كُتبت بيدٍ تشبههما — لكنّه لا يقول شيئاً عن صحّة الأرقام ولا عن
البوابات: `sidebar()` هنا يعرض كل الصفحات بلا `can()`، عمداً، لأن الغرض رؤية
الشكل. من قرأ منه حكماً على الصلاحيات قرأ ما لا يقوله.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

BACKEND = Path(r"D:\taskss\harajj dev\backend")
OUT = Path(__file__).resolve().parents[1] / "backend" / ".design-preview"

sys.path.insert(0, str(BACKEND))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")
os.chdir(BACKEND)

import django  # noqa: E402

django.setup()

from django.template.loader import render_to_string  # noqa: E402

from apps.console.dashboard import Board, Delta, Stat, _wheel  # noqa: E402
from apps.console.navigation import PAGES, PLANNED, SECTIONS  # noqa: E402


class FakeUser:
    full_name = "هيثم المالك"
    is_authenticated = True


class FakeRequest:
    path = "/console/dashboard/"
    user = FakeUser()


def sidebar() -> list[dict]:
    """كل الصفحات، بلا فلترة صلاحيات — الغرض رؤية الشكل لا اختبار البوابة."""
    out = []
    for section in SECTIONS:
        items = [page for page in PAGES if page.section == section.key]
        soon = [row for row in PLANNED if row.section == section.key]
        if items or soon:
            out.append({"label": section.label, "pages": items, "planned": soon})
    return out


states = [("قادم", 1, 2), ("منتهٍ", 55, 92), ("جارٍ", 2, 4), ("مسودّة", 1, 2)]

board = Board(
    is_clean=False,
    alarms=[
        Stat(
            label="فوارق في الدفتر",
            value="2",
            detail="حسابان لا يتّزنان — الفحص وجدهما في آخر تشغيل.",
            href="#",
            tone="alarm",
            icon="",
            action="افتح صحّة المال",
        ),
        Stat(
            label="وديعة بلا مستحقّ",
            value="1",
            detail="حجزٌ مقفول ولا عميل يملكه.",
            href="#",
            tone="warn",
            icon="",
            action="افتح الدفتر",
        ),
    ],
    stats=[
        Stat(
            label="إجمالي التأمين",
            value="9,630,004",
            detail="ريالاً محتجَزاً في المحافظ الآن.",
            href="#",
            tone="money",
            icon="book",
            action="دفتر التأمينات",
            delta=Delta(12, "up", "عن الأسبوع الماضي"),
            spark=(30, 44, 38, 61, 55, 78, 92),
        ),
        Stat(
            label="إجمالي المزايدات",
            value="125006",
            detail="7,106 مزايدة آخر 24 ساعة.",
            href="#",
            tone="auction",
            icon="gavel",
            action="قائمة المزادات",
            delta=Delta(8, "up", "عن الأسبوع الماضي"),
            spark=(20, 35, 30, 52, 48, 70, 88),
        ),
        Stat(
            label="إجمالي المستخدمين",
            value="44129",
            detail="37 مشترفاً نشطاً هذا الأسبوع.",
            href="#",
            tone="people",
            icon="users",
            action="قائمة المستخدمين",
            delta=Delta(2, "flat", "عن الأسبوع الماضي"),
            spark=(60, 62, 61, 65, 66, 68, 70),
        ),
        Stat(
            label="إجمالي المزادات",
            value="56",
            detail="1 قادم · 55 منتهٍ.",
            href="#",
            tone="auction",
            icon="award",
            action="قائمة المزادات",
        ),
        Stat(
            label="فواتير معلّقة",
            value="3945",
            detail="بقيمة 131.93 مليون ريال.",
            href="#",
            tone="money",
            icon="file",
            action="قائمة الفواتير",
            delta=Delta(5, "down", "عن الأسبوع الماضي"),
            spark=(90, 84, 80, 72, 66, 60, 52),
        ),
        Stat(
            label="مركبات في الكتالوج",
            value="20358",
            detail="منها 1 في المفضّلات.",
            href="#",
            tone="plain",
            icon="car",
            action="قائمة المركبات",
        ),
        # الثلاث الأخيرة هنا لأجل الرسم لا لأجل الرقم: `lock` و`scale` و`help`
        # بطاقاتٌ لا يبنيها إلا مالكٌ بصلاحيةٍ كاملة، ولولاها لبقيت ثلاثة رسوم
        # لا تُرى في أي معاينة — وهي المعاينة التي تُفحص فيها الرسوم.
        Stat(
            label="حجوزات قائمة",
            value="412",
            detail="كلٌّ منها يسمّي مزاده أو فاتورته.",
            href="#",
            tone="money",
            icon="lock",
            action="من عليه حجز",
        ),
        Stat(
            label="مركبات تنتظر قراراً",
            value="37",
            detail="عرضٌ معلّق على المالك.",
            href="#",
            tone="warn",
            icon="scale",
            action="قرارات الشركاء",
        ),
        Stat(
            label="مزايدات مرفوضة اليوم",
            value="18",
            detail="كلٌّ منها بسببه ولقطةٍ لماله وقتها.",
            href="#",
            tone="warn",
            icon="help",
            action="لماذا رُفضت",
        ),
    ],
    auction_states=states,
    auction_wheel=_wheel(states),
    auction_total=59,
    trend=[
        ("٣١/٨", 620, 42),
        ("١/٩", 810, 55),
        ("٢/٩", 740, 50),
        ("٣/٩", 1180, 80),
        ("٤/٩", 960, 65),
        ("٥/٩", 1340, 91),
        ("٦/٩", 1470, 100),
    ],
)

# اسمها SCREENS لا PAGES: الثانية مستوردةٌ من navigation أعلاه،
# والتظليل عليها كسر البذرة في أول تشغيل.
SCREENS = {
    "dashboard": ("console:home", "console/dashboard.html"),
    "auction_archive": ("console:auction-archive", "console/auction_archive.html"),
    "payments": ("console:payments", "console/payments.html"),
    "notifications": ("console:notifications", "console/notifications.html"),
    "vehicles": ("console:vehicles", "console/vehicles.html"),
    "invoices": ("console:invoices", "console/invoices.html"),
    "customers": ("console:customers", "console/customers.html"),
    "money_ledger": ("console:money-ledger", "console/money_ledger.html"),
    "auctions": ("console:auctions", "console/auctions.html"),
}

html = render_to_string(
    "console/dashboard.html",
    {
        "sidebar": sidebar(),
        "environment": "development",
        "request": FakeRequest(),
        "board": board,
        "messages": [],
    },
)

# الورقة والسكربت يُنسخان بجوار الصفحة ليعملا من `file://` بلا خادم ملفات ثابتة.
OUT.mkdir(parents=True, exist_ok=True)
static = BACKEND / "apps" / "console" / "static" / "console"
for name in ("app.css", "theme.js"):
    (OUT / name).write_text(
        (static / name).read_text(encoding="utf-8"), encoding="utf-8"
    )

html = html.replace("/static/console/", "./")
(OUT / "dashboard.html").write_text(html, encoding="utf-8")
print("wrote", OUT / "dashboard.html")

# ---------------------------------------------------------------------------
# باقي الشاشات: تُرسم من **القاعدة الحقيقية** بعميل الاختبار، لا بسياقٍ مصنوع.
# ---------------------------------------------------------------------------
# لماذا `force_login` لا نموذج دخول: لأن كتابة كلمة مرورٍ في نموذجٍ ليست شيئاً
# تفعله أداةُ معاينة. و`force_login` يبني الجلسة مباشرةً بلا كلمة مرورٍ أصلاً،
# وهو نفسه ما تفعله كل اختبارات اللوحة.
#
# ويصمت إن لم تكن هناك قاعدةٌ أو موظّف: المعاينة أداةُ نظرٍ لا خطوةَ بناء،
# وتوقّفُها بأثرٍ كامل عند غياب قاعدةٍ محليّة يجعلها عبئاً لا عوناً.
try:
    from django.contrib.auth import get_user_model
    from django.test import Client
    from django.urls import reverse

    staff = get_user_model().objects.filter(is_staff=True).order_by("pk").first()
    if staff is None:
        raise RuntimeError("لا موظّف في قاعدة التطوير — شغّل `manage.py seed_demo`")

    client = Client()
    client.force_login(staff)
    for name, (url_name, _template) in SCREENS.items():
        if name == "dashboard":
            continue
        # `SERVER_NAME` صريحٌ: عميل الاختبار يرسل `testserver` وليس في
        # `ALLOWED_HOSTS` بإعدادات التطوير — فيعود 400 وتُكتب صفحة خطأ بدل
        # الشاشة. أوّل تشغيلٍ كتب أربع صفحاتٍ فارغةً بلا صوت.
        response = client.get(reverse(url_name), SERVER_NAME="127.0.0.1")
        if response.status_code != 200:
            raise RuntimeError(f"{url_name} أجاب {response.status_code}")
        # الصور تُشير إلى `/media/…`، ولا يخدمها خادمُ الملفّات الساكن الذي
        # تُفتح منه هذه المعاينة — فتظهر أيقوناتُ كسرٍ وتُقرأ عطلاً وهي ليست.
        # تُحوَّل إلى خادم التطوير الذي يخدمها فعلاً (`MEDIA_URL` في
        # `config/urls.py` تحت DEBUG وحده).
        body = (
            response.content.decode()
            .replace("/static/console/", "./")
            .replace('src="/media/', 'src="http://127.0.0.1:8001/media/')
        )
        (OUT / f"{name}.html").write_text(body, encoding="utf-8")
        print(f"wrote {OUT / (name + '.html')}  [{response.status_code}]")
except Exception as problem:  # noqa: BLE001
    print(f"لم تُرسم الشاشات من القاعدة: {problem}")
