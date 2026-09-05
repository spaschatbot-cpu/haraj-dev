"""Fill in rendered copies for photographs that predate their tier. HR-12.

Generation happens at upload (`services.add_image`), which covers every
photograph taken from today on and none of the ones already on disk. The
incident is about the ones already on disk: 13 GB of originals uploaded before
anything resized them.

**Why a command and not a data migration.** A migration that opens and
re-encodes every photograph in the table runs inside `migrate`, on a deploy,
with a lock held and nobody able to stop it — and it runs again the same way
on the next environment. Re-encoding 13 GB is minutes to hours of CPU that has
nothing to do with the schema. So the schema change is a migration, and the
pixels are this: run when somebody decides to, interruptible, and safe to run
again because it only fills what is missing.

**A missing original is reported, not raised.** After a migration from v1 some
rows will name files that are not there, and a command that dies on the first
one leaves the other forty thousand unrendered. The count is printed so the
gap is a number somebody can act on rather than a silent skip.
"""

from __future__ import annotations

from django.core.management.base import BaseCommand

from apps.auctions.images import RENDERED_SUFFIX, TIERS, render
from apps.auctions.models import VehicleImage


class Command(BaseCommand):
    help = "توليد النسخ المصغّرة والمعاينة للصور التي رُفعت قبل وجودها (HR-12)."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--all",
            action="store_true",
            help="أعد التوليد حتى لما له نسخة — بعد تغيير مقاس في images.TIERS.",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=0,
            help="أوقف بعد هذا العدد من الصور. صفر يعني بلا حدّ.",
        )

    def handle(self, *args, **options) -> None:
        redo = options["all"]
        limit = options["limit"]

        rendered = 0
        skipped_complete = 0
        missing_original = 0

        for image in VehicleImage.objects.order_by("pk").iterator():
            wanted = [tier for tier in TIERS if redo or not getattr(image, tier.field)]
            if not wanted:
                skipped_complete += 1
                continue

            if not image.image or not image.image.storage.exists(image.image.name):
                missing_original += 1
                self.stderr.write(
                    f"صورة {image.pk}: الأصل غير موجود على القرص "
                    f"({image.image.name or 'بلا اسم'}) — لا نسخة تُولَّد منه."
                )
                continue

            for tier in wanted:
                getattr(image, tier.field).save(
                    f"{tier.field}{RENDERED_SUFFIX}",
                    render(image.image, tier),
                    save=False,
                )
            image.save(update_fields=[tier.field for tier in wanted])
            rendered += 1

            if limit and rendered >= limit:
                break

        self.stdout.write(
            f"وُلِّدت نسخٌ لـ{rendered} صورة، و{skipped_complete} كانت مكتملة، "
            f"و{missing_original} أصلها مفقود."
        )
