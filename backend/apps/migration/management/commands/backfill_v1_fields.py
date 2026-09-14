"""تعبئةُ حقولٍ سقطت من الجسر — **الفارغَ وحدَه، ولا تلمس ما عداه**.

لماذا أمرٌ مستقلٌّ لا إعادةُ ترحيل
==================================
`import_v1` يكتب بـ``bulk_create(ignore_conflicts=True)``: إعادةُ تشغيله على
قاعدةٍ مبنيّةٍ **لا تُحدِّث صفّاً واحداً** — الصفوفُ موجودةٌ فيُتجاهَل التعارضُ
وتمرّ. فإصلاحُ الجسر يخدم اللقطةَ القادمة، ولا يُصلح ما بُني.

والبديلُ (حذفُ الجدولين وإعادةُ البناء) يمسّ ما لا علاقةَ له بالعطل: مزاداتُ
امتحانٍ وفواتيرُ وحركاتُ دفترٍ وحساباتُ موظّفين بُنيت فوق هذه الصفوف طوال
أسبوع، وبعضُها مرجعٌ في `AuditLog`. **فالتعبئةُ تكتب الفارغَ وتترك المملوء.**

ما كُشف، وكيف
==============
قُورنت أعمدةُ اللقطة بما يقرؤه الجسر (٢٠٢٦-٠٩-١٤)، فظهر **أحدَ عشرَ عموداً
مملوءاً في v1 ولا يذكرها الجسرُ إطلاقاً**. وهذا الأمرُ يعالج ثلاثةً منها —
الثلاثةَ التي لها حقلٌ عندنا:

* **اسمُ العميل**: الجسرُ يقرأ ``row["name"]`` و``row["full_name"]``،
  **وكلاهما عمودٌ لا وجود له في `userss`** — واسمُه هناك ``arabic_name``.
  فسقطت القراءةُ إلى الفراغ صامتةً: ١٦٬١٩٦ اسماً في اللقطة، وخمسةٌ عندنا من
  ٤٤٬٠٤٠. وأثرُه يُقرأ شاشةً: «المزايد —» في كلّ صفّ، وبحثٌ بالاسم يعطي صفراً.
* **اللون** (١٣٬٠٧٢ صفّاً في اللقطة) و**الحالة الفنّيّة** (١٣٬٠٤٨): لم
  يُذكرا في الجسر أصلاً، فكلُّ مركبةٍ ``unknown``.

**ولم يرمِ شيءٌ ولم يُكتب سطرٌ في سجلّ** — لأن `dict.get` تُرجع ``None``
لمفتاحٍ غيرِ موجودٍ كما تُرجعه لقيمةٍ فارغة. **عمودٌ أُسيء اسمُه وعمودٌ خالٍ
يبدوان سواءً**، وذلك سببُ بقاء العطل شهراً.

القواعد
=======
* **الفارغُ وحدَه يُملأ.** اسمٌ كتبه موظّفٌ في اللوحة أحدثُ من لقطة سبتمبر، ولا
  يُدهَس بها.
* **ولا يُلمس ما ليس في اللقطة**: المطابقةُ بالجوّال للعميل و
  بـ(مزاد، لوت) للمركبة — وهما مفتاحا الجسر نفسُهما.
* **وما لم يُترجَم يُعَدّ ويُقال** بأمثلةٍ منه. قيمةٌ جديدةٌ في لقطةٍ قادمة
  تُرى، ولا تُبتلَع في ``other`` صامتة.
"""

from __future__ import annotations

import collections
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.accounts.models import User
from apps.auctions.models import Auction, Vehicle
from apps.migration.dumpfile import read_table
from apps.migration.vocab import colour_of, condition_of

BATCH = 1000


