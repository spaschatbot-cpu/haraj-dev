import '../../common/money.dart';
import 'auction_phase.dart';
import 'vehicle_state.dart';

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
    required this.reference,
    required this.adminFee,
    required this.adminFeeWithVat,
    required this.auctionId,
    required this.phase,
    required this.state,
    required this.auctionEndsAt,
  });

  final String id;
  final String lotNumber;
  final String title;

  /// مصغَّرة فقط — الحجم الكامل في صفحة المركبة (قاعدة التصميم 6 في الفيز 008).
  final String? thumbnailUrl;

  /// الرقم المرجعيّ على الكرت — `#10565` كما في v1.
  final String reference;

  /// الرسوم الإدارية، ومعها الرسوم + الضريبة (١٥٪) — وهما **كل ما يُعرض من
  /// مال على الكرت**.
  ///
  /// **ولا سعرَ وقوفٍ هنا ولا عددَ مزايدات**، وكانا موجودين. المزاد **مغلق**
  /// (قرارٌ في `ce013b9`): لا سعر افتتاحيّ يُنشر ولا أعلى مزايدة، فالخادم لا
  /// يرسل `reserve_price` ولا `bids_count` أصلاً. كان الكرت يعرضهما لأنه بُني
  /// على مخططٍ وهميّ أُضيف إليه `reserve_price` بيد — فكان يعد بما لا يصل، ثم
  /// يسقط على `null` عند أول استجابةٍ حقيقية.
  ///
  /// نصّاً كما وصل، لا `double`: المادة ٣-٢.
  final Money adminFee;
  final Money adminFeeWithVat;

  /// مزاد هذه المركبة.
  ///
  /// يُحمل على الكرت لأن الشبكة المسطّحة تجمع مركبات مزادات شتّى في قائمة
  /// واحدة، فلا يكفي أن يعرفه سياق الشاشة كما كان يكفي في قائمة مزادٍ بعينه.
  final String auctionId;

  /// طور مزادها **كما قاله الخادم** — لا كما يُستنتج من `auctionEndsAt`.
  final AuctionPhase phase;

  /// حالة المركبة نفسها — بها يُفعَّل زرّ المزايدة أو يُعطَّل.
  final VehicleState state;

  /// لحظة انتهاء مزادها، بتوقيت UTC.
  ///
  /// تُحمل على الكرت لأن العدّاد التنازلي على الكرت، وطلبها لكل كرت على حدة
  /// يعني طلباً لكل مركبة. والتحويل للعرض يبقى في `SaudiTime` وحدها
  /// (المادة ٣-١)، والعدّ نفسه فرقٌ بين لحظتين UTC لا حسابُ تقويم.
  final DateTime auctionEndsAt;
}
