import 'auction_phase.dart';
import 'vehicle_query.dart';

/// عدّاد كل تبويب — **الثلاثة من الخادم ومن لحظةٍ واحدة**.
///
/// لا يُشتقّ أيٌّ منها من طول القائمة المعروضة: القائمة صفحةٌ واحدة من نتيجة،
/// وطولها يقول «كم وصلني» لا «كم هناك». وفي v1 كانت الأرقام الثلاثة تُطلب في
/// ستّة طلبات منفصلة، فكان كل رقم من لحظة، ويقع التبويب على «٣» ثم يُفتح فيه
/// صفرٌ لأن المزاد أُقفل بين الطلبين.
final class PhaseCounts {
  const PhaseCounts({
    required this.upcoming,
    required this.active,
    required this.ended,
  });

  final int upcoming;
  final int active;
  final int ended;

  /// عدد تبويبٍ بعينه. `unknown` صفرٌ لأنه ليس تبويباً يُعرض أصلاً.
  int of(AuctionPhase phase) => switch (phase) {
    AuctionPhase.upcoming => upcoming,
    AuctionPhase.active => active,
    AuctionPhase.ended => ended,
    AuctionPhase.unknown => 0,
  };
}

/// ما يرجع من طلبٍ **واحد**: صفحة المركبات وعدّادات التبويبات الثلاثة معها.
///
/// اجتماعهما في نوعٍ واحد ليس تجميلاً: التبويبات الثلاثة تُرسم في كل حال، فهي
/// تحتاج الأرقام الثلاثة في كل حال؛ ونوعان يصلان من طلبين يجعلان الأرقام من
/// لحظتين، فلا يساوي مجموع التبويبات شيئاً.
final class VehicleFeed {
  const VehicleFeed({required this.page, required this.counts});

  /// نفس `VehiclePage` التي تعرضها قائمة مزادٍ بعينه — لا نسخة ثانية منها.
  final VehiclePage page;

  final PhaseCounts counts;
}
