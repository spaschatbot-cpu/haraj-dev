/// نموذج الأخطاء الموحّد للتطبيق (T705).
///
/// القاعدة الحاكمة: **ما يعرفه الخادم يقوله الخادم.** إذا ردّ الخادم بالشكل
/// الموحّد `{"error": {code, message}}` فالرسالة العربية التي فيه تُعرض كما
/// جاءت. التطبيق لا يملك نصاً بديلاً لحالة يعرفها الخادم — وإلا صار لنا نسخة
/// ثانية من القاعدة تفترق عن الأصل عند أول تعديل في الخلفية (المادة ٤-٥).
///
/// النصوص المحلية مسموحة في حالة واحدة فقط: أن الخادم **لم يتكلّم** أصلاً —
/// انقطاع شبكة، مهلة، ردّ غير مفهوم. هذه حالات لا يعرفها الخادم بحكم التعريف.
library;

/// خطأ يمكن رميه من طبقة البيانات وتلقّيه في العرض.
sealed class Failure implements Exception {
  const Failure();
}

/// خطأ ردّ به الخادم بالشكل الموحّد.
///
/// `message` عربية جاهزة للعرض — تُعرض حرفياً. `code` للتفريع البرمجي فقط
/// (مثل: خفض المزايدة يحتاج تأكيداً) ولا يُعرض لمستخدم أبداً.
final class ApiFailure extends Failure {
  const ApiFailure({
    required this.code,
    required this.message,
    this.statusCode,
    this.detail,
  });

  final String code;
  final String message;
  final int? statusCode;

  /// حمولة الرفض كما أرسلها الخادم في `error.detail`.
  ///
  /// **لا تُعرض نصّاً.** موجودة لأن رفضاً واحداً يطلب من الشاشة أن تقتبس منه
  /// أرقاماً سألها الخادم عنها (مبلغا تأكيد الخفض)، وقراءتها من جسم الردّ في
  /// كل شاشة تعني ناسخين للشكل الموحّد بدل واحد (المادة ٤-٥).
  final Map<String, Object?>? detail;

  /// ثوانٍ ينتظرها المستخدم قبل أن يعيد المحاولة، حين يقولها الخادم.
  ///
  /// نقطة القراءة الوحيدة لمفتاح `retry_after`: يرسله الخادم مع حدّ المعدّل
  /// (429) ومع «الرمز السابق ما زال حيّاً» (409)، والشاشتان تعدّان به تنازلياً.
  /// شاشة تقرأ المفتاح بنفسها هي نسخة ثانية من قراءة العقد.
  int? get retryAfterSeconds {
    final value = detail?['retry_after'];
    return value is int ? value : null;
  }

  @override
  String toString() => 'ApiFailure($code, http=$statusCode): $message';
}

/// سبب صمت الخادم — التصنيف الوحيد الذي يملك التطبيق نصاً له.
enum TransportProblem {
  /// لا اتصال بالشبكة.
  offline,

  /// انقطع الاتصال أو تجاوز المهلة قبل ردّ مفهوم.
  timeout,

  /// وصل ردّ لكن لم يطابق الشكل الموحّد — لا نخترع له رسالة، نصنّفه.
  malformedResponse,
}

/// الخادم لم يردّ ردّاً مفهوماً، فلا رسالة منه لتُعرض.
final class TransportFailure extends Failure {
  const TransportFailure(this.problem, {this.cause});

  final TransportProblem problem;
  final Object? cause;

  @override
  String toString() => 'TransportFailure($problem): $cause';
}

/// خطأ في التطبيق نفسه — يُسجَّل ويُعرض كخطأ غير متوقع.
///
/// وجوده صريحاً يمنع الفرع الصامت: لا مسار في معالجة الأخطاء ينتهي بـ`return`
/// بلا تصنيف (المادة ٢-٢ بروحها).
final class UnexpectedFailure extends Failure {
  const UnexpectedFailure(this.cause, {this.stackTrace});

  final Object cause;
  final StackTrace? stackTrace;

  @override
  String toString() => 'UnexpectedFailure: $cause';
}
