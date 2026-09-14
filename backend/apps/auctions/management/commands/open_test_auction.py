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

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.auctions.models import Auction, Vehicle
from apps.auctions.services import move_auction
from apps.auctions.states import AuctionState

#: رقمٌ خارج نطاق أرقام البذرة (1001–1004)، فلا يتنازعان على صفٍّ واحد.
NUMBER = 1900

TITLE = "مزاد الاختبار — مفتوح"


class Command(BaseCommand):
    help = "مزادٌ حيٌّ بنافذةٍ طويلة، لفحص الشاشات (DEBUG وحده)"

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--hours",
            type=int,
            default=8760,
            help="كم ساعةً يبقى مفتوحاً (الافتراضي سنة)",
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
