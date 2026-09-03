import '../../domain/auth/entities/auth_session.dart';
import '../../domain/auth/repositories/auth_repository.dart';
import '../api/api_call.dart';
import '../api/generated/clients/auth_api.dart';
import '../api/generated/models/confirm_phone_change.dart';
import '../api/generated/models/send_code.dart';
import '../api/generated/models/send_code_purpose_enum.dart';
import '../api/generated/models/start_phone_change.dart';
import '../api/generated/models/verify_code.dart';
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
  Future<CodeDelivery> sendCode({
    required String phone,
    CodePurpose purpose = CodePurpose.login,
  }) async {
    final sent = await callApi(
      () => _api.v1AuthCodeCreate(
        body: SendCode(phone: phone, purpose: _purposeOf(purpose)),
      ),
    );
    return CodeDelivery(
      expiresAt: sent.expiresAt.toUtc(),
      resendAfterSeconds: sent.resendAfter,
    );
  }

  @override
  Future<AuthSession> verifyCode({
    required String phone,
    required String code,
    String fullName = '',
  }) async {
    final pair = await callApi(
      () => _api.v1AuthVerifyCreate(
        body: VerifyCode(phone: phone, code: code, fullName: fullName),
      ),
    );
    await _tokens.save(access: pair.access, refresh: pair.refresh);
    return AuthSession(
      accessExpiresAt: pair.expiresAt.toUtc(),
      isNewAccount: pair.user?.isNew ?? false,
      displayName: pair.user?.displayName ?? '',
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

  @override
  Future<PhoneChangeCodes> startPhoneChange({required String newPhone}) async {
    final sent = await callApi(
      () => _api.v1AuthPhoneChangeCreate(
        body: StartPhoneChange(newPhone: newPhone),
      ),
    );
    return PhoneChangeCodes(
      sentToCurrent: sent.sentToCurrent,
      sentToNew: sent.sentToNew,
      delivery: CodeDelivery(
        expiresAt: sent.expiresAt.toUtc(),
        resendAfterSeconds: sent.resendAfter,
      ),
    );
  }

  @override
  Future<void> confirmPhoneChange({
    required String newPhone,
    required String currentCode,
    required String newCode,
  }) async {
    await callApi(
      () => _api.v1AuthPhoneChangeConfirmCreate(
        body: ConfirmPhoneChange(
          newPhone: newPhone,
          currentCode: currentCode,
          newCode: newCode,
        ),
      ),
    );

    // الخادم ألغى كل الجلسات — هذه منها. الرموز المحفوظة صارت ورقاً، وإبقاؤها
    // يعني شاشةً تظنّ نفسها داخل الحساب حتى أول 401.
    await signOut();
  }

  static SendCodePurposeEnum _purposeOf(CodePurpose purpose) =>
      switch (purpose) {
        CodePurpose.login => SendCodePurposeEnum.login,
        CodePurpose.changePhone => SendCodePurposeEnum.changePhone,
        CodePurpose.recover => SendCodePurposeEnum.recover,
      };
}
