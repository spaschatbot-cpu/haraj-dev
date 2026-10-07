"""مزاداتُ v1 بلا رسومٍ تأخذ رسومَ v1 الافتراضيّة: ٨٠٠.

v1 لا يقرأ الصفرَ صفراً: `BillController.php:643-652` يبدأ بـ`$auctionFees =
800.0` ولا يستبدله إلا برسومٍ **أكبر من صفر** في `auctions.fees`. و`fees` فارغٌ
في ٢٥ من ٥٦ مزاداً (`specs/004-data-migration/field-map.md:332`). أمّا الاستيرادُ
فكتب `or Decimal("0.00")`، فصار كلُّ مزادٍ منها يُفوتِر بلا رسومٍ ولا ضريبتها —
ثمانمئة ريالٍ وضريبتُها تسقط من كلّ فاتورة. والمركباتُ المُرساة بلا فاتورة
(`backfill_awards`) تُفوتَر من «المزايدات المقبولة» على هذا الصفر بالذات.

**ولا يُمسّ صفرٌ قرّره موظّف.** المزادُ الذي أُنشئ في v2 يولد بـ٨٠٠ (افتراضُ
النموذج)، فصفرُه لا يأتي إلا من يدٍ — وكلُّ يدٍ تكتب الرسوم تترك قيداً في
`AuditLog` (`console.auction_fees` و`create_auction` و`edit_auction`). فما
صفرُه بلا قيدٍ هو صفرُ الاستيراد وحده.

**وما صدر لا يتغيّر:** الفاتورةُ تختم رسومَها لحظةَ الإصدار (`Invoice.admin_fee`)،
فهذا يمسّ الفواتيرَ القادمة وحدها.
"""

from decimal import Decimal

from django.db import migrations

FEE_WRITERS = ("console.auction_fees", "console.create_auction", "console.edit_auction")


def forwards(apps, schema_editor):
    Auction = apps.get_model("auctions", "Auction")
    AuditLog = apps.get_model("core", "AuditLog")

    chosen_by_staff = set(
        AuditLog.objects.filter(
            entity_type="auctions.auction", action__in=FEE_WRITERS
        ).values_list("entity_id", flat=True)
    )
    for auction in Auction.objects.filter(admin_fee=Decimal("0.00")):
        if str(auction.pk) in chosen_by_staff:
            continue
        auction.admin_fee = Decimal("800.00")
        auction.save(update_fields=["admin_fee"])


class Migration(migrations.Migration):
    dependencies = [
        ("auctions", "0018_vehicle_payment_receipt"),
        ("core", "0001_initial"),
    ]

    # لا رجوع: الصفرُ الذي يُعاد لا يُعرف أيُّه كان صفراً. ورجوعُ الهجرة يتركها.
    operations = [migrations.RunPython(forwards, migrations.RunPython.noop)]
