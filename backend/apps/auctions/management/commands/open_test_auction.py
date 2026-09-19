"""مزادٌ حيٌّ يبقى مفتوحاً، للفحص اليدويّ وحده.

**لماذا أمرٌ مستقلٌّ عن `seed_demo`:** البذرةُ تكتب المزاد رقم 1001 مرّةً ثم
تجدّد نافذتَه في كل تشغيل، **ولا تكتب حالته أبداً** — عن قصد: بذرةٌ تُجبر
الحالة تُنتج قاعدةً لا تصلها آلةُ الحالات. فإذا انتهى 1001 (وهو ينتهي: ستُّ
ساعاتٍ تمرّ، أو يُترك الجهازُ مطفأً ليلة) بقي `ended` مهما مُدَّت نافذتُه،
لأن `ended → live` نقلةٌ غيرُ موجودة في `AUCTION_MOVES` — ولا ينبغي أن توجد:
مزادٌ انتهت مزايدتُه وصدرت فواتيرُه لا يُفتح ثانيةً بقلب عمود.

فهذا الأمرُ **يصنع مزاداً جديداً** ويمرّ به على الطريق المشروع
(`draft → scheduled → live`) بنافذةٍ طويلة، ثم ينقل إليه مركبات آخر مزادٍ
منتهٍ — بصورها وبياناتها — فتمتلئ خانةُ «نشط» في الحال.

وإعادةُ تشغيله لا تُنشئ ثانياً: تمدّد نافذةَ القائم.
"""

from __future__ import annotations

from decimal import Decimal

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Count
from django.utils import timezone

from apps.auctions.models import Auction, Vehicle, VehicleImage
from apps.auctions.services import move_auction
from apps.auctions.states import AuctionState, VehicleState

#: رقمٌ خارج نطاق أرقام البذرة (1001–1004)، فلا يتنازعان على صفٍّ واحد.
NUMBER = 1900

TITLE = "مزاد الاختبار — مفتوح"

#: ما يُملأ في المركبة المنقولة حين يكون عمودُها فارغاً. T946
#:
#: **ولماذا يُملأ أصلاً:** الترحيل نقل ١٣ ألف مركبةٍ من v1، ولون ٩٩٪ منها
#: `unknown` — لأن v1 يكتب اللونَ نصّاً حرّاً وما لم يُطابِق قائمتَنا يسقط
#: (`apps/migration/vocab.py`). وبطاقةُ المركبة في التطبيق تعرض اللونَ وناقلَ
#: الحركة والوقود، فمركبةٌ بلا شيءٍ منها تُقرأ «الشاشةُ ناقصة» لا «البياناتُ
#: ناقصة».
#:
#: وهذه **بيانات فحصٍ صريحة** في قاعدة تطويرٍ خلف `DEBUG` — لا تُكتب على صفٍّ
#: يحمل قيمةً من v1، ولا تعمل في الإنتاج أصلاً.
FILLERS = {
    "colour": ("white", "black", "silver", "grey", "blue"),
    "transmission": ("automatic",),
    "fuel_type": ("petrol",),
    "condition": ("running",),
}

#: عدّادٌ معقول حين لا عدّاد: مدىً لا رقمٌ واحد، فجدولٌ كلُّه `100000` يُقرأ
#: عموداً معطوباً.
ODOMETERS = (45_000, 68_000, 92_000, 120_000, 155_000, 180_000)


def _reserve_for(year: int | None) -> Decimal:
    """سعرُ وقوفٍ معقولٌ لمركبةِ فحص — بالسنة، لا رقمٌ واحدٌ للجميع.

    وهو **بيانُ فحصٍ صريح**: v1 لا يحمل هذا العمود أصلاً (اثنتا عشرة مركبةً
    من ١٣٬٠٠٣ تحمله)، فالصفرُ في الجدول ليس قيمةً منقولةً بل عمودٌ لم يُملأ.
    وصفرٌ في «سعر الوقوف» يُقرأ «تُباع بأيّ مبلغ».
    """
    base = 8_000
    if year:
        base += max(0, (year - 2005)) * 900
    return Decimal(min(base, 95_000))



