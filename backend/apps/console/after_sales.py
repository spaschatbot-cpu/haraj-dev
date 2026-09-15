"""ما بعد البيع — ما رسا، ولمن، وهل وصل مالُه. T869.

كانت هذه الشاشة عندنا أحدَ عشرَ عموداً ومرشّحين. وفي v1 خمسةَ عشرَ عموداً —
عُدَّت في `admin3/bills/index.php:405-419` وهي خمسةَ عشرَ `<th>` بالضبط —
و**سبعةُ** مرشّحاتٍ لا خمسة (`:362-396`: بحثٌ عامّ، ومعرّفٌ مطابق، وموقفٌ
مطابق، وسعرٌ من، وسعرٌ إلى، وتاريخُ انتهاء، وحالة). والفرقُ لم يكن رأياً في
التصميم: **موظّفُ ما بعد البيع يمسك الهاتف ومعه رقمُ مطالبةٍ أو لوحةٌ أو لونُ
سيارةٍ**، وثلاثتُها كانت غائبةً هنا، فيخرج من الشاشة إلى شاشةٍ أخرى ليجيب
سؤالاً واحداً.

فالأعمدةُ الناقصة أُضيفت كما هي في v1: الموديل والصورة والعداد واللون ورقمُ
المطالبة ومعرّفُ المركبة. والمرشّحاتُ خمسةٌ عندنا، **وليست مرشّحاتِ v1
السبعة**: مرشّحا المدى (سعرٌ من/إلى) وتاريخُ الانتهاء ليست هنا، ومكانَها
مرشّحا «حالة الفاتورة» و«سداد الشريك» — وهما ما تُفتح الشاشةُ لأجله. وv1
يرشّح في المتصفّح على صفحةٍ مجلوبةٍ كاملةً (`:568-604`)، وهنا في القاعدة.

وثلاثةٌ لا تُنقَل كما هي
========================

**١ — عمودا «المركبة» و«الموديل» في v1 يطبعان الجملة مرّتين.** في لقطة
الإنتاج: «لكزس ايه اس 300 لكزس ايه اس 300» في خانةٍ واحدة، و«لكزس ايه اس 300»
في التي بجوارها — وذلك لأن `vehicle_name` هناك حقلٌ حرٌّ كُتب فيه الاسمُ
كاملاً، و`vehicle_brand + model` يُطبعان بعده.

والعمودان **قائمان كما في ترويسة v1** بطلب المالك (الالتزام بالهيدر حرفياً)،
لكن بلا التكرار: «المركبة» هي `make model` («لكزس ES 350»)، و«الموديل» هي
سنةُ الصنع («٢٠٢١») — «موديل ٢٠٢١» في العُرف السعوديّ. نفسُ عمودَي v1، ومعلومةٌ
مختلفة في كلٍّ منهما.

**٢ — «حالة الفاتورة» كانت تُطبع بالإنجليزية.** القالبُ كان يكتب
`{{ row.billing.state }}` وهي قيمةُ التعداد لا اسمُها، فيقرأ الموظّفُ `paid`
و`partial` في شاشةٍ عربيّةٍ كلِّها. صارت تُطبع بالاسم، والقيمةُ تبقى في
`data-*` للمرشّح.

**٣ — «المزادات المخفيّة» لم تُبنَ ولا تُدَّعى.** في v1 زرٌّ يخفي مزاداً من
العرض الافتراضيّ (`aftersales_hidden_auctions`)، وهو **كتابةٌ** تحتاج جدولاً
وقراراً من المالك: مزادٌ مخفيٌّ يختفي عن كل موظّف، فمن يبحث عن سيارةٍ فيه
يقرأ «لا نتائج» وهي موجودة. فتُركت، ولم يُوضع زرٌّ لا يفعل شيئاً.

ولماذا «سداد الشريك» يُسأل عن الدفتر لا عن جدول
================================================

مرشّحُ v1 يقرأ `partner_payments`، وهو الجدولُ الذي وصفته شاشتُه بنفسها بأنه
مصدرُ الحقيقة الوحيد لصفحة الشريك — أي حقيقةٌ ثانيةٌ بجوار الدفتر (T830ي).
وهنا دفعةُ الشريك **قيدٌ على الفاتورة**، فالسؤال يُطرح على القيد.

وهذا الملفُّ يبني **شاشتين** لا واحدة — T922
============================================

«القرارات المنتهية» في v1 هي هذا الجدولُ نفسُه: الخمسةَ عشرَ عموداً
والمرشّحاتُ الخمسة (قُرئ في `src/Views/Admin/aftersales/index.php:131-147`
و`src/Controllers/Admin/AfterSalesController.php:245-265` — شاشتان تستدعيان
`listPage` الواحدة)، **زائداً عموداً واحداً: `المزايدون`**. وعندنا كانت
جدولاً ثانياً بتسعة أعمدةٍ ومرشّحين في `billing.py`، أي **قاعدتان لسؤالٍ
واحد**: يُصلَح البحثُ العربيّ في إحداهما ويبقى `icontains` في أختها، ويُحجَب
الجوّالُ هنا ويظهر هناك. وذلك بعينه ما تشكو منه وثيقةُ الجرد
(`docs/v1-admin-menu.md` §١٣): «في v2 تُبنى واحدةً بفلترٍ يُظهر العمود، لا
شاشتين تُصانان معاً».

فالصفوفُ والمرشّحاتُ والأعمدةُ والتصديرُ والحارسُ هنا، ويبقى في `billing.py`
**ما يختلف حقاً**: مجموعةُ الصفوف (`DECIDED` لا `SOLD`)، ومرشّحُ `which`،
والعنوانُ. و`sale_table` هي البابُ الذي يدخل منه الاثنان.

والوصلةُ نصٌّ لا مفتاح: `record_payment` تبني
`payment:{invoice}:sheet:{digest}:{line}`، ولا حقلَ فاتورةٍ على
:class:`~apps.money.models.Transaction`. فالمرشّح يطابق بادئةَ المفتاح —
**وهذا هشٌّ عن قصدٍ مذكور**: يومَ يتغيّر شكلُ المفتاح يصمت هذا المرشّح ولا
يُخطئ، فيُقرأ «لا شيء مسدَّد» بدل رقمٍ غلط.
"""

