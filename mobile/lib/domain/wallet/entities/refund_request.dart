import '../../common/money.dart';

/// طلبُ استردادٍ قدّمه العميل، كما ردّ به الخادم.
///
/// **الحالةُ نصُّها من الخادم** (`stateLabel`) لا خريطةَ أسماءٍ هنا: حالةٌ
/// جديدة في الدفتر تصل باسمها العربيّ فتُعرض، ولا تسقط الشاشةُ ولا تُعرض
/// بمفتاحٍ إنجليزيّ لأن التطبيق لا يعرفها (المادة ٣-٥).
final class RefundRequest {
  const RefundRequest({
    required this.id,
    required this.reference,
    required this.money,
    required this.stateLabel,
    required this.createdAt,
  });

  final String id;

  /// المرجعُ الذي يذكره العميل لخدمة العملاء.
  final String reference;

  final Money money;

  /// اسمُ الحالة بالعربية من الخادم.
  final String stateLabel;

  final DateTime createdAt;
}
