import '../entities/auth_session.dart';

/// عقد المصادقة كما تراه طبقة النطاق — بلا dio وبلا أي أثر للنقل.
///
/// كل دالة ترجع كياناً أو ترمي `Failure` مسمّى. لا أعلام نجاح/فشل ولا `null`
/// تعني خطأ (ميثاق الكود النظيف، بند 5 من خطة الفريق §5).
abstract interface class AuthRepository {
  /// يطلب إرسال رمز تحقق إلى الجوال.
  Future<OtpChallenge> requestOtp({required String phone});

  /// يتحقق من الرمز، ويخزّن الرمزين في التخزين الآمن، ويرجع وصف الجلسة.
  Future<AuthSession> verifyOtp({required String phone, required String code});

  /// هل توجد جلسة مخزَّنة أصلاً — يُسأل عند الإقلاع لتقرير الوجهة.
  Future<bool> hasStoredSession();

  /// يمحو الرمزين من التخزين الآمن.
  Future<void> signOut();
}
