import 'dart:io';

import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:haraj_mobile/data/api/generated/models/company_profile_read.dart';
import 'package:haraj_mobile/data/api/generated/models/locked_field.dart'
    as api;
import 'package:haraj_mobile/data/api/generated/models/patched_profile_update.dart';
import 'package:haraj_mobile/data/api/generated/models/profile.dart' as api;
import 'package:haraj_mobile/data/profile/profile_repository_impl.dart';
import 'package:haraj_mobile/domain/common/failure.dart';
import 'package:haraj_mobile/domain/common/snapshot.dart';
import 'package:haraj_mobile/domain/profile/entities/customer_profile.dart';

import '../support/fake_profile_api.dart';
import '../support/memory_response_cache.dart';

/// T715 — الملف الشخصي: ما يُقفل ولماذا، والعمل بلا اتصال (H5).
void main() {
  final fetchedAt = DateTime.utc(2026, 9, 1, 10);

  api.Profile serverProfile({
    bool verified = true,
    List<api.LockedField> locked = const <api.LockedField>[],
  }) => api.Profile(
    id: 7,
    phone: '966500000001',
    displayName: 'عميل',
    fullName: 'عميل الاختبار',
    email: 'a@b.com',
    accountType: 'individual',
    nationalId: verified ? '1000000008' : '',
    nationalIdVerified: verified,
    phoneVerifiedAt: DateTime.utc(2026, 8, 1),
    hasCompanyProfile: false,
    companyProfileComplete: false,
    lockedFields: locked,
  );

  ProfileRepositoryImpl build(FakeProfileApi api, MemoryResponseCache cache) =>
      ProfileRepositoryImpl(api: api, cache: cache, clock: () => fetchedAt);

  DioException transportFailure() => DioException(
    requestOptions: RequestOptions(path: '/api/v1/profile/'),
    type: DioExceptionType.connectionError,
    error: const SocketException('no route to host'),
  );

  DioException serverRefusal({
    required int status,
    required String code,
    required String message,
  }) => DioException(
    requestOptions: RequestOptions(path: '/api/v1/profile/'),
    type: DioExceptionType.badResponse,
    response: Response<Object?>(
      requestOptions: RequestOptions(path: '/api/v1/profile/'),
      statusCode: status,
      data: <String, Object?>{
        'error': <String, Object?>{
          'code': code,
          'message': message,
          'detail': <String, Object?>{},
        },
      },
    ),
  );

  test('الحقول المقفولة تصل بسببها كما كتبه الخادم', () async {
    final profileApi = FakeProfileApi(
      profile: serverProfile(
        locked: const <api.LockedField>[
          api.LockedField(
            field: 'phone',
            reason: 'رقم الجوال يتغيّر بتأكيد رمزين.',
          ),
          api.LockedField(
            field: 'national_id',
            reason: 'رقم الهوية مثبَّت ولا يمكن تغييره.',
          ),
        ],
      ),
    );

    final snapshot = await build(profileApi, MemoryResponseCache()).load();

    // السبب يُنقل حرفياً: التطبيق لا يملك صياغة ثانية لقاعدة يملكها الخادم.
    expect(
      snapshot.value.lockOn(ProfileFields.nationalId)?.reason,
      'رقم الهوية مثبَّت ولا يمكن تغييره.',
    );
    expect(snapshot.value.lockOn(ProfileFields.phone), isNotNull);
  });

  test('حقل غير مذكور في المقفولة ليس مقفولاً', () async {
    final profileApi = FakeProfileApi(
      profile: serverProfile(
        verified: false,
        locked: const <api.LockedField>[
          api.LockedField(field: 'phone', reason: 'يتغيّر عبر مسار خاص.'),
        ],
      ),
    );

    final snapshot = await build(profileApi, MemoryResponseCache()).load();

    // هوية غير صحيحة يصحّحها صاحبها (T606) — والشاشة تعرف ذلك من غياب القفل
    // لا من إعادة تنفيذ قاعدة التحقّق.
    expect(snapshot.value.lockOn(ProfileFields.nationalId), isNull);
  });

  test('انقطاع الشبكة بعد نجاح سابق يعرض المحفوظ بطابعه', () async {
    final cache = MemoryResponseCache();
    final profileApi = FakeProfileApi(profile: serverProfile());
    await build(profileApi, cache).load();

    profileApi.failure = transportFailure();
    final snapshot = await build(profileApi, cache).load();

    expect(snapshot.origin, DataOrigin.cache);
    expect(snapshot.fetchedAt, fetchedAt);
    expect(snapshot.value.fullName, 'عميل الاختبار');
  });

  test('انقطاع الشبكة بلا كاش يرمي العطب ولا يرجع ملفاً فارغاً', () async {
    final profileApi = FakeProfileApi()..failure = transportFailure();

    expect(
      () => build(profileApi, MemoryResponseCache()).load(),
      throwsA(isA<TransportFailure>()),
    );
  });

  test(
    'التعديل يحدّث النسخة المحفوظة فلا يعود الاسم القديم بلا شبكة',
    () async {
      final cache = MemoryResponseCache();
      final profileApi = FakeProfileApi(profile: serverProfile());
      final repository = build(profileApi, cache);
      await repository.load();

      profileApi.profile = api.Profile(
        id: 7,
        phone: '966500000001',
        displayName: 'عميل',
        fullName: 'الاسم الجديد',
        email: 'a@b.com',
        accountType: 'individual',
        nationalId: '1000000008',
        nationalIdVerified: true,
        phoneVerifiedAt: DateTime.utc(2026, 8, 1),
        hasCompanyProfile: false,
        companyProfileComplete: false,
        lockedFields: const <api.LockedField>[],
      );
      await repository.update(fullName: 'الاسم الجديد');

      profileApi.failure = transportFailure();
      final offline = await build(profileApi, cache).load();
      expect(offline.value.fullName, 'الاسم الجديد');
    },
  );

  test('التعديل يرسل الحقول المتغيّرة وحدها', () async {
    final profileApi = FakeProfileApi(profile: serverProfile());

    await build(profileApi, MemoryResponseCache()).update(fullName: 'اسم');

    final body = profileApi.bodies.single as PatchedProfileUpdate;
    expect(body.fullName, 'اسم');
    expect(body.email, isNull);
  });

  test('رفض الخادم يمرّ برسالته ولا يُخفى خلف كاش', () async {
    final cache = MemoryResponseCache();
    final profileApi = FakeProfileApi(profile: serverProfile());
    await build(profileApi, cache).load();

    profileApi.failure = serverRefusal(
      status: 409,
      code: 'national_id_already_verified',
      message: 'رقم الهوية مثبَّت ولا يمكن تغييره.',
    );

    await expectLater(
      build(profileApi, cache).setNationalId('1000000008'),
      throwsA(
        isA<ApiFailure>()
            .having((f) => f.code, 'code', 'national_id_already_verified')
            .having((f) => f.message, 'message', contains('مثبَّت')),
      ),
    );
  });

  test('لا شركة على الحساب جواب لا عطب', () async {
    final profileApi = FakeProfileApi()
      ..failure = serverRefusal(
        status: 404,
        code: 'not_found',
        message: 'غير موجود',
      );

    // 404 هنا تعني «لا شركة»، والشاشة تعرض نموذج إنشاء لا رسالة خطأ.
    expect(
      await build(profileApi, MemoryResponseCache()).loadCompany(),
      isNull,
    );
  });

  test('اكتمال ملف الشركة يأتي من الخادم لا من عدّ الحقول', () async {
    final profileApi = FakeProfileApi(
      company: const CompanyProfileRead(
        name: 'شركة قديمة',
        commercialRegister: '',
        vatNumber: '',
        buildingNumber: '',
        street: '',
        district: '',
        city: '',
        postalCode: '',
        isComplete: true,
      ),
    );

    final company = await build(
      profileApi,
      MemoryResponseCache(),
    ).loadCompany();

    // حقول فارغة و«مكتملة» معاً: إعفاء الشركات السابقة على العنوان الوطني
    // (T607). أي حساب في الشاشة كان سيقول عكس ما يقوله الخادم.
    expect(company!.isComplete, isTrue);
  });
}
