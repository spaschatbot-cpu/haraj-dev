import '../../common/money.dart';

/// حالة تأمين المزايد في مزاد بعينه — **كما قرّرها الخادم**.
///
/// `unknown` مقصودة (المادة ٢-٣ و٣-٥): حالة لم نرها من قبل تُقرأ ولا تُسقط
/// الاستجابة التي تحملها. ولأن الوصف العربي يصل بجوارها، تبقى الحالة غير
/// المعروفة معروضة بنصّها الصحيح ولو لم يعرف التطبيق كيف يبرزها.
enum InsuranceState {
  /// لا تأمين مرتبط بهذا المزاد.
  none,

  /// محجوز لمزايدة جارية.
  held,

  /// مقفول على مستحقات — فاتورة فوز غير مسدَّدة.
  locked,

  /// فُكّ بعد نهاية المزاد.
  released,

  unknown,
}

/// مزاد دخله العميل، وحالة تأمينه فيه.
///
/// **لماذا كيان واحد لا تركيب في الشاشة:** «مزايداتي» و«المحفظة» يكفيان نظرياً
/// لبناء هذه القائمة بالمطابقة على معرّف المزاد — وتلك المطابقة قاعدةُ عمل،
/// ولو عاشت في الشاشة لصارت نسخة ثانية تفترق عن الخادم عند أول تعديل
/// (المادة ٤-٥). لذلك تُسأل نقطة واحدة وتُعرض إجابتها.
final class Participation {
  const Participation({
    required this.auctionId,
    required this.auctionTitle,
    required this.auctionStatusLabel,
    required this.endsAt,
    required this.bidsCount,
    required this.insuranceState,
    required this.insuranceStateLabel,
    this.insuranceMoney,
  });

  final String auctionId;
  final String auctionTitle;

  /// حالة المزاد بالعربية من الخادم — لا خريطة حالات هنا.
  final String auctionStatusLabel;

  /// بتوقيت UTC؛ التحويل للعرض عند حافة العرض وحدها (المادة ٣-١).
  final DateTime endsAt;

  /// عدد مزايدات العميل في هذا المزاد — يعدّها الخادم.
  final int bidsCount;

  final InsuranceState insuranceState;

  /// وصف عربي جاهز للعرض، من الخادم.
  final String insuranceStateLabel;

  /// المبلغ المحجوز أو المقفول لهذا المزاد. يغيب حين لا تأمين مرتبطاً به.
  final Money? insuranceMoney;
}
