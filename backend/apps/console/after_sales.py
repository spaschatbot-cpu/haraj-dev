"""ما بعد البيع — ما رسا، ولمن، وهل وصل مالُه. T869.

كانت هذه الشاشة عندنا أحدَ عشرَ عموداً ومرشّحين، وفي v1 خمسةَ عشرَ عموداً
وخمسَ مرشّحات. والفرقُ لم يكن رأياً في التصميم: **موظّفُ ما بعد البيع يمسك
الهاتف ومعه رقمُ مطالبةٍ أو لوحةٌ أو لونُ سيارةٍ**، وثلاثتُها كانت غائبةً
هنا، فيخرج من الشاشة إلى شاشةٍ أخرى ليجيب سؤالاً واحداً.

فالأعمدةُ الناقصة أُضيفت كما هي في v1: الموديل والصورة والعداد واللون ورقمُ
المطالبة ومعرّفُ المركبة. والمرشّحاتُ الخمسة كذلك.

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

والوصلةُ نصٌّ لا مفتاح: `record_payment` تبني
`payment:{invoice}:sheet:{digest}:{line}`، ولا حقلَ فاتورةٍ على
:class:`~apps.money.models.Transaction`. فالمرشّح يطابق بادئةَ المفتاح —
**وهذا هشٌّ عن قصدٍ مذكور**: يومَ يتغيّر شكلُ المفتاح يصمت هذا المرشّح ولا
يُخطئ، فيُقرأ «لا شيء مسدَّد» بدل رقمٍ غلط.
"""

from __future__ import annotations

from decimal import Decimal

from django.core.paginator import Paginator
from django.db.models import Count, F, OuterRef, Q, Subquery, Sum
from django.shortcuts import render
from django.urls import reverse

from apps.auctions.models import Auction, Vehicle, VehicleImage
from apps.auctions.states import AuctionState
from apps.money.models import Invoice, InvoiceSource, InvoiceState, Transaction

#: حالاتُ المركبة التي تعني «بيعت» — من `catalog` نفسِها ولا تُكتب ثانيةً:
#: قائمتان تنسى إحداهما `released` يوماً، فتختفي سيارةٌ خرجت من الشاشة
#: التي تتابع خروجها.
from .catalog import SOLD
from .dashboard import Stat
from .exports import export, wants_export
from .icons import path_of
from .tones import with_tones
from .views import console_page

ZERO = Decimal("0.00")

#: مقاساتُ الصفحة كما في «إدارة المستخدمين» — و٥٠ هو مقاسُ v1 هنا.
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
}

