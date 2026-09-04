import 'package:flutter/material.dart';

import '../../../domain/catalog/entities/auction_phase.dart';
import '../../../domain/catalog/entities/vehicle_summary.dart';
import '../../../l10n/generated/app_localizations.dart';
import '../../common/money_text.dart';
import 'countdown_text.dart';
import 'remote_image.dart';

/// كرت المركبة — **مكوّن واحد، ولا رسم لكرت خارجه** (T708).
///
/// في v1 كانت الصفحة الرئيسية وحدها فيها أربعة مسارات لرسم هذا الكرت وثلاث
/// قوائم حقول، فأي حقل يُضاف للمنتج يظهر في بعضها ويختفي في الباقي **بصمت** —
/// ولم ينتبه أحد حتى سأل عميل لماذا يظهر الممشى في صفحة المزاد ولا يظهر في
/// نتائج البحث. الخلفية سدّت الثغرة نفسها في الفيز 005
/// (`ops/checks/one_vehicle_card.py`)، والويب في الفيز 011
/// (`ops/checks/web_one_vehicle_card.mjs`)، وهذا نظيرهما في التطبيق:
/// `test/architecture/one_vehicle_card_test.dart` يُسقط الاختبارات على أي رسمٍ
/// ثانٍ.
///
/// **السعر `reservePrice` ولا شيء غيره.** لا مبلغ أعلى مزايدة، ولا «قيمة
/// تقديرية»، ولا حساب في الشاشة: في v1 حُسب سعر المركبة في أربع شاشات بأربع
/// طرق فاختلفت الأرقام أمام العميل (المادة ٤-٥، ودليل النظام §8-3). ويُعرض
/// عبر `MoneyText` كما وصل نصّاً — بلا فواصل ولا تقريب.
///
/// **«انتهى» يقولها الخادم، والعدّاد يقول «كم بقي» فقط.** الطور يأتي جاهزاً في
/// `phase`، والكرت يطبعه كما وصل؛ ولا يقارن `auctionEndsAt` بساعة الجهاز
/// ليستنتجه. هذا بعينه ما فعله v1: عدّادٌ تنازلي على ساعة العميل كتب «انتهى»
/// على مزادٍ ما زال مفتوحاً لكل من ساعته متقدّمة دقيقتين، فأغلق باب المزايدة
/// أمامه وهو مفتوح.
class VehicleCard extends StatelessWidget {
  const VehicleCard({required this.vehicle, this.onTap, super.key});

  final VehicleSummary vehicle;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final theme = Theme.of(context);
    final price = vehicle.reservePrice;

    return Card(
      clipBehavior: Clip.antiAlias,
      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
      child: InkWell(
        onTap: onTap,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: <Widget>[
            AspectRatio(
              aspectRatio: 4 / 3,
              // مصغَّرة لا صورة كاملة (قاعدة التصميم 6)، ومفكوكة بعرضٍ يقارب
              // عرض الشاشة لا بعرضها الأصلي.
              child: RemoteImage(url: vehicle.thumbnailUrl, decodeWidth: 640),
            ),
            Padding(
              padding: const EdgeInsets.all(12),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  // سطران على الأكثر: عنوانٌ طويل في خليّة شبكة يدفع السعر
                  // خارج الكرت، فيُقصّ الرقم بدل أن يُقصّ الاسم.
                  Text(
                    vehicle.title,
                    style: theme.textTheme.titleMedium,
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                  ),
                  const SizedBox(height: 4),
                  Text(
                    l10n.vehicleLot(vehicle.lotNumber),
                    style: theme.textTheme.bodySmall,
                  ),
                  const SizedBox(height: 8),
                  // `Wrap` لا `Row`: على أضيق جوال يصير السعر وعدد المزايدات
                  // أعرض من السطر، و`Row` تقصّ ما لا يتّسع بلا أن يعرف أحد.
                  Wrap(
                    crossAxisAlignment: WrapCrossAlignment.center,
                    spacing: 8,
                    runSpacing: 4,
                    children: <Widget>[
                      Text(
                        l10n.vehicleReservePrice,
                        style: theme.textTheme.bodySmall,
                      ),
                      if (price == null)
                        // ليس «٠» ولا فراغاً: مركبةٌ لم يحدّد مالكها سعر
                        // وقوفها شيءٌ آخر غير مركبةٍ سعرها صفر، وطباعة رقمٍ
                        // للأولى رقمٌ لم يختره أحد.
                        Text(
                          l10n.vehicleReservePriceUnset,
                          style: theme.textTheme.bodyMedium,
                        )
                      else
                        MoneyText(price, style: theme.textTheme.titleMedium),
                      Text(
                        l10n.vehicleBidsCount(vehicle.bidsCount),
                        style: theme.textTheme.bodySmall,
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  // مزادٌ قاله الخادم منتهياً لا عدّاد له: العدّ إلى لحظةٍ مضت
                  // يعطي نصّاً عن ساعة الجهاز، والخبر عن المزاد أصدق منه.
                  // وطورٌ لا نعرفه يُعامَل معاملة القائم لا المنتهي — الجهل
                  // ليس نفياً (المادة ٢-٣).
                  if (vehicle.phase == AuctionPhase.ended)
                    Text(
                      l10n.vehicleAuctionEnded,
                      style: theme.textTheme.bodyMedium,
                    )
                  else
                    CountdownText(
                      at: vehicle.auctionEndsAt,
                      target: CountdownTarget.end,
                    ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