class Command(BaseCommand):
    help = "مزادٌ حيٌّ بنافذةٍ طويلة، لفحص الشاشات (DEBUG وحده)"

    def add_arguments(self, parser) -> None:
        # **ثلاثةُ أيّامٍ لا سنة.** T950.
        #
        # كان الافتراضُ 8760 ساعةً، فقرأ العدّادُ على كلّ بطاقةٍ
        # `364:08:24:21` — رقمٌ لا يُقرأ، ولا يشبه مزاداً، ويشغل أعرضَ حوضٍ
        # في الكرت بلا معنى. ومزادُ حراج الحقيقيّ يُفتح أيّاماً لا سنوات،
        # فبيانةُ الفحص تُشبه ما تُحاكيه.
        parser.add_argument(
            "--hours",
            type=int,
            default=72,
            help="كم ساعةً يبقى مفتوحاً (الافتراضي ثلاثة أيّام)",
        )
        parser.add_argument(
            "--cars",
            type=int,
            default=0,
            help="أضِف هذا العددَ من المركبات **معروضةً** بكامل بياناتها",
        )

    def handle(self, *args, **options) -> None:
        if not settings.DEBUG:
            raise CommandError(
                "مزادُ الفحص لا يعمل خارج DEBUG. مزادٌ مفتوحٌ سنةً في الإنتاج "
                "ليس بيانات فحص، هو مزادٌ يقبل مزايدات."
            )

        now = timezone.now()
        ends = now + timezone.timedelta(hours=options["hours"])

        with transaction.atomic():
            auction, created = Auction.objects.get_or_create(
                number=NUMBER,
                defaults={
                    "title": TITLE,
                    # يبدأ في الماضي: شرطُ النقلة إلى `live` هو بلوغُ وقت
                    # البدء، وبدايةٌ في المستقبل تردّها `TransitionNotReady`.
                    "starts_at": now - timezone.timedelta(hours=1),
                    "ends_at": ends,
                    "state": AuctionState.DRAFT,
                    "location": "الرياض / طريق الحائر",
                },
            )
            if not created:
                Auction.objects.filter(pk=auction.pk).update(ends_at=ends)
                auction.refresh_from_db()
                self.stdout.write(f"مُدّدت نافذة المزاد {NUMBER} إلى {ends:%Y-%m-%d}")

        # **المركباتُ قبل الجدولة، لا بعدها**: شرطُ `draft → scheduled` أن
        # يكون في المزاد مركبةٌ واحدة على الأقل — وهو شرطٌ محقّ: مزادٌ مجدولٌ
        # بلا مركبات موعدٌ لا شيء فيه.
        moved = self._fill(auction)
        if options["cars"]:
            moved += self._stock(auction, options["cars"])

        if auction.state == AuctionState.DRAFT:
            move_auction(auction, AuctionState.SCHEDULED)
        if auction.state == AuctionState.SCHEDULED:
            move_auction(auction, AuctionState.LIVE)

        if auction.state != AuctionState.LIVE:
            # حالةٌ لا يُخرجها هذا الأمر من نفسه (انتهى وهو مفتوح؟) — تُقال
            # ولا تُصلَح بقلب عمود.
            self.stdout.write(
                f"⚠ المزاد {NUMBER} حالته {auction.state} لا live — "
                "احذفه من اللوحة ثم أعد الأمر"
            )
            return

        self.stdout.write(
            f"المزاد {NUMBER} حيٌّ حتى {ends:%Y-%m-%d %H:%M} — {moved} مركبة"
        )

    def _fill(self, auction: Auction) -> int:
        """انقل إليه مركباتِ آخرِ مزادٍ منتهٍ، بصورها.

        نقلٌ لا نسخ: الصورةُ صفٌّ يشير إلى ملفٍ على القرص، ونسخُها يضاعف
        الملفّات في كل تشغيل. والمزادُ المنتهي مصدرُها لأن مركباته تحمل
        `bidding` أصلاً — فلا نقلةَ حالةٍ تُطلب لها.
        """
        already = auction.vehicles.count()
        if already:
            return already

        source = (
            Auction.objects.filter(state=AuctionState.ENDED)
            .exclude(pk=auction.pk)
            .order_by("-ends_at")
            .first()
        )
        if source is None:
            self.stdout.write("لا مزاد منتهٍ تُنقل مركباتُه — شغّل seed_demo أوّلاً")
            return 0

        return Vehicle.objects.filter(auction=source).update(auction=auction)

    def _stock(self, auction: Auction, count: int) -> int:
        """انسخ مركباتٍ حقيقيّةً إلى المزاد **معروضةً** وبكامل بياناتها. T946.

        **نسخٌ لا نقل** — خلافاً لـ`_fill` فوقه: تلك تأخذ مركبات مزادٍ منتهٍ
        بحالاتها (`invoiced` · `awarded` · `paid`)، فيمتلئ «الجاري» بمركباتٍ
        **حُسم أمرُها** ولا تُزايَد. وهذه تنسخ صفّاً جديداً بحالة `listed`،
        فالأصلُ يبقى في مزاده وتاريخُه لا يُمسّ.

        والمصدرُ مركباتٌ تحمل صانعاً وطرازاً وسنةً ولوحةً وشاصياً — أي ما
        يملأ بطاقةَ التطبيق. وما نقص من عمودٍ عرضيّ (لون · ناقل · وقود ·
        عدّاد) يُملأ من :data:`FILLERS`، والسببُ عندها.

        و`lot_number` يبدأ بعد أكبر رقمٍ في المزاد: رقمان متساويان في مزادٍ
        واحد يجعلان «اللوت ٣» يشير إلى سيّارتين.
        """
        import itertools
        import random

        base = (
            Vehicle.objects.exclude(auction=auction)
            .exclude(make="")
            .exclude(plate_number="")
            .exclude(vin="")
            # **ولا شرطَ على سعر الوقوف.** قِيس على `haraj2_t307`: من ١٣٬٠٠٣
            # مركبةٍ مُرحَّلة **اثنتا عشرةَ** تحمل سعرَ وقوفٍ أكبر من صفر —
            # فالعمودُ لم يأتِ من v1. واشتراطُه يترك المزادَ بمركبتين.
            .filter(year__isnull=False)
        )

        # **ذواتُ الصور أوّلاً.** T950.
        #
        # كانت المركباتُ تُنتقى بالسنة وحدَها، فجاءت كلُّها بلا صورة — وشبكةُ
        # الرئيسيّة أربعٌ وثلاثون بطاقةً تقول «لا توجد صورة». والصورةُ نصفُ
        # البطاقة بالمساحة، فمزادُ اختبارٍ بلا صور لا يُختبَر عليه شيءٌ ممّا
        # يراه العميل.
        #
        # و`prefetch_related` لا استعلامٌ لكلّ مركبة: النسخُ أدناه يقرأ صفوفَ
        # الصور، وقراءتُها واحدةً واحدةً أربعون رحلةً إلى القاعدة.
        with_photos = list(
            base.annotate(shots=Count("images"))
            .filter(shots__gt=0)
            .prefetch_related("images")
            .order_by("-year", "-id")[:count]
        )
        remainder = count - len(with_photos)
        picked = with_photos + (
            list(base.order_by("-year", "-id")[: remainder * 3])[:remainder]
            if remainder > 0
            else []
        )
        if not picked:
            self.stdout.write("لا مركبةَ كاملةَ البيانات تُنسَخ")
            return 0

        top = (
            Vehicle.objects.filter(auction=auction)
            .order_by("-lot_number")
            .values_list("lot_number", flat=True)
            .first()
            or 0
        )
        colours = itertools.cycle(FILLERS["colour"])
        odometers = itertools.cycle(ODOMETERS)
        random.seed(auction.pk)

        made = []
        for offset, car in enumerate(picked, start=1):
            made.append(
                Vehicle(
                    auction=auction,
                    lot_number=top + offset,
                    make=car.make,
                    model=car.model,
                    year=car.year,
                    # لوحةٌ وشاصٍ **جديدان**: كلاهما فريدٌ في القاعدة، ونسخُهما
                    # كما هما يصطدم بالقيد.
                    plate_number=f"ف ح ص {top + offset:04d}",
                    vin=f"TEST{auction.number}{top + offset:06d}",
                    plate_type=car.plate_type,
                    odometer_km=car.odometer_km or next(odometers),
                    colour=(
                        car.colour
                        if car.colour and car.colour != "unknown"
                        else next(colours)
                    ),
                    transmission=(
                        car.transmission
                        if car.transmission and car.transmission != "unknown"
                        else FILLERS["transmission"][0]
                    ),
                    fuel_type=(
                        car.fuel_type
                        if car.fuel_type and car.fuel_type != "unknown"
                        else FILLERS["fuel_type"][0]
                    ),
                    condition=(
                        car.condition
                        if car.condition and car.condition != "unknown"
                        else FILLERS["condition"][0]
                    ),
                    # سعرُ وقوفٍ محسوبٌ حين لا يوجد: أحدثُ سيّارةٍ أغلى،
                    # والمدى يجعل العمودَ يُقرأ عموداً لا رقماً مكرّراً.
                    reserve_price=(
                        car.reserve_price
                        if car.reserve_price and car.reserve_price > 0
                        else _reserve_for(car.year)
                    ),
                    claim_number=car.claim_number or f"CLM-TEST-{top + offset:04d}",
                    insurance_company=car.insurance_company or "شركة تأمين الاختبار",
                    # **معروضة**: هي كلمةُ هذا الأمر كلِّه — مركبةٌ تُزايَد.
                    state=VehicleState.LISTED,
                )
            )

        Vehicle.objects.bulk_create(made, batch_size=200)
        photos = self._copy_photos(picked, made)
        self.stdout.write(
            f"أُضيفت {len(made)} مركبةً معروضةً بكامل بياناتها"
            + (f" · و{photos} صورةً منسوخة" if photos else " · بلا صور")
        )
        return len(made)

    def _copy_photos(self, sources: list[Vehicle], made: list[Vehicle]) -> int:
        """انسخ صفوفَ صور المصدر إلى النسخة — **بمشاركة الملفّ لا بنسخه**.

        الصفُّ الجديد يحمل المسارات الثلاثة نفسَها (الأصل والمصغَّرة
        والمعاينة)، فلا بايت يُكتب على القرص ولا طبقةٌ تُولَّد ثانيةً:
        `add_image` يُعقّم ويُولّد لأن مصدرَه رفعُ مستخدم، وهذه بايتاتٌ
        مرّت بذلك البابِ أصلاً.

        ومشاركةُ الملفّ آمنةٌ هنا: Django لا يحذف ملفَّ حقلٍ عند حذف صفّه
        (سلوكُه منذ 1.3)، فحذفُ نسخةِ الاختبار لا يترك الأصلَ بلا صورة.
        """
        copies = []
        for origin, clone in zip(sources, made, strict=True):
            for shot in origin.images.all():
                copies.append(
                    VehicleImage(
                        vehicle=clone,
                        image=shot.image.name,
                        thumbnail=shot.thumbnail.name,
                        preview=shot.preview.name,
                        position=shot.position,
                        is_cover=shot.is_cover,
                    )
                )
        VehicleImage.objects.bulk_create(copies, batch_size=200)
        return len(copies)