from __future__ import annotations

from decimal import Decimal

from django.conf import settings
from django.core.paginator import Paginator
from django.db.models import Count, F, OuterRef, Q, Subquery, Sum
from django.shortcuts import render
from django.urls import reverse

from apps.auctions.models import Auction, Vehicle, VehicleImage
from apps.auctions.states import AuctionState, VehicleState
from apps.bidding.models import Bid
from apps.core.arabic import search_q
from apps.money.models import Invoice, InvoiceSource, InvoiceState, Transaction

#: حالاتُ المركبة التي تعني «بيعت» — من `catalog` نفسِها ولا تُكتب ثانيةً:
#: قائمتان تنسى إحداهما `released` يوماً، فتختفي سيارةٌ خرجت من الشاشة
#: التي تتابع خروجها.
from .catalog import SOLD
from .dashboard import Stat
from .exports import export_table, oversize, refuse, wants_export
from .icons import path_of
from .sensitive import CUSTOMER, MONEY, columns_for, prepare, shown_to
from .tones import tone_of, with_tones
from .views import console_page

ZERO = Decimal("0.00")

#: مقاساتُ الصفحة كما في «إدارة المستخدمين».
#:
#: وكان مكتوباً أن «٥٠ هو مقاسُ v1 هنا» — **ولا مقاسَ لـv1 هنا**: شاشتُه
#: المقابلة (`admin3/bills/index.php`) تجلب الصفوفَ كلَّها بلا ترقيم وترشّح
#: في المتصفّح، وأقربُ رقمٍ عنده ٢٥ في `admin3/bills/invoices_list.php:208-211`.
#: فالخمسون قرارُنا نحن — ونصفُ الشاشة يُقرأ بلا تمرير.
ROW_CHOICES = (10, 15, 25, 50, 100)
DEFAULT_ROWS = 50

#: رسمُ كلِّ بطاقة، باسمه في `icons.py`. مكتوبٌ هنا لا في القالب: البطاقةُ
#: تُبنى في بايثون فيبقى الرسمُ مع الرقم الذي يصفه.
CARD_ICONS = {
    "sold": "handshake",
    "unbilled": "receipt",
    "owing": "coins",
    "marketing": "briefcase",
    "settled": "layers-check",
    # الثلاثةُ الأخيرة لوجه «القرارات المنتهية» من الشاشة نفسِها.
    "decided": "stamp",
    "awarded": "gavel",
    "rejected": "ban",
}

#: رسمُ الفعل الوحيد في عمود «عرض»: سندُ الفاتورة. أُزيلت أيقونتا «فتح ملفّ
#: المركبة» و«فتح ملفّ المشتري» بطلب المالك — لا تُفتح صفحةٌ من هذه الشاشة إلا
#: السند. ومعه `title` و`aria-label` بالكلمة نفسها لمن لا يقرأ الرسم.
ROW_ICONS = {
    "invoice": "receipt",
}

#: حالاتُ الفاتورة كما تُعرض في المرشّح، ومعها «بلا فاتورة» — وهي حالةٌ
#: حقيقيّة لا غيابُ قيمة: مركبةٌ رست ولم تُفوتر بعدُ لا يُطالَب صاحبُها بشيء.
NO_INVOICE = "none"


def latest_invoice_field(name: str):
    """قيمةُ حقلٍ من **آخر** فاتورةٍ على هذه المركبة.

    آخرُ فاتورة لا أوّلُها: المركبةُ قد تُفوتَر ثم تُلغى فاتورتُها وتُفوتَر
    ثانيةً، والمستحقُّ هو الأخيرة. وهو ترتيبُ v1 نفسه (`ORDER BY io.id DESC`).
    """
    return Subquery(
        Invoice.objects.filter(vehicle=OuterRef("pk"))
        .order_by("-issued_at", "-id")
        .values(name)[:1]
    )


def sheet_settled_vehicle_ids() -> frozenset[int]:
    """معرّفاتُ المركبات التي دخلت دفعتُها بملفّ شريكٍ مرفوع — باستعلامٍ **واحد**.

    ولماذا مجموعةٌ تُحسب مرّةً لا استعلامٌ فرعيٌّ في كل صفّ
    ========================================================

    كان هذا المرشّح استعلاماً فرعياً `Exists` بادئتُه
    `payment:{invoice_pk}:sheet:`، و`invoice_pk` فيه هو **نفسه** استعلامٌ فرعيّ
    (آخرُ فاتورة). فبوستجرس لا يقدر أن يجعلها مدىً على الفهرس — يمسح جدولَ
    :class:`~apps.money.models.Transaction` **مسحاً كاملاً لكل صفّ**
    (`EXPLAIN`: تكلفةُ ٢٣٤٠٤، `Seq Scan`). على صفحةٍ من خمسين محتمل، وفي
    :func:`tallies` كارثة: المسحُ الكامل × كلِّ الصفوف المطابقة = تعليقٌ على
    البيانات الحقيقية (أربعةٌ وأربعون ألفاً).

    والبادئةُ الثابتة `"payment:"` **مدىٌ على الفهرس الفريد** لا مسح، ودفعاتُ
    الملفّات قليلةٌ أصلاً — فمسحةٌ واحدةٌ في كل تحميل، لا واحدةٌ لكل صفّ.

    والمفتاحُ يُفكَّك لا يُطابَق بـ`LIKE '%'` وسطاً: شكلُه
    `payment:{invoice}:sheet:{digest}:{line}`، فرقمُ الفاتورة هو الجزءُ الثاني.
    """
    invoice_ids = set()
    keys = Transaction.objects.filter(
        idempotency_key__startswith="payment:",
        idempotency_key__contains=":sheet:",
    ).values_list("idempotency_key", flat=True)
    for key in keys:
        parts = key.split(":")
        if len(parts) >= 3 and parts[1].isdigit():
            invoice_ids.add(int(parts[1]))
    if not invoice_ids:
        return frozenset()
    return frozenset(
        Invoice.objects.filter(pk__in=invoice_ids).values_list("vehicle_id", flat=True)
    )