class Command(BaseCommand):
    help = "يملأ الاسمَ واللونَ والحالةَ الفنّيّة من لقطة v1 — الفارغَ وحدَه."

    def add_arguments(self, parser):
        parser.add_argument("--path", default=str(getattr(settings, "V1_DUMP_PATH", "")))
        parser.add_argument(
            "--dry",
            action="store_true",
            help="اقرأ وقِس ولا تكتب — الرقمُ نفسُه بلا أثر.",
        )

    def handle(self, *args, **options):
        path = Path(options["path"])
        if not path.exists():
            self.stderr.write(f"لا لقطةَ في {path}")
            return

        self.dry = options["dry"]
        if self.dry:
            self.stdout.write("— قراءةٌ بلا كتابة —")

        self._people(path)
        self._vehicles(path)

    # ---------------------------------------------------------------- الأشخاص
    def _people(self, path: Path) -> None:
        """الاسمُ من ``arabic_name``، ثمّ ``english_name`` لمن لا عربيَّ له."""
        blank = {
            phone: pk
            for pk, phone in User.objects.filter(full_name="").values_list("pk", "phone")
        }
        self.stdout.write(f"عملاءُ بلا اسمٍ عندنا: {len(blank)}")

        from apps.migration.management.commands.import_v1 import phone_of

        updates: list[User] = []
        seen = missing = 0
        for row in read_table(path, "userss"):
            seen += 1
            phone = phone_of(row.get("phone"))
            pk = blank.get(phone) if phone else None
            if pk is None:
                continue
            name = (row.get("arabic_name") or row.get("english_name") or "").strip()
            if not name:
                missing += 1
                continue
            updates.append(User(pk=pk, full_name=name[:150]))

        self.stdout.write(
            f"  قُرئ {seen} صفّاً · طابق {len(updates)} اسماً · "
            f"{missing} مطابقاً بلا اسمٍ في اللقطة"
        )
        self._write(User, updates, ["full_name"])

    # --------------------------------------------------------------- المركبات
    def _vehicles(self, path: Path) -> None:
        """اللونُ والحالةُ الفنّيّة، بمفتاح (رقمُ المزاد، اللوت) كالجسر."""
        auctions = dict(Auction.objects.values_list("number", "pk"))
        blank = {
            (auction_id, lot): pk
            for pk, auction_id, lot in Vehicle.objects.filter(
                colour="unknown"
            ).values_list("pk", "auction_id", "lot_number")
        }
        self.stdout.write(f"مركباتٌ بلا لونٍ عندنا: {len(blank)}")

        updates: list[Vehicle] = []
        unmapped: collections.Counter = collections.Counter()
        for row in read_table(path, "auction_vehicles"):
            # **مفتاحا الجسر نفسُهما** (`import_v1._vehicles`): `Auction.number`
            # هو مُعرِّفُ مزاد v1 حرفياً، واللوتُ `lot_number` وإلّا فمُعرِّفُ
            # الصفّ. وأيُّ مفتاحٍ آخر يطابق صفراً — جرّبتُ `id_park` فأعطى صفراً،
            # وهو رقمُ موقفٍ لا رقمُ لوت.
            auction_pk = auctions.get(_int(row.get("auction_id")))
            lot = _int(row.get("lot_number")) or _int(row.get("id"))
            pk = blank.get((auction_pk, lot))
            if pk is None:
                continue
            raw = (row.get("the_color") or "").strip()
            colour = colour_of(raw)
            if colour == "other" and raw:
                unmapped[raw] += 1
            updates.append(
                Vehicle(
                    pk=pk,
                    colour=colour,
                    condition=condition_of(row.get("vehicle_condition")),
                )
            )

        self.stdout.write(f"  طابق {len(updates)} مركبة")
        if unmapped:
            top = " · ".join(f"{name}×{count}" for name, count in unmapped.most_common(6))
            self.stdout.write(
                f"  لونٌ خارج تعدادنا ⇐ «أخرى»: {sum(unmapped.values())} صفّاً "
                f"في {len(unmapped)} قيمة — {top}"
            )
        self._write(Vehicle, updates, ["colour", "condition"])

    # ----------------------------------------------------------------- الكتابة
    def _write(self, model, rows: list, fields: list[str]) -> None:
        if self.dry:
            self.stdout.write(f"  (لم يُكتب شيء — {len(rows)} صفّاً كانت ستُحدَّث)")
            return
        with transaction.atomic():
            model.objects.bulk_update(rows, fields, batch_size=BATCH)
        self.stdout.write(self.style.SUCCESS(f"  كُتب {len(rows)} صفّاً"))


def _int(value) -> int | None:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None
