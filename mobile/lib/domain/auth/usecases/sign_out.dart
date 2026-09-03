import '../../notifications/usecases/forget_this_device.dart';
import '../repositories/auth_repository.dart';

/// الخروج كاملاً: الجهاز يتوقف عن استقبال إشعارات هذا الحساب، ثم تُمحى الجلسة.
///
/// **الترتيب هو التاسك كله.** `AuthRepository.signOut` يمحو الرمزين من التخزين
/// الآمن؛ وبعد محوهما لا شيء يثبت للخادم من صاحب الجهاز، فيردّ 401 على إلغاء
/// التسجيل ويبقى الجهاز مربوطاً بمن خرج — ومن يدخل بعده على نفس الجوال يرى
/// إشعارات مزايدات ليست له. لذلك: أَبلغ الخادم وأنت ما زلت تحمل الرمز، ثم امحُه.
///
/// يحرس الترتيبَ اختبارٌ يفشل بدونه: `test/domain/sign_out_test.dart`.
final class SignOut {
  const SignOut({
    required AuthRepository auth,
    required ForgetThisDevice forgetDevice,
  }) : _auth = auth,
       _forgetDevice = forgetDevice;

  final AuthRepository _auth;
  final ForgetThisDevice _forgetDevice;

  Future<ForgetDeviceOutcome> call() async {
    final outcome = await _forgetDevice();
    await _auth.signOut();
    return outcome;
  }
}