def sold_rows(
    *,
    states: tuple = SOLD,
    text: str = "",
    auction: str = "",
    pay: str = "",
    marketing: str = "",
    settled: str = "",
    sheet_ids: frozenset[int] = frozenset(),
):
    """صفوفُ ما بعد البيع بمرشّحات v1 الخمسة.

    والمرشّحاتُ تُطبَّق على استعلامٍ واحد يخدم الشاشةَ والبطاقاتِ والتصدير
    معاً، فلا يعني المرشّحُ شيئاً على الشاشة وشيئاً في الملفّ.

    و`sheet_ids` تأتي محسوبةً من :func:`sheet_settled_vehicle_ids` — لا تُحسب
    هنا كي لا تتكرّر بين الصفوف والبطاقات والتصدير في الطلب الواحد.

    و`states` هي **الفرقُ الوحيد** بين هذه الشاشة و«القرارات المنتهية»
    ==============================================================
    تلك تسأل «ماذا قرّرنا» فمجموعتُها :data:`~apps.console.billing.DECIDED`
    والمرفوضةُ فيها كالمقبولة؛ وهذه تسأل «ماذا بعنا» فمجموعتُها :data:`SOLD`.
    وما عدا ذلك — المرشّحاتُ الخمسة، والأعمدةُ، والتصدير — واحدٌ حرفياً. فلو
    نُسخ الاستعلامُ لشاشتين لصار **قاعدتين**: يُصلَح البحثُ في إحداهما ويُنسى
    في أختها، وهو العطلُ الذي وقع في هذه اللوحة مراراً وتشكو منه وثيقةُ جرد
    v1 عن هاتين الشاشتين بعينهما (`docs/v1-admin-menu.md` §١٣).
    """
    rows = (
        Vehicle.objects.filter(state__in=states)
        .select_related("auction", "awarded_to")
        .annotate(
            invoice_pk=latest_invoice_field("pk"),
            invoice_number=latest_invoice_field("number"),
            invoice_state=latest_invoice_field("state"),
            invoice_odoo=latest_invoice_field("odoo_state_raw"),
            invoice_amount=latest_invoice_field("amount"),
            invoice_paid=latest_invoice_field("amount_paid"),
            invoice_issued=latest_invoice_field("issued_at"),
            invoice_source=latest_invoice_field("source"),
            invoice_odoo_id=latest_invoice_field("odoo_invoice_id"),
        )
        .order_by("-awarded_at", "-id")
    )

    text = (text or "").strip()
    if text:
        # سبعةُ حقولٍ نصّية كما في v1، ومعها اسمُ المشتري وهاتفُه — ومطابقةٌ
        # تطبّع العربية (T897)، فـ«شاحنه» تجد «شاحنة» و«دطق1265» تجد
        # «د ط ق 1265» وهي مكتوبةٌ بمسافاتٍ في القاعدة المُرحَّلة.
        matches = search_q(
            text,
            "plate_number",
            "vin",
            "claim_number",
            "make",
            "model",
            "colour",
            "awarded_to__full_name",
            "awarded_to__phone",
        )
        # الأرقام وحدها تُقارَن بالأرقام. في v1 كان `(int)'تويوتا' = 0` يُقارَن
        # بـ`av.id` فيرجع آلافَ الصفوف لأي كلمةٍ عربية — عطلٌ مكتوبٌ في
        # تعليقهم نفسِه على شاشة الخروج.
        if text.isdigit():
            number = int(text)
            matches |= Q(lot_number=number) | Q(auction__number=number) | Q(pk=number)
        rows = rows.filter(matches)

    auction = (auction or "").strip()
    if auction.isdigit():
        rows = rows.filter(auction__number=int(auction))

    pay = (pay or "").strip()
    if pay == NO_INVOICE:
        rows = rows.filter(invoice_pk__isnull=True)
    elif pay in InvoiceState.values:
        rows = rows.filter(invoice_state=pay)

    marketing = (marketing or "").strip()
    if marketing == "yes":
        rows = rows.filter(is_marketing=True)
    elif marketing == "no":
        rows = rows.filter(is_marketing=False)

    settled = (settled or "").strip()
    # المرشّحُ على `pk__in` لمجموعةٍ محسوبةٍ سلفاً — فهرسٌ لا مسح. و«لا» تُقصي
    # لا تُطابق `False`: مركبةٌ ليست في المجموعة هي التي لم تُسدَّد من ملفّ.
    if settled == "yes":
        rows = rows.filter(pk__in=sheet_ids)
    elif settled == "no":
        rows = rows.exclude(pk__in=sheet_ids)

    return rows


