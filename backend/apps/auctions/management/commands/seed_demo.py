"""بذرةُ عرضٍ للتطوير: بيانات تُرى على الشاشات، مبنيّةٌ بالخدمات لا بالإدراج.

**لماذا وُجد هذا الأمر.** قاعدة التطوير كان فيها مزادات ومركبات ومستخدمون —
وصفرُ صورة وصفرُ مزايدة وصفرُ فاتورة. فالشاشات تعمل وتعرض لا شيء، وهي أسوأ
حالٍ للاختبار: من ينظر لا يعرف أعُطلٌ في الشاشة أم فراغٌ في البيانات.

**والقاعدة الحاكمة: يُبنى بالخدمات لا بـ`objects.create`.** كل مزايدةٍ هنا
تمرّ ببوابة الأهلية، وكل ريالٍ يمرّ بـ`money.services.post`، وكل صورةٍ تمرّ
بـ`add_image` فتُولَّد طبقاتها. فبذرةٌ تنجح تعني أن المسار الحقيقي يعمل —
وبذرةٌ تُدرِج صفوفاً مباشرةً تُنتج قاعدةً جميلةً لا يشبهها الإنتاج في شيء،
وتُخفي بالضبط الأعطال التي يُراد للاختبار أن يجدها.

**وخاملٌ:** يُعاد تشغيله فلا يضاعف. ما وُجد يُترك، وما نقص يُكمَّل.

**ولا يعمل خارج `DEBUG`.** بيانات عرضٍ في الإنتاج ليست خطأً يُصلَح، هي دفترُ
مالٍ ملوَّث.

    python manage.py seed_demo
    python manage.py seed_demo --images 4 --bidders 6
"""

from __future__ import annotations

from decimal import Decimal
from io import BytesIO

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from PIL import Image, ImageDraw

from apps.accounts import services as accounts
from apps.accounts.models import User
from apps.auctions import services as auction_services
from apps.auctions.models import Auction, Vehicle
from apps.auctions.states import AuctionState, VehicleState
from apps.bidding import services as bidding
from apps.bidding import settlement
from apps.money import services as money
from apps.money.models import AccountKind

DEPOSIT = Decimal("10000.00")

#: مركباتٌ تُقرأ على الشاشة كأنها حقيقية — واسمُ المزاد يفرّقها.
FLEET = [
    ("تويوتا", "كامري", 2022, "أوتوماتيك", "بنزين", 45_000, "70000.00", (196, 30, 58)),
    ("لكزس", "ES 350", 2021, "أوتوماتيك", "بنزين", 62_000, "120000.00", (28, 42, 74)),
    ("نيسان", "التيما", 2020, "أوتوماتيك", "بنزين", 98_000, "48000.00", (240, 240, 245)),
    ("هيونداي", "سوناتا", 2023, "أوتوماتيك", "بنزين", 21_000, "82000.00", (18, 18, 22)),
    ("شفروليه", "تاهو", 2019, "أوتوماتيك", "بنزين", 140_000, "95000.00", (120, 124, 130)),
    ("فورد", "F-150", 2021, "أوتوماتيك", "بنزين", 77_000, "110000.00", (10, 66, 120)),
    (
        "جي إم سي",
        "يوكن",
        2022,
        "أوتوماتيك",
        "بنزين",
        39_000,
        "165000.00",
        (245, 245, 248),
    ),
]


def a_photograph(vehicle: Vehicle, index: int, colour: tuple) -> SimpleUploadedFile:
    """صورةٌ مولَّدة تُميَّز بالعين: لونُ المركبة، ورقمُ اللقطة، ولوتُها.

    ليست صورةَ سيارة، ولا تدّعي: الغرض أن تُرى البطاقةُ مملوءةً وأن تُختبَر
    الطبقات (HR-12)، لا أن يُخدَع الناظر. وحجمُها كبيرٌ عمداً (1600×1200)
    ليكون التصغير مرئياً في الأرقام.
    """
    picture = Image.new("RGB", (1600, 1200), colour)
    draw = ImageDraw.Draw(picture)
    ink = (255, 255, 255) if sum(colour) < 380 else (20, 20, 20)
    draw.rectangle([60, 60, 1540, 1140], outline=ink, width=6)
    draw.text((110, 130), f"{vehicle.make} {vehicle.model}", fill=ink)
    draw.text((110, 190), f"{vehicle.year}  ·  LOT {vehicle.lot_number}", fill=ink)
    draw.text((110, 250), f"صورة {index + 1} — بيانات عرض", fill=ink)
    buffer = BytesIO()
    picture.save(buffer, format="PNG")
    return SimpleUploadedFile(
        f"demo-{vehicle.pk}-{index}.png", buffer.getvalue(), content_type="image/png"
    )


