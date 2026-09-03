import '../../common/money.dart';

/// سطر مواصفة: تسميته العربية وقيمته، وكلاهما من الخادم.
///
/// **لا خريطة أسماء في التطبيق.** لو ترجم التطبيق أسماء المواصفات لصار عندنا
/// تعريف ثانٍ لما يعنيه كل حقل، وأول مواصفة جديدة تظهر في الويب وتغيب هنا.
final class VehicleSpecification {
  const VehicleSpecification({required this.label, required this.value});

  final String label;
  final String value;
}

/// المركبة في صفحتها: صورها ومواصفاتها وسعرها وهل المزايدة عليها مفتوحة.
final class VehicleDetail {
  const VehicleDetail({
    required this.id,
    required this.lotNumber,
    required this.title,
    required this.imageUrls,
    required this.specifications,
    required this.reservePrice,
    required this.biddingOpen,
  });

  final String id;
  final String lotNumber;
  final String title;

  /// قد تكون كثيرة وقد تكون فارغة. الشاشة تحمّلها كسولاً وتعالج فشل كل صورة
  /// على حدة — صورة ساقطة ليست شاشة ساقطة.
  final List<String> imageUrls;

  final List<VehicleSpecification> specifications;

  /// نفس حقل الكرت. سعر واحد للمركبة في كل شاشة، وإلا اختلفت الأرقام أمام
  /// العميل كما اختلفت في v1 (المادة ٤-٥).
  final Money? reservePrice;

  /// **الخادم يقرّر** هل المزايدة مفتوحة. التطبيق لا يقارن وقتاً بوقت ليستنتج
  /// أن المزاد انتهى — ساعة الجهاز ليست ساعة الخادم، والأهلية نقطة قرار واحدة
  /// في `apps/bidding/eligibility.py`.
  final bool biddingOpen;
}
