import 'vehicle_summary.dart';

/// سطر مواصفة: تسميته العربية وقيمته.
///
/// **لا خريطة أسماء في التطبيق.** التسمية المعروضة للقيمة تأتي من الخادم
/// (`colour_label`، `condition_label`)، واسمُ الحقل نفسه من ملف الترجمة —
/// وهو نصُّ واجهةٍ لا معرفةٌ بالمجال. لو ترجم التطبيق **القيم** لصار عندنا
/// تعريف ثانٍ لما يعنيه كل حقل، وأول قيمة جديدة تظهر في الويب وتغيب هنا.
final class VehicleSpecification {
  const VehicleSpecification({required this.label, required this.value});

  final String label;
  final String value;
}

/// المركبة في صفحتها: كرتُها وصورُها.
///
/// **الكرت نفسه لا نسخةٌ منه.** معيار T609 أن حقول القائمة وحقول التفاصيل
/// واحدة، والخادم يفي به حرفياً: `/vehicles/` و`/vehicles/{id}/` يردّان
/// `VehicleCard` عينه. فحملُ الكرت هنا بدل إعادة سرد حقوله يجعل ذلك التطابق
/// **بنيةً** لا وعداً يُراجَع بالعين.
///
/// والصور وحدها من نداءٍ ثانٍ (`/vehicles/{id}/images/`): الكرت يحمل مصغَّرة
/// واحدة، وصفحةٌ فيها عشرون صورة لا تُحمَّل مع كل كرت في شبكة.
final class VehicleDetail {
  const VehicleDetail({
    required this.card,
    required this.imageUrls,
    required this.specifications,
  });

  final VehicleSummary card;

  /// قد تكون كثيرة وقد تكون فارغة. الشاشة تحمّلها كسولاً وتعالج فشل كل صورة
  /// على حدة — صورة ساقطة ليست شاشة ساقطة.
  final List<String> imageUrls;

  final List<VehicleSpecification> specifications;

  String get id => card.id;
  String get lotNumber => card.lotNumber;
  String get title => card.title;

  /// هل يُفعَّل زرّ المزايدة.
  ///
  /// **من حالة المركبة كما أرسلها الخادم**، وهي موجودة على الكرت لهذا الغرض
  /// بعينه — تعليق `apps/auctions/cards.py`: «الحالة تبقى رمزاً لا نصّاً: زرّ
  /// مزايدة يُفعَّل أو يُعطَّل بها، والعميل يحتاج القيمة ليقرّر».
  ///
  /// وهذا **عرضٌ لا حكم**: الأهلية الحقيقية تُقرَّر في
  /// `apps/bidding/eligibility.py` وحدها، وردُّ الخادم على محاولة مزايدةٍ هو
  /// الفصل. الزرّ المعطَّل يوفّر نداءً، ولا يمنح إذناً.
  bool get biddingOpen => card.state.isBiddable;
}
