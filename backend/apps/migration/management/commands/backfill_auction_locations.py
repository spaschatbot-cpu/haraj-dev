"""موقعُ المزاد من `auction_vehicles.preview_site` — وكان فارغاً في كلّ مزادٍ منقول.

    python manage.py backfill_auction_locations --dump … --dry-run
    python manage.py backfill_auction_locations --dump …

## العطل، كما رآه المالك (٢٤ نوفمبر ٢٠٢٦)

«بيانات السيارة مش كاملة… لو شفتها في الموقع الأساسي هتلاقي بيانات أكتر».
وأوّلُ ما يُرى: v1 يكتب تحت كلّ سيّارة «الرياض / طريق الحائر»، وv2 يكتب
«المدينة —». والسببُ أن v1 لا يحمل الموقعَ على المزاد أصلاً: `auctions` بلا
عمودِ مكان، والمكانُ في **`auction_vehicles.preview_site`** لكلّ سيّارة —
وهو عمودٌ لم يقرأه الجسرُ قطّ. وفي v2 الموقعُ على المزاد (`Auction.location`)
وتأخذه كلُّ مركباته.

## ولماذا الأكثرُ تكراراً لا الأوّل

المزادُ في v1 حوشٌ واحد، فسيّاراتُه كلُّها تحمل المكانَ نفسَه في الغالب
(قِيس على المزاد 1030: ٣٤٤ من ٣٤٤). وحين يختلف صفٌّ يُؤخذ ما عليه الأكثر —
لا الأوّل الذي قد يكون الشاذّ.

## ولا يكتب فوق شيء

يملأ الفارغَ وحدَه، كأخويه `backfill_v1_fields` و`backfill_awards`: موقعٌ
كتبه موظّفٌ من اللوحة بعد الترحيل لا يُستبدل.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.auctions.models import Auction
from apps.migration.dumpfile import read_table


def sites_by_auction(path: Path) -> dict[int, str]:
    """رقمُ مزاد v1 ⟶ المكانُ الأكثرُ تكراراً بين سيّاراته."""
    counts: dict[int, Counter] = defaultdict(Counter)
    for row in read_table(path, "auction_vehicles"):
        site = " ".join(str(row.get("preview_site") or "").split())
        auction = str(row.get("auction_id") or "")
        if site and auction.isdigit():
            counts[int(auction)][site] += 1
    return {number: c.most_common(1)[0][0][:200] for number, c in counts.items()}


class Command(BaseCommand):
    help = "يملأ موقعَ المزادات المنقولة من `preview_site` في نسخة v1."

    def add_arguments(self, parser):
        parser.add_argument("--dump", required=True, help="مسارُ نسخة mysqldump")
        parser.add_argument("--dry-run", action="store_true", help="اقرأ ولا تكتب")

    def handle(self, *args, **options):
        path = Path(options["dump"])
        if not path.exists():
            raise CommandError(f"لا نسخةَ في {path}")

        sites = sites_by_auction(path)
        # رقمُ المزاد في v2 هو رقمُه في v1 (`import_v1`: `number=int(row["id"])`).
        empty = Auction.objects.filter(number__in=sites, location="")
        written = 0
        for auction in empty:
            if not options["dry_run"]:
                Auction.objects.filter(pk=auction.pk, location="").update(
                    location=sites[auction.number]
                )
            written += 1

        top = Counter(sites.values()).most_common(3)
        self.stdout.write(f"مزاداتٌ لها مكانٌ في النسخة: {len(sites)}")
        self.stdout.write("الأكثر: " + " · ".join(f"{s} ×{n}" for s, n in top))
        verb = "سيُكتب" if options["dry_run"] else "كُتب"
        self.stdout.write(f"{verb}: {written} مزاداً كان موقعُه فارغاً")