def tallies(
    rows, sheet_ids: frozenset[int], *, money: bool = True, decided: bool = False
) -> list[Stat]:
    """خمسةُ أرقامٍ عن **الصفوف المعروضة**، لا عن الجدول كلِّه.

    وذلك مقصود: من رشّح على مزادٍ بعينه يسأل عن ذلك المزاد، وبطاقةٌ تعدّ
    اثني عشر ألفاً بجوار جدولٍ فيه أربعون تجيب سؤالاً لم يُطرح.

    و«سُدِّدت من ملفّ» **خارج التجميعة الكبرى**: كانت `Count` بمرشّحٍ على
    الاستعلام الفرعيّ الماسح، فتُحوِّل التجميعةَ من مسحٍ واحدٍ رخيص إلى مسحٍ
    لجدول القيود لكل صفّ. وهي الآن عدٌّ مستقلٌّ على `pk__in` — فهرسٌ لا مسح.

    و`decided` يزيد بطاقتين لا شاشةً ثانية
    =====================================
    «القرارات المنتهية» تعرض المرفوضَ مع المُرسى، فسؤالُها الأوّل «كم منها
    رسا وكم رُفض» — وكانت الشاشةُ تجيبه بعدّادَين **يعدّان الجدولَ كلَّه
    ويتجاهلان المرشّحات**: من يرشّح على مزادٍ واحد يقرأ «٢٨٨ مرفوضة» وتحته
    جدولٌ فيه ثلاثة. فصارا بطاقتين داخل **نفس** `aggregate` الذي يحسب
    الباقي — استعلامٌ واحدٌ لا ثلاثة، ورقمٌ يحترم المرشّح كبقيّة البطاقات.

    ولا يُضافان لـ«ما بعد البيع»: مجموعتُها :data:`SOLD` بلا مرفوضةٍ أصلاً،
    فبطاقةُ «رفضها المالك» فيها صفرٌ دائمٌ يشغل مكاناً. والشرطُ هنا يُسقط
    `Count`ين من استعلام تلك الشاشة أيضاً، فلا تدفع ثمنَ عمودٍ لا تعرضه.
    """
    extra = (
        {
            "awarded": Count(
                "pk", distinct=True, filter=~Q(state=VehicleState.REJECTED)
            ),
            "rejected": Count(
                "pk", distinct=True, filter=Q(state=VehicleState.REJECTED)
            ),
        }
        if decided
        else {}
    )
    counted = rows.aggregate(
        total=Count("pk", distinct=True),
        unbilled=Count("pk", distinct=True, filter=Q(invoice_pk__isnull=True)),
        owing=Count(
            "pk",
            distinct=True,
            filter=Q(invoice_state__in=(InvoiceState.OPEN, InvoiceState.PARTIAL)),
        ),
        marketing=Count("pk", distinct=True, filter=Q(is_marketing=True)),
        residual=Sum(
            F("invoice_amount") - F("invoice_paid"),
            filter=Q(invoice_state__in=(InvoiceState.OPEN, InvoiceState.PARTIAL)),
        ),
        **extra,
    )
    residual = counted["residual"] or ZERO
    # **العددُ يبقى والمبلغُ يُحجَب.** «كم فاتورةً لم تكتمل» سؤالُ تشغيلٍ يجيبه
    # عدٌّ، و«كم ريالاً باقياً» مبلغٌ — ومبلغٌ مجموعٌ على مئاتِ العملاء ليس
    # أقلَّ حساسيّةً من مبلغِ فاتورةٍ واحدة، بل أكثر. فالبطاقةُ تبقى وعددُها
    # يبقى، ويسقط الرقمُ من تفصيلها لمن لا يملك `invoices.view`.
    owing_detail = (
        f"باقٍ عليها {residual:,.2f} ريالاً — محسوبٌ من الدفعات لا من كلمة أودو."
        if money
        else "محسوبٌ من الدفعات لا من كلمة أودو — والمبلغُ خلف صلاحية الفواتير."
    )
    # يحترمُ كلَّ المرشّحات القائمة: عدُّ المطابقِ الذي هو أيضاً في المجموعة.
    settled_count = rows.filter(pk__in=sheet_ids).count() if sheet_ids else 0

    head = [
        Stat(
            label="قرارات منتهية" if decided else "مركبات مباعة",
            value=f"{counted['total']:,}",
            detail=(
                "ما حُسم فيه قرار — والمرفوضُ كالمقبول، بالمرشّحات المطبَّقة الآن."
                if decided
                else "ما رست في مزادٍ منتهٍ — بالمرشّحات المطبَّقة الآن."
            ),
            tone="auction",
            icon=CARD_ICONS["decided"] if decided else CARD_ICONS["sold"],
        ),
    ]
    if decided:
        head += [
            Stat(
                label="رست",
                value=f"{counted['awarded']:,}",
                detail="قُبل فيها أعلى عرضٍ — ولها مشترٍ وفاتورة.",
                tone="auction",
                icon=CARD_ICONS["awarded"],
            ),
            Stat(
                label="رفضها المالك",
                value=f"{counted['rejected']:,}",
                detail="رُدَّ أعلى عرضٍ فيها — فلا مشتريَ لها ولا فاتورة.",
                tone="warn" if counted["rejected"] else "plain",
                icon=CARD_ICONS["rejected"],
            ),
        ]

    return [
        *head,
        Stat(
            label="بلا فاتورة بعد",
            value=f"{counted['unbilled']:,}",
            # ونصُّها يختلف في شاشة القرارات: المرفوضةُ هناك بلا فاتورةٍ
            # **بطبيعتها** لا تأخّراً، فـ«رست ولم تُفوتَر» تقرأ اتّهاماً حيث
            # لا تأخير — والعدّادُ نفسُه يبقى لأن السؤال «كم بلا فاتورة» واحد.
            detail=(
                "لا فاتورة عليها — والمرفوضةُ منها لا تُفوتَر أصلاً."
                if decided
                else "رست ولم تُفوتَر — ولا يُطالَب صاحبُها بشيءٍ حتى تُفوتَر."
            ),
            tone="warn" if counted["unbilled"] else "plain",
            icon=CARD_ICONS["unbilled"],
        ),
        Stat(
            label="لم يكتمل سدادها",
            value=f"{counted['owing']:,}",
            detail=owing_detail,
            tone="alarm" if counted["owing"] else "plain",
            icon=CARD_ICONS["owing"],
        ),
        Stat(
            label="سيارات تسويق",
            value=f"{counted['marketing']:,}",
            detail="مركبةُ شريكٍ تُعرض عندنا — لا مركبةٌ نملكها.",
            tone="plain",
            icon=CARD_ICONS["marketing"],
        ),
        Stat(
            label="سُدِّدت من ملفّ شريك",
            value=f"{settled_count:,}",
            detail="دخلت دفعتُها بملفٍّ مرفوع، وقُيّدت في الدفتر كغيرها.",
            tone="money",
            icon=CARD_ICONS["settled"],
        ),
    ]


def covers(page_rows):
    """صورةُ الغلاف لكل صفٍّ — باستعلامٍ واحد لكل الصفحة لا واحدٍ لكل صفّ.

    خمسون صفّاً × استعلامُ صورة = خمسون رحلةً إلى القاعدة لعمودٍ عرضُه
    أربعون بكسلاً. وهو ثمنٌ يُدفع مرّةً في كل تحميلٍ لكلِّ موظّف.
    """
    rows = list(page_rows)
    found = {}
    images = (
        VehicleImage.objects.filter(vehicle_id__in=[row.pk for row in rows])
        .order_by("vehicle_id", "-is_cover", "position", "id")
        .only("vehicle_id", "thumbnail", "image", "is_cover", "position")
    )
    for image in images:
        found.setdefault(image.vehicle_id, image)
    for row in rows:
        row.cover = found.get(row.pk)
    return rows


