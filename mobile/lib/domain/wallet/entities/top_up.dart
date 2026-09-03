import '../../common/money.dart';

/// حالة نيّة الشحن **كما يعرفها الخادم**.
///
/// `unknown` مقصودة (المادة ٢-٣): حالة جديدة من الخادم تُعرض بوصفها العربي ولا
/// تُسقط الشاشة، ولا تُترجَم هنا إلى حالة نعرفها فتُقرأ خطأً.
enum TopUpStatus { pending, succeeded, cancelled, failed, unknown }

/// نيّة شحن بالبطاقة: صفٌّ كتبه الخادم قبل أن يصل العميل إلى البوابة.
///
/// **المرجع ليس ادّعاءً.** هو اسم هذا الصفّ، وهو كل ما يحتاجه التطبيق ليسأل
/// الخادم «ماذا حدث؟». ما يعود من البوابة في الرابط لا يُقرأ ولا يُصدَّق —
/// في v1 كان تغيير معامل في رابط العودة كافياً ليعتقد التطبيق أن الدفع تمّ.
final class TopUp {
  const TopUp({
    required this.reference,
    required this.money,
    required this.checkoutUrl,
    required this.status,
    required this.statusLabel,
  });

  final String reference;

  /// المبلغ الذي حدّده الخادم — التطبيق لا يرسل مبلغاً ولا يقترحه.
  final Money money;

  /// عنوان البوابة. يُفتح، ولا يُقرأ ما يعود منه.
  final String checkoutUrl;

  final TopUpStatus status;

  /// وصف الحالة بالعربية من الخادم — يُعرض حرفياً.
  final String statusLabel;

  /// ما زال معلَّقاً: البوابة لم تؤكّد للخادم بعد.
  bool get isPending => status == TopUpStatus.pending;

  /// نجح **بشهادة الخادم**. لا يُشتق من عودة العميل من البوابة.
  bool get hasSucceeded => status == TopUpStatus.succeeded;
}

/// نتيجة تسليم العميل إلى البوابة.
///
/// `gatewayOpened` منفصل عن النيّة عمداً: النيّة تُكتب في الخادم حتى لو تعذّر
/// فتح صفحة الدفع، ومحوها من الشاشة عندها يترك العميل بلا مرجع يسأل به.
final class TopUpHandoff {
  const TopUpHandoff({required this.intent, required this.gatewayOpened});

  final TopUp intent;
  final bool gatewayOpened;
}
