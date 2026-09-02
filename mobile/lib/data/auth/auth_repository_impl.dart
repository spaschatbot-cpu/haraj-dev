import '../../domain/auth/entities/auth_session.dart';
import '../../domain/auth/repositories/auth_repository.dart';
import '../api/api_call.dart';
import '../api/generated/clients/auth_api.dart';
import '../api/generated/models/otp_request.dart';
import '../api/generated/models/otp_verification.dart';
import '../local/cache/response_cache.dart';
import '../local/secure/secure_token_store.dart';

/// تنفيذ المصادقة فوق العميل المولَّد.
final class AuthRepositoryImpl implements AuthRepository {
  const AuthRepositoryImpl({
    required AuthApi api,
    required SecureTokenStore tokens,
    required ResponseCache cache,
  }) : _api = api,
       _tokens = tokens,
       _cache = cache;

  final AuthApi _api;
  final SecureTokenStore _tokens;
  final ResponseCache _cache;

  @override
  Future<OtpChallenge> requestOtp({required String phone}) async {
    final challenge = await callApi(
      () => _api.authOtpRequest(body: OtpRequest(phone: phone)),
    );
    return OtpChallenge(
      expiresAt: challenge.expiresAt.toUtc(),
      resendAfterSeconds: challenge.resendAfterSeconds,
    );
  }

  @override
  Future<AuthSession> verifyOtp({
    required String phone,
    required String code,
  }) async {
    final tokens = await callApi(
      () => _api.authOtpVerify(
        body: OtpVerification(phone: phone, code: code),
      ),
    );
    await _tokens.save(access: tokens.access, refresh: tokens.refresh);
    return AuthSession(
      accessExpiresAt: tokens.accessExpiresAt.toUtc(),
      isNewUser: tokens.isNewUser,
    );
  }

  @override
  Future<bool> hasStoredSession() => _tokens.hasSession();

  @override
  Future<void> signOut() async {
    await _tokens.clear();
    // الكاش يُمحى مع الخروج: بيانات عميل لا تظهر لمن يدخل بعده على نفس الجهاز.
    await _cache.clear();
  }
}