def page_size(raw: str) -> int:
    """مقاسُ الصفحة المطلوب، أو الافتراضيُّ لكل ما ليس في القائمة."""
    if raw.isdigit() and int(raw) in ROW_CHOICES:
        return int(raw)
    return DEFAULT_ROWS


def bid_counts(page_rows) -> None:
    """عددُ المزايدين لكلّ صفٍّ في `bids_count` — **باستعلامٍ واحدٍ للصفحة**.

    ولماذا تجميعةٌ على الصفحة لا تعليقٌ على الاستعلام
    ================================================
    في القاعدة **١٦٣٬٢٨٩ مزايدة** على ٦٬٥٤٧ مركبة، و`annotate(Count("bids"))`
    على استعلام الشاشة **وصلةٌ** تُضيف `GROUP BY` إلى كلّ ما يُسأل عن هذا
    الاستعلام بعدها.

    **والمقيس أوّلاً — ثم ما ثبت وما لم يثبت** (`haraj2_t307`، ٢٩٦ قراراً،
    ١٤ سبتمبر ٢٠٢٦):

    * *لم يثبت* أن المجاميع تفسد. ظُنّ أن `Sum(invoice_amount - invoice_paid)`
      في :func:`tallies` سيُجمَع مرّةً لكلّ مزايدة فوق الوصلة، **وقِيس فلم
      يقع**: ٦٨٩٬١٨٦٫٨٥ ريالاً بالوصلة وبدونها سواء، وعددُ الصفوف ٢٩٦ في
      الحالتين — جانغو يلفّ `aggregate` فوق استعلامٍ مجمَّعٍ أصلاً. فلا يُكتب
      هنا عطلٌ لم يُشاهَد.
    * *وثبت الثمن*، وهو وحده سببُ الرفض: التجميعة ٥٫٥ms ⇐ **٢٦ms**، وعدُّ
      المرقّم ٠٫٨ms ⇐ **٢٣ms**، وخمسون صفّاً ٩٫٢ms ⇐ **٣٧٫٦ms**. أي **نحو
      ٧١ms تُدفع في كلّ تحميلٍ لكلّ موظّف** ثمناً لعمودٍ واحد — على ٢٩٦ صفّاً؛
      وشاشةُ «ما بعد البيع» بالبنّاء نفسِه تبلغ اثني عشر ألفاً.

    والمختار: مفاتيحُ الصفحة (خمسون على الأكثر) ثمّ `GROUP BY` واحد —
    **١٫٧ms** مقابل ٣٤٫٣ms لو سُئل استعلامٌ لكلّ صفّ. كما تفعل :func:`covers`
    بالصور للسبب نفسِه.

    وضربٌ ديكارتيٌّ فوق تجميعٍ في هذه اللوحة **قتل عمليّةَ خادمٍ فعلاً** (علِق
    الطلبُ عشرَ دقائقَ وإحدى وأربعين ثانية)، ولذلك قِيست هذه الوصلةُ قبل أن
    تُكتب لا بعدها.

    و`order_by()` ليس زينةً: ترتيبُ :class:`~apps.bidding.models.Bid`
    الافتراضيّ يدخل `GROUP BY` فيُفرِّق الصفَّ الواحد على أعمدةِ ترتيبٍ لا
    تعني شيئاً هنا، فيرجع عددٌ أكبرُ من الحقيقة.
    """
    rows = list(page_rows)
    if not rows:
        return
    counted = dict(
        Bid.objects.filter(vehicle_id__in=[row.pk for row in rows])
        .order_by()
        .values_list("vehicle_id")
        .annotate(number=Count("pk"))
    )
    for row in rows:
        row.bids_count = counted.get(row.pk, 0)


def with_bid_counts(rows):
    """نفسُ العدد، مُعلَّقاً على الاستعلام — **لملفّ التصدير وحده**.

    الملفُّ كلُّ المطابق لا صفحةً، فلا مفاتيحَ في اليد تُجمَّع عليها. والتعليقُ
    هنا **استعلامٌ فرعيٌّ عدديّ** لا وصلة: لا `GROUP BY` على الاستعلام الخارجيّ،
    فلا يُدفَع ثمنُه في العدّ ولا في التجميعة. وقِيس: ٢٩٦ صفّاً بالعمود في
    **٣٦ms**، وسقفُ :data:`~.exports.MAX_ROWS` يحدّه بخمسة آلافٍ على الأكثر.

    ويُعلَّق **في فرع التصدير وحدَه**، لا على الاستعلام الذي تقرؤه
    :func:`tallies`: هناك يُحسب لكلّ صفٍّ في تجميعةٍ لا تستعمله.
    """
    return rows.annotate(
        bids_count=Subquery(
            Bid.objects.filter(vehicle=OuterRef("pk"))
            .order_by()
            .values("vehicle")
            .annotate(number=Count("pk"))
            .values("number")[:1]
        )
    )


