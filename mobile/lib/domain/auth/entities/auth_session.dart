/// جلسة مستخدم مسجَّل الدخول.
///
/// الرموز نفسها لا تسكن هنا: `AuthSession` تصف **حالة** الجلسة للعرض والتوجيه،
/// بينما الرمزان يعيشان في التخزين الآمن وحده ولا يعبران إلى طبقة العرض
/// (انظر `data/local/secure/secure_token_store.dart`).
final class AuthSession {
  const AuthSession({required this.accessExpiresAt, required this.isNewUser});

  /// بتوقيت UTC.
  final DateTime accessExpiresAt;

  /// أول دخول لهذا الرقم — يقرّر مسار الإكمال بعد تثبيت الشاشات.
  final bool isNewUser;
}

/// تحدٍّ OTP قائم: متى ينتهي، ومتى يُسمح بإعادة الإرسال.
final class OtpChallenge {
  const OtpChallenge({
    required this.expiresAt,
    required this.resendAfterSeconds,
  });

  /// بتوقيت UTC.
  final DateTime expiresAt;
  final int resendAfterSeconds;
}
