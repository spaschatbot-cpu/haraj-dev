/// جلسة مستخدم مسجَّل الدخول.
///
/// الرموز نفسها لا تسكن هنا: `AuthSession` تصف **حالة** الجلسة للعرض والتوجيه،
/// بينما الرمزان يعيشان في التخزين الآمن وحده ولا يعبران إلى طبقة العرض
/// (انظر `data/local/secure/secure_token_store.dart`).
library;

/// غرض الرمز المُرسَل — نفس قيم الخادم (`SendCodePurposeEnum`).
///
/// موجود في النطاق حتى لا تستورد الشاشة نوعاً مولَّداً من المخطط: لو تغيّر
/// اسم النوع عند إعادة التوليد، تتغيّر ملفات `data` وحدها.
enum CodePurpose {
  /// دخول أو تسجيل بأول رمز.
  login,

  /// تغيير رقم الجوال — رمز للرقم الحالي ورمز للجديد.
  changePhone,

  /// استعادة الحساب.
  recover,
}

/// جلسة قائمة بعد تحقّق ناجح.
final class AuthSession {
  const AuthSession({
    required this.accessExpiresAt,
    required this.isNewAccount,
    required this.displayName,
  });

  /// بتوقيت UTC.
  final DateTime accessExpiresAt;

  /// أنشأ الخادم الحساب بهذا الدخول — أول دخول لهذا الرقم.
  final bool isNewAccount;

  /// الاسم الذي يعرض به الخادم صاحب الحساب، أو فارغ إن لم يذكره.
  ///
  /// من الخادم لا من `full_name` الذي كتبه المستخدم: حساب الشركة يُعرض باسم
  /// الشركة، والقاعدة التي تختار الاسم واحدة وتعيش هناك.
  final String displayName;
}

/// رمز أُرسل فعلاً: متى ينتهي، ومتى يُسمح بطلب غيره.
final class CodeDelivery {
  const CodeDelivery({
    required this.expiresAt,
    required this.resendAfterSeconds,
  });

  /// بتوقيت UTC.
  final DateTime expiresAt;

  /// ثوانٍ قبل أن يُقبل طلب رمز جديد — الخادم يقولها، والشاشة تعدّ بها.
  final int resendAfterSeconds;
}

/// رمزا تغيير الجوال: أُرسل إلى الرقم الحالي وإلى الجديد.
final class PhoneChangeCodes {
  const PhoneChangeCodes({
    required this.sentToCurrent,
    required this.sentToNew,
    required this.delivery,
  });

  /// علمان لا علم واحد: الشاشة تطلب من المستخدم أن ينظر في جهازين، وأحدهما
  /// قد يكون في الدرج.
  final bool sentToCurrent;
  final bool sentToNew;

  final CodeDelivery delivery;
}
