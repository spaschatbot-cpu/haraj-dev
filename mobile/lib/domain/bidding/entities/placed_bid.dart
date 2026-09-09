import '../../common/money.dart';

/// حال المزايدة **كما يقولها الخادم** — وهو يقولها بعلمين لا بكلمة.
///
/// **ولا `leading` ولا `outbid` هنا، عمداً.** المزاد مغلق (قرار `ce013b9`):
/// لا أعلى مزايدة تُنشر ولا ترتيب. فالخادم لا يملك أن يقول «أنت المتصدّر» بلا
/// أن يكشف ما تعهّد بألّا يكشفه — ولذلك لا يقولها، وكانت في التطبيق لأنها
/// كانت في مخططٍ وهميّ لا يعرف هذه السياسة.
///
/// ما يقوله العقد علمان: `is_withdrawn` و`is_superseded`. وهذا التعداد
/// تسميتُهما، لا استنتاجٌ فوقهما.
enum BidState {
  /// قائمة: لم تُسحب ولم تعلُها مزايدةٌ أحدث من صاحبها نفسه.
  standing,

  /// علتها مزايدةٌ أحدث **من المزايد نفسه** — لا من غيره.
  superseded,

  /// سحبها صاحبها.
  withdrawn,

  /// تركيبةٌ لم يعرفها هذا الإصدار.
  ///
  /// المادتان ٢-٣ و٣-٥: الحال يُحفظ ولا تُسقط المزايدة التي تحمله.
  unknown,
}

/// مزايدةٌ وُضعت.
final class PlacedBid {
  const PlacedBid({
    required this.id,
    required this.vehicleId,
    required this.auctionId,
    required this.lotNumber,
    required this.vehicleTitle,
    required this.money,
    required this.state,
    required this.placedAtUtc,
  });

  final String id;
  final String vehicleId;
  final String auctionId;

  /// رقم اللوت — به يعرف العميل مركبته في القاعة، ولا يُشتقّ من ترتيب قائمة.
  final String lotNumber;

  final String vehicleTitle;
  final Money money;
  final BidState state;

  /// **ولا `stateLabel` هنا.** الخادم لا يرسل نصّاً لهذا الحال — يرسل العلمين
  /// وحدهما. والنصّ المعروض من ملفّ الترجمة في طبقة العرض، حيث تعيش كل نصوص
  /// الواجهة (المعيار H3). كان الحقل هنا لأن المخطط الوهميّ وعد بـ
  /// `status_label` ولم يفِ به عقدٌ حقيقيّ قط.
  final DateTime placedAtUtc;

  bool get isWithdrawn => state == BidState.withdrawn;
  bool get isSuperseded => state == BidState.superseded;
}
