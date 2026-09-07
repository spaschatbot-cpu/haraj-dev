import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:haraj_mobile/data/api/generated/models/authenticated_user.dart';
import 'package:haraj_mobile/data/api/generated/models/confirm_phone_change.dart';
import 'package:haraj_mobile/data/api/generated/models/send_code.dart';
import 'package:haraj_mobile/data/api/generated/models/send_code_purpose_enum.dart';
import 'package:haraj_mobile/data/api/generated/models/send_code_response.dart';
import 'package:haraj_mobile/data/api/generated/models/start_phone_change_response.dart';
import 'package:haraj_mobile/data/api/generated/models/token_pair.dart';
import 'package:haraj_mobile/data/api/generated/models/verify_code.dart';
import 'package:haraj_mobile/data/auth/auth_repository_impl.dart';
import 'package:haraj_mobile/data/local/secure/secure_token_store.dart';
import 'package:haraj_mobile/domain/auth/entities/auth_session.dart';

import '../support/fake_auth_api.dart';
import '../support/memory_response_cache.dart';

/// T706 — الدخول والتسجيل، والرموز لا تعيش إلا في التخزين الآمن.
void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  late FakeAuthApi api;
  late SecureTokenStore tokens;
  late MemoryResponseCache cache;
  late AuthRepositoryImpl repository;

  setUp(() {
    FlutterSecureStorage.setMockInitialValues(<String, String>{});
    api = FakeAuthApi();
    tokens = SecureTokenStore.platformDefault();
    cache = MemoryResponseCache();
    repository = AuthRepositoryImpl(api: api, tokens: tokens, cache: cache);
  });

  TokenPair pairFor({bool isNew = false}) => TokenPair(
    access: 'access-token',
    refresh: 'refresh-token',
    expiresIn: 900,
    expiresAt: DateTime.utc(2026, 9, 1, 12),
    user: AuthenticatedUser(
      id: 7,
      phone: '966500000001',
      displayName: 'شركة الاختبار',
      accountType: 'company',
      isNew: isNew,
    ),
  );

  test('طلب الرمز يرسل الغرض الذي طلبته الشاشة', () async {
    api.sendResponse = SendCodeResponse(
      sent: true,
      expiresAt: DateTime.utc(2026, 9, 1, 10, 5),
      resendAfter: 60,
    );

    final delivery = await repository.sendCode(
      phone: '966500000001',
      purpose: CodePurpose.changePhone,
    );

    expect(
      (api.bodies.single as SendCode).purpose,
      SendCodePurposeEnum.changePhone,
    );
    expect(delivery.resendAfterSeconds, 60);
    // الوقت UTC في النقل والتخزين؛ التحويل عند حافة العرض وحدها (المادة ٣-١).
    expect(delivery.expiresAt.isUtc, isTrue);
  });

  test('التحقق الناجح يحفظ الرمزين في التخزين الآمن', () async {
    api.tokenPair = pairFor(isNew: true);

    final session = await repository.verifyCode(
      phone: '966500000001',
      code: '123456',
      fullName: 'عميل جديد',
    );

    expect(session.isNewAccount, isTrue);
    // الاسم المعروض من الخادم لا من الحقل الذي كتبه المستخدم: حساب الشركة
    // يُعرض باسم الشركة، والقاعدة التي تختار الاسم تعيش هناك.
    expect(session.displayName, 'شركة الاختبار');
    expect(await tokens.readAccessToken(), 'access-token');
    expect(await tokens.readRefreshToken(), 'refresh-token');
  });

  test('الاسم يُرسَل مع التحقق حين يطلبه الخادم لرقم بلا حساب', () async {
    api.tokenPair = pairFor();

    await repository.verifyCode(
      phone: '966500000001',
      code: '123456',
      fullName: 'عميل جديد',
    );

    expect((api.bodies.single as VerifyCode).fullName, 'عميل جديد');
  });

  test('بدء تغيير الجوال يرجع علمَي الإرسال منفصلين', () async {
    api.startResponse = StartPhoneChangeResponse(
      sentToCurrent: true,
      sentToNew: true,
      expiresAt: DateTime.utc(2026, 9, 1, 10, 5),
      resendAfter: 60,
    );

    final sent = await repository.startPhoneChange(newPhone: '966500000002');

    expect(sent.sentToCurrent, isTrue);
    expect(sent.sentToNew, isTrue);
  });

  test('تأكيد تغيير الجوال يرسل الرمزين معاً', () async {
    api.confirmResponse = const AuthenticatedUser(
      id: 7,
      phone: '966500000002',
      displayName: 'عميل',
      accountType: 'individual',
      isNew: false,
    );
    await tokens.save(access: 'access-token', refresh: 'refresh-token');

    await repository.confirmPhoneChange(
      newPhone: '966500000002',
      currentCode: '111111',
      newCode: '222222',
    );

    final body = api.bodies.single as ConfirmPhoneChange;
    expect(body.currentCode, '111111');
    expect(body.newCode, '222222');
  });

  test('نجاح تغيير الجوال ينهي الجلسة المحلية بلا 401 ينتظر', () async {
    // الخادم يُلغي كل الجلسات عند النجاح — هذه منها. رموز باقية بعد ذلك تعني
    // تطبيقاً يظنّ نفسه داخل الحساب حتى أول طلب يفشل.
    api.confirmResponse = const AuthenticatedUser(
      id: 7,
      phone: '966500000002',
      displayName: 'عميل',
      accountType: 'individual',
      isNew: false,
    );
    await tokens.save(access: 'access-token', refresh: 'refresh-token');

    await repository.confirmPhoneChange(
      newPhone: '966500000002',
      currentCode: '111111',
      newCode: '222222',
    );

    expect(await tokens.hasSession(), isFalse);
    expect(cache.clearCount, 1);
  });

  test('الخروج يمحو الرموز ويفرّغ الكاش', () async {
    await tokens.save(access: 'access-token', refresh: 'refresh-token');

    await repository.signOut();

    expect(await tokens.readAccessToken(), isNull);
    expect(cache.clearCount, 1);
  });
}