#: رسمُ كلِّ فعلٍ في الصفّ. أفعالٌ ثلاثة لا كلماتٌ ثلاث: عمودٌ بثلاث كلمات
#: يُوسّع الجدولَ الذي فيه ستّةَ عشرَ عموداً أصلاً، والرسمُ يُقرأ في لمحة —
#: ومعه `title` و`aria-label` بالكلمة نفسها لمن لا يقرأ الرسم.
ROW_ICONS = {
    "open": "eye",
    "invoice": "receipt",
    "buyer": "person-search",
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
    """
    rows = (
        Vehicle.objects.filter(state__in=SOLD)
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
        )
        .order_by("-awarded_at", "-id")
    )

    text = (text or "").strip()
    if text:
        # سبعةُ حقولٍ نصّية كما في v1، ومعها اسمُ المشتري وهاتفُه.
        matches = (
            Q(plate_number__icontains=text)
            | Q(vin__icontains=text)
            | Q(claim_number__icontains=text)
            | Q(make__icontains=text)
            | Q(model__icontains=text)
            | Q(colour__icontains=text)
            | Q(awarded_to__full_name__icontains=text)
            | Q(awarded_to__phone__icontains=text)
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


def tallies(rows, sheet_ids: frozenset[int]) -> list[Stat]:
    """خمسةُ أرقامٍ عن **الصفوف المعروضة**، لا عن الجدول كلِّه.

    وذلك مقصود: من رشّح على مزادٍ بعينه يسأل عن ذلك المزاد، وبطاقةٌ تعدّ
    اثني عشر ألفاً بجوار جدولٍ فيه أربعون تجيب سؤالاً لم يُطرح.

    و«سُدِّدت من ملفّ» **خارج التجميعة الكبرى**: كانت `Count` بمرشّحٍ على
    الاستعلام الفرعيّ الماسح، فتُحوِّل التجميعةَ من مسحٍ واحدٍ رخيص إلى مسحٍ
    لجدول القيود لكل صفّ. وهي الآن عدٌّ مستقلٌّ على `pk__in` — فهرسٌ لا مسح.
    """
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
    )
    residual = counted["residual"] or ZERO
    # يحترمُ كلَّ المرشّحات القائمة: عدُّ المطابقِ الذي هو أيضاً في المجموعة.
    settled_count = rows.filter(pk__in=sheet_ids).count() if sheet_ids else 0

    return [
        Stat(
            label="مركبات مباعة",
            value=f"{counted['total']:,}",
            detail="ما رست في مزادٍ منتهٍ — بالمرشّحات المطبَّقة الآن.",
            tone="auction",
            icon=CARD_ICONS["sold"],
        ),
        Stat(
            label="بلا فاتورة بعد",
            value=f"{counted['unbilled']:,}",
            detail="رست ولم تُفوتَر — ولا يُطالَب صاحبُها بشيءٍ حتى تُفوتَر.",
            tone="warn" if counted["unbilled"] else "plain",
            icon=CARD_ICONS["unbilled"],
        ),
        Stat(
            label="لم يكتمل سدادها",
            value=f"{counted['owing']:,}",
            detail=f"باقٍ عليها {residual:,.2f} ريالاً — محسوبٌ من الدفعات لا من كلمة أودو.",
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


@console_page("console:after-sales")
def after_sales(request):
    """ما بعد البيع: ما بيع، ولمن، وهل وصل مالُه."""
    text = request.GET.get("q", "")
    auction = request.GET.get("auction", "")
    pay = request.GET.get("pay", "")
    marketing = request.GET.get("mkt", "")
    settled = request.GET.get("settle", "")

    # تُحسب مرّةً للطلب كلِّه: الصفوفُ والبطاقاتُ والتصدير تقرؤها، فلا تتكرّر.
    sheet_ids = sheet_settled_vehicle_ids()

    rows = sold_rows(
        text=text,
        auction=auction,
        pay=pay,
        marketing=marketing,
        settled=settled,
        sheet_ids=sheet_ids,
    )

    if wants_export(request):
        # الملفُّ هو **كلُّ** المطابق لا الصفحةُ المعروضة — كما في v1 حرفياً:
        # «تصدير كل النتائج المطابقة للفلاتر (وليس الصفحة الحالية فقط)». ومن
        # يصدّر ليُطابق كشفاً بنكياً يأخذ صفحةً واحدة ويظنّها الكلّ.
        return export(
            rows.iterator(chunk_size=500),
            name="ما-بعد-البيع",
            headers=[
                "الموقف",
                "المزاد",
                "اسم المزاد",
                "المركبة",
                "السنة",
                "اللوحة",
                "العداد",
                "اللون",
                "الشاصي",
                "رقم المطالبة",
                "المشتري",
                "هاتف المشتري",
                "معرّف المركبة",
                "سعر الترسية",
                "الفاتورة",
                "حالتها — من الدفعات",
                "المسدَّد",
                "الباقي",
                "كلمة أودو",
                "تسويق",
                "سُدِّدت من ملفّ شريك",
            ],
            cell=lambda row: [
                row.lot_number,
                row.auction.number,
                row.auction.title,
                f"{row.make} {row.model}",
                row.year,
                row.plate_number,
                row.odometer_km,
                row.get_colour_display(),
                row.vin,
                row.claim_number,
                row.awarded_to.full_name if row.awarded_to else "",
                row.awarded_to.phone if row.awarded_to else "",
                row.pk,
                row.awarded_price,
                row.invoice_number,
                state_label(row.invoice_state),
                row.invoice_paid,
                residual_of(row),
                row.invoice_odoo,
                "نعم" if row.is_marketing else "لا",
                "نعم" if row.pk in sheet_ids else "لا",
            ],
        )

    size = page_size(request.GET.get("per_page", ""))
    page = Paginator(rows, size).get_page(request.GET.get("page"))
    with_tones(page.object_list)
    covers(page.object_list)

    source_labels = dict(InvoiceSource.choices)
    for row in page.object_list:
        row.invoice_label = state_label(row.invoice_state)
        row.invoice_residual = residual_of(row)
        row.invoice_source_label = source_labels.get(row.invoice_source, "—")
        # العضويّةُ في المجموعة المحسوبة سلفاً — لا استعلامَ لكل صفّ.
        row.settled_by_sheet = row.pk in sheet_ids

    return render(
        request,
        "console/after_sales.html",
        {
            "page": page,
            "rows": page.object_list,
            "cards": tallies(rows, sheet_ids),
            "q": text,
            "auction": auction,
            "pay": pay,
            "mkt": marketing,
            "settle": settled,
            "size": size,
            "row_choices": ROW_CHOICES,
            "auctions": ended_auctions(),
            "pay_choices": [
                *[(value, label) for value, label in InvoiceState.choices],
                (NO_INVOICE, "بلا فاتورة"),
            ],
            "export_url": f"{reverse('console:after-sales')}?{export_query(request)}",
            "filtered": any([text, auction, pay, marketing, settled])
            or size != DEFAULT_ROWS,
            "icon_open": path_of(ROW_ICONS["open"]),
            "icon_invoice": path_of(ROW_ICONS["invoice"]),
            "icon_buyer": path_of(ROW_ICONS["buyer"]),
        },
    )


def state_label(value: str) -> str:
    """اسمُ حالة الفاتورة بالعربية.

    كان القالبُ يطبع القيمة نفسَها، فيقرأ الموظّفُ `paid` و`partial` في شاشةٍ
    عربيّةٍ كلِّها. والقيمةُ تبقى في `data-*` لأن المرشّح يرسلها.
    """
    if not value:
        return "بلا فاتورة"
    return dict(InvoiceState.choices).get(value, value)


def residual_of(row) -> Decimal:
    """الباقي على فاتورة هذا الصفّ — أو صفرٌ إن لا فاتورة."""
    if row.invoice_amount is None:
        return ZERO
    return (row.invoice_amount or ZERO) - (row.invoice_paid or ZERO)


def ended_auctions():
    """المزاداتُ التي انتهت — قائمةُ المرشّح.

    مقصورةٌ على ثلاثمئة كما في v1: قائمةٌ منسدلة بألفِ عنصرٍ لا تُستعمَل،
    ومن يريد مزاداً أقدمَ يكتب رقمَه في البحث.
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