def decorate(page_rows, sheet_ids: frozenset[int], *, rejected_note: bool = False):
    """ما يُحسب لكلّ صفٍّ قبل القالب — لشاشتَي الجدول معاً.

    كان هذا الجسدُ في عرض «ما بعد البيع»، فكان على «القرارات المنتهية» أن
    تنسخه أو تفقده. وهو مكانُ خمسة قراراتٍ مكتوبةٍ بأسبابها (اسمُ الحالة
    بالعربية، والنغمةُ من الخريطة الواحدة، والباقي من محرّك المال، ورابطُ
    أودو، وعضويّةُ مجموعة الملفّات) — ونسخُها يعني أن يُصلَح أحدُها في شاشةٍ
    ويبقى غلطاً في أختها.

    و`rejected_note` لفرقٍ حقيقيٍّ لا يُمحى
    ======================================
    «القرارات المنتهية» تعرض **المرفوضة**، وهي بلا مشترٍ وبلا فاتورة —
    لا تأخّراً بل بحكم القرار. فخليّةٌ خاليةٌ فيها («—» و«بلا فاتورة بعد»)
    تُقرأ «ناقصٌ يُلاحَق»، والصحيحُ «مرفوضة، فلا شيءَ هنا أصلاً». والفراغُ
    يُقال لا يُصمَت عنه.
    """
    rows = list(page_rows)
    source_labels = dict(InvoiceSource.choices)
    for row in rows:
        row.invoice_label = state_label(row.invoice_state)
        # نغمةُ حالة الفاتورة من `tones.py` — الخريطةُ الواحدة. وكانت تُحسب
        # في القالب بسلسلة `{% if %}`، **فأعطت جواباً غير جوابها**: «مستحقة»
        # (`open`) رماديّةٌ محايدة هناك و`warn` هنا. أي أن فاتورةً لم يصلها
        # ريالٌ واحد كانت أهدأ لوناً من فاتورةٍ وصل نصفُها، وبطاقةُ «لم يكتمل
        # سدادها» فوقها حمراء. و`with_tones` تقول ذلك بنفسها: «قالبٌ يحسب
        # نغمةً هو مكانٌ ثانٍ للقاعدة».
        row.invoice_tone = tone_of(row.invoice_state)
        row.invoice_residual = residual_of(row)
        row.invoice_source_label = source_labels.get(row.invoice_source, "—")
        row.odoo_invoice_url = odoo_move_url(row.invoice_odoo_id)
        # العضويّةُ في المجموعة المحسوبة سلفاً — لا استعلامَ لكل صفّ.
        row.settled_by_sheet = row.pk in sheet_ids
        # العدّادُ بفاصل آلاف كما في v1 (`aftersales/index.php:166`:
        # `number_format((float) $mileage)`) — «120,000» لا «120000». ورقمٌ من
        # ستّة أرقامٍ بلا فاصلٍ في عمودٍ ضيّق يُقرأ خطأً، وهو ما كان يقع.
        #
        # ويُحسَب هنا لا في القالب: `intcomma` تحتاج `django.contrib.humanize`
        # في `INSTALLED_APPS`، وتطبيقٌ كاملٌ لأجل فاصلةٍ أغلى من سطر. والفاصلةُ
        # لاتينيّةٌ صراحةً (`f"{n:,}"`) لا مترجَمة، كما `unlocalize` في كلّ
        # أرقام اللوحة. **ولا يُمَسُّ ملفُّ التصدير**: `export_columns` تقرأ
        # `row.odometer_km` الخام، فيبقى في إكسل رقماً يُجمَع لا نصّاً.
        row.odometer_text = (
            f"{row.odometer_km:,}" if isinstance(row.odometer_km, int) else ""
        )
        refused = rejected_note and row.state == VehicleState.REJECTED
        row.buyer_blank = "مرفوضة — لا مشتريَ لها" if refused else "—"
        # «بدون فاتورة» حرفيّاً كما في v1 (`:176`)، لا «بلا فاتورة بعد»:
        # و«بعدُ» تَعِد بفاتورةٍ قادمة، وهي وعدٌ لا يقع على مركبةٍ لم تُبَع.
        row.invoice_blank = "مرفوضة — لا فاتورة" if refused else "بدون فاتورة"
    return rows


def export_columns(sheet_ids: frozenset[int], *, bidders: bool = False):
    """أعمدةُ الملفّ ثلاثيّاتٍ `(عنوان, دالّة, قدرة)` — قبل أن يقصّها الحارس.

    **و«سعر الترسية» محذوفٌ عمداً**: لا عمودَ له على الشاشة ولا سطرَ في السند —
    وعمودٌ يخرج في ملفٍّ ولا يظهر على شاشةٍ هو بابُ التسريب نفسُه. (قِيس في
    ملفٍّ منزَّل: `9500.00` للمركبة 25963 و`20000.00` للمركبة 25961.)

    **و«الإجمالي المستحق» مضاف**: كان الملفُّ يحمل «المسدَّد» و«الباقي» بلا
    الرقم الذي يُقاسان عليه، فلا يُطابَق به شيء — وهو معروضٌ في السند على
    الشاشة.

    و«المزايدون» آخرُ الأعمدة لا وسطَها: ترتيبُ الملفّ يُقرأ يساراً في إكسل،
    وإقحامُ عمودٍ في الوسط يُزحزح كلَّ ما بعده في ملفٍّ يُقارَن بملفٍّ سابق.
    """
    columns = [
        ("الموقف", lambda row: row.lot_number, None),
        ("المزاد", lambda row: row.auction.number, None),
        ("اسم المزاد", lambda row: row.auction.title, None),
        ("المركبة", lambda row: f"{row.make} {row.model}", None),
        ("السنة", lambda row: row.year, None),
        ("اللوحة", lambda row: row.plate_number, None),
        ("العداد", lambda row: row.odometer_km, None),
        ("اللون", lambda row: row.get_colour_display(), None),
        ("الشاصي", lambda row: row.vin, None),
        ("رقم المطالبة", lambda row: row.claim_number, None),
        (
            "المشتري",
            lambda row: row.awarded_to.full_name if row.awarded_to else "",
            CUSTOMER,
        ),
        (
            "هاتف المشتري",
            lambda row: row.awarded_to.phone if row.awarded_to else "",
            CUSTOMER,
        ),
        ("معرّف المركبة", lambda row: row.pk, None),
        ("الفاتورة", lambda row: row.invoice_number, None),
        ("حالتها — من الدفعات", lambda row: state_label(row.invoice_state), None),
        ("الإجمالي المستحق", lambda row: row.invoice_amount, MONEY),
        ("المسدَّد", lambda row: row.invoice_paid, MONEY),
        ("الباقي", lambda row: residual_of(row), MONEY),
        ("كلمة أودو", lambda row: row.invoice_odoo, None),
        ("تسويق", lambda row: "نعم" if row.is_marketing else "لا", None),
        (
            "سُدِّدت من ملفّ شريك",
            lambda row: "نعم" if row.pk in sheet_ids else "لا",
            MONEY,
        ),
    ]
    if bidders:
        # القرارُ نفسُه في الملفّ: «ماذا قرّرنا» يحتاج الحالةَ، وv1 يضعها في
        # ملفّه أيضاً (`حالة المركبة`). و«صفرٌ» لا فراغٌ لمن لا مزايدَ عليها:
        # الخليّةُ الفارغة تُقرأ «لم يُحسَب» لا «لم يزايد أحد».
        columns += [
            ("القرار", lambda row: row.get_state_display(), None),
            ("وقت القرار", lambda row: row.awarded_at, None),
            ("المزايدون", lambda row: row.bids_count or 0, None),
        ]
    return columns


