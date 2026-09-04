import '../../common/money.dart';
import 'auction_phase.dart';

/// المركبة كما تظهر في **كرت** — وهذه هي كل حقول الكرت.
///
/// جمعُ الحقول في كيان واحد نصفُ قاعدة «كرت واحد»؛ نصفها الآخر مكوّن عرض واحد
/// (`presentation/catalog/widgets/vehicle_card.dart`) وفحصٌ نصّي يمنع رسم كرت
/// خارجه. في v1 كانت الصفحة الرئيسية وحدها فيها أربعة مسارات لرسم الكرت وثلاث
/// قوائم حقول، فأي حقل جديد يظهر في بعضها ويختفي في الباقي بصمت.
final class VehicleSummary {
  const VehicleSummary({
    required this.id,
    required this.lotNumber,
    required this.title,
    required this.thumbnailUrl,
    required this.reservePrice,
    required this.bidsCount,
    required this.auctionId,
    required this.phase,
    required this.auctionEndsAt,
  });

  final String id;
  final String lotNumber;
  final String title;

  /// مصغَّرة فقط — الحجم الكامل في صفحة المركبة (قاعدة التصميم 6 في الفيز 008).
  final String? thumbnailUrl;

  /// سعر وقوف المركبة، **الحقل الوحيد لسعرها** (دليل النظام §8-3).
  ///
  /// `null` يعني أن المالك لم يحدّد سعراً، وهو غير الصفر: يُعرض بنصّ يقول ذلك،
  /// لا برقم لم يختره أحد.
  final Money? reservePrice;

  /// عدد المزايدات لا مبلغها: المزاد مغلق، ومبلغ أعلى مزايدة ليس معلومة عامة.
  final int bidsCount;

  /// مزاد هذه المركبة.
  ///
  /// يُحمل على الكرت لأن الشبكة المسطّحة تجمع مركبات مزادات شتّى في قائمة
  /// واحدة، فلا يكفي أن يعرفه سياق الشاشة كما كان يكفي في قائمة مزادٍ بعينه.
  final String auctionId;

  /// طور مزادها **كما قاله الخادم** — لا كما يُستنتج من `auctionEndsAt`.
  final AuctionPhase phase;

  /// لحظة انتهاء مزادها، بتوقيت UTC.
  ///
  /// تُحمل على الكرت لأن العدّاد التنازلي على الكرت، وطلبها لكل كرت على حدة
  /// يعني طلباً لكل مركبة. والتحويل للعرض يبقى في `SaudiTime` وحدها
  /// (المادة ٣-١)، والعدّ نفسه فرقٌ بين لحظتين UTC لا حسابُ تقويم.
  final DateTime auctionEndsAt;
}