class Command(BaseCommand):
    help = "بيانات عرضٍ للتطوير: صور ومزايدات وفواتير على المزادات الثلاثة."

    def add_arguments(self, parser) -> None:
        parser.add_argument("--images", type=int, default=3, help="صور لكل مركبة")
        parser.add_argument("--bidders", type=int, default=6, help="عدد المزايدين")

    def handle(self, *args, **options) -> None:
        if not settings.DEBUG:
            raise CommandError(
                "بذرة العرض لا تعمل خارج DEBUG. بياناتٌ كهذه في الإنتاج ليست "
                "خطأً يُصلَح، هي دفترُ مالٍ ملوَّث."
            )

        bidders = self.customers(options["bidders"])
        auctions = self.auctions()
        self.vehicles(auctions)
        self.images(options["images"])
        # **مجموعتان لا واحدة.** الفائز في الدورة الكاملة تصير عليه فاتورة،
        # وبوابةُ الأهلية ترفض مزايدةَ من عليه مستحقّ (`unpaid_dues`) — وهي
        # محقّة. فلو زايدت المجموعةُ نفسها على الاثنين لرُفض كلُّ شيء بعد
        # الفوترة، وبدت الشاشة معطوبة والبوابةُ تعمل تماماً. وقع ذلك فعلاً.
        self.bids(auctions["live"], bidders[:3])
        self.full_cycle(bidders[3:])
        self.summary()

    # -- المستخدمون ---------------------------------------------------------

    def customers(self, count: int) -> list[User]:
        """مزايدون موثَّقو الجوال ومموَّلون بالوديعة المطلوبة بالضبط.

        بالضبط لا أكثر (HR-01ب): وسادةٌ فوق الوديعة تجعل كل بوابةٍ تجد ما
        تأخذه، فتمرّ الشاشات على حالةٍ لا تقع في الإنتاج.
        """
        people = []
        for index in range(count):
            phone = f"9665511111{index:02d}"
            # ‏`user_for_verified_phone` هو ما يُنشئ حساباً بجوالٍ مُثبَت
            # ويختمه بوقت التوثيق — وهو الطريق نفسه الذي يسلكه الدخول
            # الحقيقي. وقراءةُ `phone_verified_at` هنا بيدي كانت شرطَ أهليةٍ
            # يُقرأ خارج بوابته، وأمسكها `one_eligibility_gate` بحق.
            user, created = accounts.user_for_verified_phone(
                phone=phone, full_name=f"عميل تجريبي {index + 1}"
            )
            if created:
                user.national_id = f"10000000{index:02d}"
                user.save(update_fields=["national_id"])
            self.fund(user)
            people.append(user)
        self.stdout.write(f"مزايدون: {len(people)}")
        return people

    # -- المزادات -----------------------------------------------------------

    def auctions(self) -> dict[str, Auction]:
        """واحدٌ لكل طور، فتُرى التبويبات الثلاثة مملوءة."""
        now = timezone.now()
        wanted = {
            "soon": (1002, "مزاد الرياض — الأسبوع القادم", 3, 10, AuctionState.SCHEDULED),
            "live": (1001, "مزاد الرياض — الجاري", -2, 6, AuctionState.LIVE),
            "ended": (1003, "مزاد جدة — المنتهي", -240, -216, AuctionState.ENDED),
        }
        found = {}
        for key, (number, title, starts, ends, state) in wanted.items():
            auction, created = Auction.objects.get_or_create(
                number=number,
                defaults={
                    "title": title,
                    "starts_at": now + timezone.timedelta(hours=starts),
                    "ends_at": now + timezone.timedelta(hours=ends),
                    "state": state,
                    "deposit_required": DEPOSIT,
                },
            )
            # **تُجدَّد النافذة في كل تشغيل، وهذا ليس تجميلاً.** بذرةٌ تكتب
            # `ends_at` مرّةً تُنتج بعد يومين مزاداً حالتُه `live` ووقتُه
            # انتهى — فترفض بوابةُ الأهلية كلَّ مزايدة بـ`auction_ended`
            # والشاشة تبدو معطوبة. وقع ذلك فعلاً في أول تشغيل: سبعُ مركبات
            # معروضة وصفرُ مزايدة، والسبب تاريخٌ لا شيفرة.
            #
            # و1004 مستثنى: تلك دورةٌ كاملة تنتهي عمداً (انظر `full_cycle`).
            fresh_start = now + timezone.timedelta(hours=starts)
            fresh_end = now + timezone.timedelta(hours=ends)
            if not created and auction.ends_at != fresh_end:
                # **الوقت وحده يُكتب هنا، لا الحالة.** كتابة `state` بـ`update`
                # تتخطّى آلة الحالات، وأمسكها `auction_state_single_writer`
                # بحق: بذرةٌ تُجبر حالةً هي بذرةٌ تُنتج قاعدةً لا تصلها آلةُ
                # الحالات أبداً — وذلك نقضُ ما تقوله هذه البذرة عن نفسها في
                # سطرها الأول.
                Auction.objects.filter(pk=auction.pk).update(
                    starts_at=fresh_start, ends_at=fresh_end
                )
                auction.refresh_from_db()
                self.stdout.write(f"  جُدِّدت نافذة المزاد {auction.number}")
            if auction.state != state:
                self.stdout.write(
                    f"  ⚠ المزاد {auction.number} حالته {auction.state} لا {state}"
                    " — تُنقَل بآلة الحالات لا بالبذرة"
                )

            found[key] = auction
            self.stdout.write(
                f"مزاد {auction.number}: {auction.state}" + (" (جديد)" if created else "")
            )
        return found

    def vehicles(self, auctions: dict[str, Auction]) -> None:
        spread = {"live": FLEET[:4], "soon": FLEET[4:6], "ended": FLEET[6:]}
        for key, fleet in spread.items():
            auction = auctions[key]
            state = {
                "live": VehicleState.BIDDING,
                "soon": VehicleState.LISTED,
                "ended": VehicleState.LISTED,
            }[key]
            for lot, row in enumerate(fleet, start=1):
                make, model, year, gear, fuel, km, reserve, _ = row
                Vehicle.objects.get_or_create(
                    auction=auction,
                    lot_number=lot,
                    defaults={
                        "make": make,
                        "model": model,
                        "year": year,
                        "vin": f"DEMO{auction.number}{lot:03d}00000",
                        "odometer_km": km,
                        "transmission": "automatic",
                        "fuel_type": "petrol",
                        "condition": "running",
                        "reserve_price": Decimal(reserve),
                        "state": state,
                    },
                )
        self.stdout.write(f"مركبات: {Vehicle.objects.count()}")

    # -- الصور --------------------------------------------------------------

    def images(self, per_vehicle: int) -> None:
        """تمرّ بـ`add_image`، فتُولَّد طبقاتها (HR-12) كما في الإنتاج."""
        colours = {row[1]: row[7] for row in FLEET}
        added = 0
        for vehicle in Vehicle.objects.filter(images__isnull=True).distinct():
            colour = colours.get(vehicle.model, (90, 96, 104))
            for index in range(per_vehicle):
                auction_services.add_image(
                    vehicle,
                    a_photograph(vehicle, index, colour),
                    position=index,
                    cover=(index == 0),
                )
                added += 1
        self.stdout.write(f"صور مضافة: {added}")

    # -- المزايدات ----------------------------------------------------------

    def settle_dues(self, people: list[User]) -> None:
        """تُسدَّد مستحقّات مزايدي العرض قبل جولةٍ جديدة.

        **وإلا لم يكن الأمر خاملاً عملياً.** تشغيلةٌ سابقة تترك على أحدهم
        فاتورة، فترفض البوابةُ مزايدته في التشغيلة التالية بـ`unpaid_dues` —
        وهي محقّة تماماً، لكنّ النتيجة مزادٌ حيّ بلا مزايدة يقرؤه الناظر
        عطلاً في الشاشة. فالبذرة تُنظّف أثرَها هي، ولا تُرخي البوابة.
        """
        from apps.money.models import Invoice, InvoiceState

        for invoice in Invoice.objects.filter(
            customer__in=people, state__in=[InvoiceState.OPEN, InvoiceState.PARTIAL]
        ):
            # المبلغ كلّه لا المتبقّي: أكثرُ ممّا يلزم دائماً، ولا يُقرأ
            # `outstanding` خارج بوابته (`one_eligibility_gate`).
            money.deposit_insurance(
                user=invoice.customer,
                amount=invoice.amount,
                source="cash",
                reference=f"demo/clear/{invoice.number}",
            )
            money.pay_invoice_from_balance(user=invoice.customer, invoice=invoice)
            self.stdout.write(f"  سُدِّدت {invoice.number} لتحرير المزايد")

        # ثم يُعاد التمويل: السداد استهلك الوديعة، فبوابةُ الأهلية ترفض
        # التالية بـ`no_deposit` — وهي محقّة أيضاً. ترتيبُ الخطوتين هو
        # المسألة، لا أيٌّ منهما.
        for person in people:
            self.fund(person)

    def fund(self, user: User) -> None:
        """يُرفَع رصيده إلى الوديعة المطلوبة بالضبط — لا أكثر (HR-01ب)."""
        free = money.account_for(user, AccountKind.INSURANCE_FREE).balance
        held = money.account_for(user, AccountKind.INSURANCE_HELD).balance
        if free + held < DEPOSIT:
            money.deposit_insurance(
                user=user,
                amount=DEPOSIT - free - held,
                source="cash",
                reference=f"demo/fund/{user.phone}/{timezone.now():%Y%m%d%H%M%S}",
            )

    def bids(self, auction: Auction, bidders: list[User]) -> None:
        """تمرّ ببوابة الأهلية الحقيقية — فالمرفوض يُسجَّل في `BidRefusal`."""
        self.settle_dues(bidders)
        placed = refused = 0
        # ‏`listed` و`bidding` كلتاهما: المركبة تدخل المزاد معروضة وتصير
        # `bidding` بأول مزايدة، فقصرُ البذرة على `bidding` يعني ألّا تُزايد
        # على شيء أبداً — وهو ما وقع في أول تشغيل. والبوابة هي التي تقرّر،
        # لا هذا السطر.
        cars = list(
            auction.vehicles.filter(state__in=[VehicleState.LISTED, VehicleState.BIDDING])
        )
        for position, vehicle in enumerate(cars):
            floor = vehicle.reserve_price or Decimal("40000.00")
            for step, bidder in enumerate(bidders[: 3 + (position % 2)]):
                amount = floor + Decimal(1000 * (step + 1))
                try:
                    bidding.place_bid(user=bidder, vehicle=vehicle, amount=amount)
                    placed += 1
                except Exception as exc:  # noqa: BLE001 — الرفض بيانٌ لا انهيار
                    refused += 1
                    self.stdout.write(f"  رُفضت مزايدة: {exc}")
        self.stdout.write(f"مزايدات: {placed} مقبولة، {refused} مرفوضة")

    # -- دورةٌ كاملة: مزادٌ يُفتح ويُزايَد عليه ويُغلَق ويُفوتَر -----------

    def full_cycle(self, bidders: list[User]) -> None:
        """مزادٌ رابع يمرّ بدورته كلّها، فتُرى الفاتورة وقفلُ الوديعة.

        **ولا تُخترع ترسية.** `award_to` يرفض ترسيةً بلا مزايدةٍ حيّة خلفها،
        وهو محقّ: ترسيةٌ مكتوبةٌ بيدٍ لا مزايدةَ وراءها ولا مالَ تحرّك هي
        بالضبط ما تحذّر منه الوثائق. فيُفتح مزادٌ حقيقيّ، ويُزايَد عليه
        بالخدمة، ثم يُغلَق بآلة الحالات، ثم تُسوّى ويُفوتَر الفائز.

        وهذا ما يجعل البذرة اختباراً لا زينة: إن انكسر أيُّ حلقةٍ في السلسلة
        سقط الأمر هنا، لا في متصفّح أحدهم بعد أسبوع.
        """
        now = timezone.now()
        auction, created = Auction.objects.get_or_create(
            number=1004,
            defaults={
                "title": "مزاد الدمّام — دورة كاملة",
                "starts_at": now - timezone.timedelta(hours=3),
                "ends_at": now + timezone.timedelta(minutes=5),
                "state": AuctionState.LIVE,
                "deposit_required": DEPOSIT,
            },
        )
        if auction.state == AuctionState.ENDED:
            self.stdout.write(f"مزاد {auction.number}: مُسوّى بالفعل")
            return

        for lot, row in enumerate(FLEET[:2], start=1):
            make, model, year, _gear, _fuel, km, reserve, _ = row
            Vehicle.objects.get_or_create(
                auction=auction,
                lot_number=lot,
                defaults={
                    "make": make,
                    "model": model,
                    "year": year,
                    "vin": f"DEMO1004{lot:03d}00000",
                    "odometer_km": km,
                    "transmission": "automatic",
                    "fuel_type": "petrol",
                    "condition": "running",
                    "reserve_price": Decimal(reserve),
                    "state": VehicleState.BIDDING,
                },
            )

        for position, car in enumerate(auction.vehicles.all()):
            floor = car.reserve_price or Decimal("40000.00")
            for step, bidder in enumerate(bidders[: 2 + position]):
                try:
                    bidding.place_bid(
                        user=bidder,
                        vehicle=car,
                        amount=floor + Decimal(2000 * (step + 1)),
                    )
                except Exception as exc:  # noqa: BLE001 — الرفض بيانٌ لا انهيار
                    self.stdout.write(f"  رُفضت مزايدة الدورة: {exc}")

        # ينتهي وقته، ثم يُغلَق بآلة الحالات لا بكتابة عمود.
        Auction.objects.filter(pk=auction.pk).update(
            ends_at=timezone.now() - timezone.timedelta(minutes=1)
        )
        auction.refresh_from_db()
        auction_services.end(auction)
        report = settlement.settle_auction(auction)

        invoices = []
        for car in auction.vehicles.filter(state=VehicleState.AWARDED):
            invoices.append(settlement.invoice_award(car))

        # واحدةٌ تُسدَّد وواحدةٌ تبقى: الشاشة تحتاج الحالتين، ومسارُ السداد من
        # الرصيد هو الذي يُدرِج الدفعة في الصادر إلى أودو (HR-17).
        paid = 0
        for invoice in invoices[:1]:
            money.deposit_insurance(
                user=invoice.customer,
                amount=invoice.amount,
                source="cash",
                reference=f"demo/settle/{invoice.number}",
            )
            money.pay_invoice_from_balance(user=invoice.customer, invoice=invoice)
            paid += 1

        self.stdout.write(
            f"مزاد {auction.number}: {len(report.vehicles)} مُسوّاة، "
            f"{len(invoices)} فاتورة، منها {paid} مسدَّدة"
        )

    # -- ماذا صار ------------------------------------------------------------

    def summary(self) -> None:
        from apps.auctions.models import VehicleImage
        from apps.bidding.models import Bid
        from apps.money.models import Invoice
        from apps.money.verification import verify_ledger

        self.stdout.write("")
        for label, count in (
            ("مزادات", Auction.objects.count()),
            ("مركبات", Vehicle.objects.count()),
            ("صور", VehicleImage.objects.count()),
            ("مزايدات", Bid.objects.count()),
            ("فواتير", Invoice.objects.count()),
        ):
            self.stdout.write(f"{label:10} {count}")
        problems = verify_ledger()
        self.stdout.write("الدفتر: نظيف" if not problems else f"الدفتر: {problems}")
