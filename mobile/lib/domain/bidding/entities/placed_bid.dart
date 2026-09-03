import '../../common/money.dart';

/// حالة المزايدة كما يعرّفها الخادم.
///
/// `unknown` مقصودة (المادة ٢-٣ و٣-٥): حالة جديدة في الخلفية تُقرأ ولا تُسقط
/// الاستجابة التي تحملها. ولأن الوصف العربي يأتي من الخادم في `stateLabel`،
/// تبقى الحالة التي لا يعرفها التطبيق **معروضة بوصفها الصحيح**.
enum BidState { placed, outbid, leading, withdrawn, won, lost, unknown }

/// مزايدة واحدة للعميل نفسه.
///
/// لا يوجد هنا «هل أنا الأعلى» ولا «كم يفصلني عن الأول»: المزاد مغلق ولا نقطة
/// تسرد مزايدات مركبة، فحقلٌ كهذا في التطبيق يكون قد اختُرع هنا.
final class PlacedBid {
  const PlacedBid({
    required this.id,
    required this.vehicleId,
    required this.money,
    required this.state,
    required this.stateLabel,
    required this.placedAtUtc,
    this.vehicleTitle,
  });

  final String id;
  final String vehicleId;

  /// عنوان المركبة من الخادم — قد يغيب، فلا تفترضه الشاشة.
  final String? vehicleTitle;

  final Money money;
  final BidState state;

  /// الوصف العربي للحالة من الخادم — لا خريطة حالات في التطبيق.
  final String stateLabel;

  /// بتوقيت UTC (المادة ٣-١)؛ التحويل للعرض عند حافة العرض وحدها.
  final DateTime placedAtUtc;

  /// المسحوبة تُعلَّم ولا تُحذف، فيبقى للعميل أثر ما فعل.
  bool get isWithdrawn => state == BidState.withdrawn;

  /// هل يعرض لها زرّ سحب؟
  ///
  /// **ليست قاعدة أهلية.** الخادم وحده يقرّر إن كان السحب ممكناً الآن، وردّه
  /// هو الجواب؛ هذه إخفاءُ زرٍّ لمزايدة سحبها العميل بنفسه لتوّه. أي شرط أوسع
  /// من «مسحوبة بالفعل» يكون قاعدةً ثانية تعيش في التطبيق.
  bool get offersWithdraw => !isWithdrawn;
}