def chosen_filters(request) -> dict:
    """مرشّحاتُ الشاشة الخمسة من `GET` — تُقرأ مرّةً وتُمرَّر.

    مرّةً واحدةً لأنها تُستعمل مرّتين في الطلب: مرّةً لبناء الصفوف ومرّةً
    لرسم الخانات في القالب. وقراءتان لنفس المفتاح في نفس الطلب هما كيف يصير
    `mkt` في الاستعلام و`marketing` في القالب فلا تعود الخانةُ تُظهر ما رُشِّح.
    """
    return {
        "text": request.GET.get("q", ""),
        "auction": request.GET.get("auction", ""),
        "pay": request.GET.get("pay", ""),
        "marketing": request.GET.get("mkt", ""),
        "settled": request.GET.get("settle", ""),
    }


def sale_table(request, rows, *, chosen, sheet_ids, seen, screen, name, decided=False):
    """جسدُ الشاشة كاملاً: إمّا ملفُّ تصديرٍ، وإمّا سياقُ قالب الجدول.

    **وهو البنّاءُ الواحد لشاشتين**، وهو ما تطلبه وثيقةُ جرد v1 نصّاً عن
    هاتين بعينهما: «شاشتان بجدولٍ واحد يفترقان بعمود — في v2 تُبنى واحدةً
    بفلترٍ يُظهر العمود، لا شاشتين تُصانان معاً».

    ولماذا سياقٌ يُرجَع لا `render` يُنادى
    =====================================
    لأن الشاشتين تختلفان في العنوان والافتتاحية وفي مرشّحٍ سادس (`which`)،
    وعرضُ كلٍّ منهما يضيف ما يخصّه ثمّ يرسم. ودالّةٌ ترسم بنفسها كانت ستحتاج
    وسائطَ للعنوان وللافتتاحية وللمرشّح الزائد — أي أن يُكتب شكلُ كلّ شاشةٍ
    في الملفّ الذي يخدمهما معاً.

    و`decided` علمٌ واحدٌ لثلاثة فروقٍ تأتي معاً
    ==========================================
    عمودُ «المزايدون» وبطاقتا «رست/رفضها المالك» وكلمةُ «مرفوضة» مكان الخليّة
    الخالية — ثلاثتُها وجهُ «القرارات المنتهية» ولا يُطلب أحدُها وحده. وعلَمٌ
    واحدٌ يقول ذلك أصدقُ من ثلاثةٍ تُمرَّر معاً دائماً ويُنسى أحدُها يوماً.
    """
    if wants_export(request):
        # الملفُّ هو **كلُّ** المطابق لا الصفحةُ المعروضة — كما في v1 حرفياً:
        # «تصدير كل النتائج المطابقة للفلاتر (وليس الصفحة الحالية فقط)». ومن
        # يصدّر ليُطابق كشفاً بنكياً يأخذ صفحةً واحدة ويظنّها الكلّ.
        #
        # **وبسقفِ صفوفٍ صريح** (`exports.MAX_ROWS`): ملفٌّ مقصوصٌ صامتاً
        # يُقرأ كاملاً ويُطابَق به كشفٌ بنكيّ ولا شيءَ فيه يقول إنّه ناقص.
        count = oversize(rows)
        if count:
            return refuse(request, count)

        # **والملفُّ يرث حارسَ الشاشة**: المشتري وجوّالُه خلف `users.view`،
        # والمبالغُ خلف `invoices.view` — بالقاعدة نفسِها التي تحجبها في
        # الصفحة (`sensitive.py`). ومن يفتح الشاشة كان يضغط «تصدير» فيأخذ في
        # ملفٍّ واحدٍ ما لا يحقّ له في الصفحة.
        stream = with_bid_counts(rows) if decided else rows
        return export_table(
            stream.iterator(chunk_size=500),
            name=name,
            columns=columns_for(export_columns(sheet_ids, bidders=decided), seen),
        )

    size = page_size(request.GET.get("per_page", ""))
    page = Paginator(rows, size).get_page(request.GET.get("page"))
    with_tones(page.object_list)
    covers(page.object_list)
    decorate(page.object_list, sheet_ids, rejected_note=decided)
    if decided:
        bid_counts(page.object_list)

    # **المحجوبُ يُمحى هنا، بعد الحساب وقبل القالب.** كانت الشاشةُ تضع في مصدر
    # الصفحة جوّالَ المشتري ومبلغَ فاتورته ومسدَّدَها وباقيها لكلّ صفّ، وهي
    # `auctions.view` وحدَها. والقاعدةُ في `sensitive.py` — نفسُها التي يقرؤها
    # «كتالوج السيارات»، فلا تُطبَّق في شاشةٍ وتُترك في أختها.
    prepare(page.object_list, seen)

    return {
        "page": page,
        "rows": page.object_list,
        "cards": tallies(rows, sheet_ids, money=seen.money, decided=decided),
        "show_money": seen.money,
        "show_customer": seen.customer,
        "show_bidders": decided,
        # عددُ أعمدةِ صفّ «لا نتائج». رقمٌ في السياق لا `{% if %}` في القالب:
        # عمودٌ يُضاف يوماً يُنسى في الشرط فيخرج صفُّ الفراغ أقصرَ من الجدول.
        "colspan": 17 if decided else 15,
        "q": chosen["text"],
        "auction": chosen["auction"],
        "pay": chosen["pay"],
        "mkt": chosen["marketing"],
        "settle": chosen["settled"],
        "size": size,
        "row_choices": ROW_CHOICES,
        "auctions": ended_auctions(),
        "pay_choices": [
            *[(value, label) for value, label in InvoiceState.choices],
            (NO_INVOICE, "بلا فاتورة"),
        ],
        "export_url": f"{reverse(screen)}?{export_query(request)}",
        "reset_url": reverse(screen),
        "filtered": any(chosen.values()) or size != DEFAULT_ROWS,
        "icon_invoice": path_of(ROW_ICONS["invoice"]),
    }


