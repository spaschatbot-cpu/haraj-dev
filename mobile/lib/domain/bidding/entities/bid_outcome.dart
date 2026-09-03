import 'placed_bid.dart';

/// جواب الخادم على محاولة مزايدة، حين يكون الجواب **سلوكاً** لا نصّاً.
///
/// لماذا نوع بدل رمي `Failure` وحده: أغلب الرفض رسالةٌ تُعرض كما جاءت وتنتهي
/// عندها القصة، فيكفيه `ApiFailure`. حالة واحدة تطلب من الشاشة أن تفعل شيئاً —
/// الخفض يحتاج تأكيداً صريحاً (F3) — ولو بقيت رمزاً داخل خطأ لاحتاجت كل شاشة
/// أن تقارن نصّ الرمز وتفكّ حمولته بيدها. تُترجَم هنا مرة واحدة في طبقة
/// البيانات، فتصل العرضَ نوعاً لا يُنسى فحصه.
sealed class BidOutcome {
  const BidOutcome();
}

/// سُجّلت المزايدة.
final class BidAccepted extends BidOutcome {
  const BidAccepted(this.bid);

  final PlacedBid bid;
}

/// أقل من المزايدة القائمة — مسموح، لكن ليس صدفةً.
///
/// المبلغان نصّان **كما أرسلهما الخادم في رفضه**، لا قراءة جديدة للمزايدة
/// القائمة: الرقم الذي يُطلب من العميل تأكيد النزول عنه يجب أن يكون الرقم الذي
/// كان الرفض عنه. قراءة طازجة بعد لحظة قد تعطي رقماً آخر، فيصير التأكيد موافقةً
/// على شيء لم يُسأل عنه.
///
/// وبلا عملة عمداً: حمولة الرفض لا تحمل عملة، والتطبيق لا يخترع واحدة.
final class BidNeedsLowerConfirmation extends BidOutcome {
  const BidNeedsLowerConfirmation({
    required this.standingAmount,
    required this.requestedAmount,
    required this.message,
  });

  /// المزايدة القائمة الآن.
  final String standingAmount;

  /// ما طلبه العميل، وهو أقل.
  final String requestedAmount;

  /// جملة الخادم العربية — تُعرض كما جاءت فوق المبلغين.
  final String message;
}
