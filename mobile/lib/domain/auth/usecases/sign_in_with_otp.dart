import '../entities/auth_session.dart';
import '../repositories/auth_repository.dart';

/// دخول برقم الجوال ورمز التحقق.
///
/// الخطوتان في usecase واحدة لأنهما قرار واحد في نظر المستخدم، ولأن فصلهما
/// يغري بمسار ثانٍ لإرسال الرمز — و«مسار OTP بلا حدّ» كان بوابة رسائل مجانية
/// في v1 (الفيز 007، T602). مسار الإرسال هنا واحد لا غير.
final class SignInWithOtp {
  const SignInWithOtp(this._repository);

  final AuthRepository _repository;

  Future<OtpChallenge> requestCode({required String phone}) =>
      _repository.requestOtp(phone: phone);

  Future<AuthSession> submitCode({
    required String phone,
    required String code,
  }) => _repository.verifyOtp(phone: phone, code: code);
}
