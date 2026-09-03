import '../entities/auth_session.dart';

/// عقد المصادقة كما تراه طبقة النطاق — بلا dio وبلا أي أثر للنقل.
///
/// كل دالة ترجع كياناً أو ترمي `Failure` مسمّى. لا أعلام نجاح/فشل ولا `null`
/// تعني خطأ (ميثاق الكود النظيف، بند 5 من خطة الفريق §5).
abstract interface class AuthRepository {
  /// يطلب إرسال رمز تحقق إلى جوال، لغرض بعينه.
  Future<CodeDelivery> sendCode({
    required String phone,
    CodePurpose purpose = CodePurpose.login,
  });

  /// يتحقق من الرمز، ويخزّن الرمزين في التخزين الآمن، ويرجع وصف الجلسة.
  ///
  /// [fullName] يلزم لرقم لا حساب له. الخادم يرفض بلا اسم **قبل** أن يستهلك
  /// الرمز (`registration_needs_name`)، فالرمز الذي بيد المستخدم يبقى صالحاً
  /// ولا يكلّفه الخطأ رسالة جديدة.
  Future<AuthSession> verifyCode({
    required String phone,
    required String code,
    String fullName,
  });

  /// هل توجد جلسة مخزَّنة أصلاً — يُسأل عند الإقلاع لتقرير الوجهة.
  Future<bool> hasStoredSession();

  /// يمحو الرمزين من التخزين الآمن ويفرّغ الكاش.
  Future<void> signOut();

  /// يبدأ تغيير رقم الجوال: رمز للرقم الحالي ورمز للجديد.
  ///
  /// الرقم الحالي لا يُرسَل — الخادم يقرؤه من رمز الوصول. لو قبله من الجسم
  /// لصار المسار طريقاً لنقل حساب غيرك (T604).
  Future<PhoneChangeCodes> startPhoneChange({required String newPhone});

  /// يؤكّد تغيير الرقم بالرمزين معاً.
  ///
  /// النجاح يُلغي **كل** الجلسات بما فيها هذه، فينتهي الاستدعاء بلا رموز
  /// مخزَّنة: من نجح يعود إلى شاشة الدخول بالرقم الجديد.
  Future<void> confirmPhoneChange({
    required String newPhone,
    required String currentCode,
    required String newCode,
  });
}
