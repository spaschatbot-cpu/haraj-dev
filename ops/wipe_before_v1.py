"""يُفرغ نطاقَ اللوحة قبل ترحيلٍ كامل من v1 — ويستثني من يفتح اللوحة.

    python manage.py shell < ops/wipe_before_v1.py          # يعدّ ويطبع
    WIPE=yes python manage.py shell < ops/wipe_before_v1.py # يمحو

لماذا ليس `drop_demo`
=====================
`drop_demo` يمحو **بيانات العرض** — مزادات ١٠٠١ و١٠٠٢ و١٠٠٣ والعملاء
التجريبيّين ودفترَ القياس — ويستثني بياناتِ v1 صراحةً. والموجودُ على الإنتاج
اليوم أرقامُ v1 نفسُها (#1008 · #1010 · #1012 · #1017 · #1018)، أي شريحةٌ
جزئيّةٌ حُمِّلت في ١٣ سبتمبر ٢٠٢٦ بلا صفٍّ واحدٍ في `migration_legacyref`.
فهي ليست «عرضاً» يمحوه ذلك الأمر، وتركُها يعني مزاداتٍ مكرّرةً بعد الترحيل.

ما يُمحى، وبهذا الترتيب
=======================
الترتيبُ من الورقة إلى الجذر، وإلّا رفضت المفاتيحُ الأجنبيّة. والمالُ أوّلاً
لأن كلَّ شيءٍ يرهن عليه.

ما لا يُمحى
===========
* **حسابات الموظّفين** (`is_staff=True`) — ومحوُ حسابِ المالك يُقفل اللوحة
  على صاحبها بلا طريقِ عودة.
* **أقسامُ الدعم وشريطُ الأخبار والباقات** — محتوىً يكتبه الموظّف، لا يأتي
  من v1 ولا يعيده الترحيل.

وقبل تشغيله تُؤخذ نسخةٌ احتياطيّة. المحوُ لا يُعكَس.
"""

import os

from django.db import transaction

from apps.accounts.models import Company, CustomerDocument, NationalAddress, User
from apps.auctions.models import Auction, Favourite, Vehicle, VehicleImage
from apps.bidding.models import Bid
from apps.migration.models import LegacyRef
from apps.money.models import (
    Account,
    Entry,
    Hold,
    Invoice,
    PaymentIntent,
    RefundRequest,
    Transaction,
)

#: من الورقة إلى الجذر. الاسمُ يُطبع كما هو، فالعدُّ يُقرأ قبل المحو وبعده.
ORDER = [
    ("قيود الدفتر", Entry),
    ("المعاملات", Transaction),
    ("الحجوزات", Hold),
    ("نيّات الدفع", PaymentIntent),
    ("طلبات الاسترداد", RefundRequest),
    ("الفواتير", Invoice),
    ("الحسابات المالية", Account),
    ("المزايدات", Bid),
    ("المفضّلة", Favourite),
    ("صور المركبات", VehicleImage),
    ("المركبات", Vehicle),
    ("المزادات", Auction),
    ("مستندات العملاء", CustomerDocument),
    ("العناوين الوطنية", NationalAddress),
    ("الشركات", Company),
    ("جسرُ معرّفات v1", LegacyRef),
]

customers = User.objects.filter(is_staff=False)

print("قبل المحو:")
for label, model in ORDER:
    print(f"  {model.objects.count():>9,}  {label}")
print(f"  {customers.count():>9,}  العملاء (غير الموظّفين)")
print(f"  {User.objects.filter(is_staff=True).count():>9,}  الموظّفون — **لا يُمحَون**")

if os.environ.get("WIPE") != "yes":
    print("\nوضعُ العدّ. للمحو: WIPE=yes")
else:
    with transaction.atomic():
        for label, model in ORDER:
            removed, _ = model.objects.all().delete()
            print(f"مُحي {removed:>9,}  {label}")
        removed, _ = customers.delete()
        print(f"مُحي {removed:>9,}  العملاء")
    print("\nتمّ. القاعدةُ جاهزةٌ للترحيل.")