@console_page("console:after-sales")
def after_sales(request):
    """ما بعد البيع: ما بيع، ولمن، وهل وصل مالُه."""
    chosen = chosen_filters(request)
    # تُحسب مرّةً للطلب كلِّه: الصفوفُ والبطاقاتُ والتصدير تقرؤها، فلا تتكرّر.
    sheet_ids = sheet_settled_vehicle_ids()
    rows = sold_rows(states=SOLD, sheet_ids=sheet_ids, **chosen)
    seen = shown_to(request.user)

    built = sale_table(
        request,
        rows,
        chosen=chosen,
        sheet_ids=sheet_ids,
        seen=seen,
        screen="console:after-sales",
        name="ما-بعد-البيع",
    )
    if not isinstance(built, dict):
        return built
    return render(request, "console/after_sales.html", built)


def state_label(value: str) -> str:
    """اسمُ حالة الفاتورة بالعربية.

    كان القالبُ يطبع القيمة نفسَها، فيقرأ الموظّفُ `paid` و`partial` في شاشةٍ
    عربيّةٍ كلِّها. والقيمةُ تبقى في `data-*` لأن المرشّح يرسلها.
    """
    if not value:
        return "بلا فاتورة"
    return dict(InvoiceState.choices).get(value, value)


def residual_of(row) -> Decimal:
    """الباقي على فاتورة هذا الصفّ — بتعريف محرّك المال لا بطرحٍ هنا.

    كان السطرُ `amount - amount_paid` مكتوباً هنا، **وهو تعريفٌ ثانٍ للمستحقّ
    يخالف الأوّل**: `Invoice.outstanding` تُصفّر الملغاة وتقصّ السالب، وهذا
    الطرحُ لا يفعل. فقِيس على `haraj2_t307`: ٢٦١ فاتورةً ملغاة مجموعُ
    (المبلغ − المسدَّد) فيها ١٠٬٧٣٧٬٧٦٣٫٤٧ ريالاً، وكلُّها **صفرٌ** عند
    المحرّك. ورُئي على الشاشة: الفاتورة `V-25963-202609` حالتُها «ملغاة»
    والسندُ يطبع «الباقي ١١٬٢٧٠٫٠٠» والمحرّك يقول صفراً — ويخرج الرقمُ نفسه
    في عمود «الباقي» من ملفّ إكسل يُطابَق به كشفٌ بنكيّ.

    والصفُّ حقولٌ مُعلَّقةٌ لا كائنُ فاتورة، فتُبنى فاتورةٌ **غير محفوظة**
    حاملةً الثلاثة ويُسأل المحرّكُ نفسُه. لا كتابةَ ولا استعلام — قراءةُ قاعدةٍ
    من صاحبها، فلا تتفارق يوم تتغيّر.
    """
    if row.invoice_amount is None:
        return ZERO
    return Invoice(
        state=row.invoice_state or "",
        amount=row.invoice_amount or ZERO,
        amount_paid=row.invoice_paid or ZERO,
    ).outstanding


def odoo_move_url(odoo_id: str) -> str:
    """رابطُ الفاتورة الضريبيّة في أودو — أو فراغٌ إن لا فاتورةَ هناك.

    نفسُ بناء v1: `{base}/web#id={id}&model=account.move&view_type=form`. ولا
    يُبنى إلا حين يجتمع أمران — عنوانُ أودو مضبوطٌ في البيئة، وللفاتورة معرّفٌ
    هناك. ففاتورةٌ محليّةٌ لم تُزامَن لا فاتورةَ ضريبيّةَ لها، وزرٌّ يفتح لا شيء
    أسوأ من غيابه. ولذلك يبقى الزرُّ مخفيّاً في التطوير حيث `ODOO_BASE_URL`
    فارغٌ والفواتيرُ محليّة.
    """
    base = (getattr(settings, "ODOO_BASE_URL", "") or "").rstrip("/")
    ref = (odoo_id or "").strip()
    if not base or not ref:
        return ""
    return f"{base}/web#id={ref}&model=account.move&view_type=form"


def ended_auctions():
    """المزاداتُ التي انتهت — قائمةُ المرشّح.

    مقصورةٌ على ثلاثمئة: قائمةٌ منسدلة بألفِ عنصرٍ لا تُستعمَل، ومن يريد مزاداً
    أقدمَ يكتب رقمَه في البحث.

    وكان مكتوباً «كما في v1» — **ولا قائمةَ مزاداتٍ في v1 أصلاً**؛ مرشّحُه على
    المزاد خانةٌ يُكتب فيها رقمٌ (`admin3/bills/index.php:362-396` في المتصفّح،
    و`admin3/bills/invoices_list_ajax.php:71-84` على الخادم). والثلاثمئةُ عنده
    سقفُ **صفوفِ فواتير** في `admin3/paid/get2.php:138` (`LIMIT 300`)، لا سقفُ
    قائمة. فالرقمُ مصادفةٌ لا نقل.
    """
    return list(
        Auction.objects.filter(state__in=(AuctionState.ENDED, AuctionState.SETTLED))
        .order_by("-number")
        .values_list("number", "title")[:300]
    )


def export_query(request) -> str:
    """مرشّحاتُ الشاشة كما هي، ومعها طلبُ الملفّ.

    الصفحةُ ومقاسُها يُسقطان: الملفُّ كلُّ المطابق، فرقمُ صفحةٍ فيه لا معنى له.
    """
    kept = request.GET.copy()
    kept.pop("page", None)
    kept.pop("per_page", None)
    kept["export"] = "xlsx"
    return kept.urlencode()
