import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:haraj_mobile/data/api/generated/clients/devices_api.dart';
import 'package:haraj_mobile/data/notifications/device_registry_impl.dart';
import 'package:haraj_mobile/domain/common/failure.dart';
import 'package:haraj_mobile/domain/notifications/repositories/push_service.dart';

import '../support/recording_http_adapter.dart';

/// T716 — ⚠️ «يُربط بالمستخدم من الرمز لا من معامل».
///
/// ثغرة IDOR على FCM في v1: كان معرّف الحساب حقلاً في الجسم، فتسجيل جهاز باسم
/// عميل آخر كان بُعد حقلٍ واحد — وإشعارات هذه القناة تقول على ماذا يزايد الرجل
/// وبكم. الفحص هنا على الطلب المُركَّب نفسه.
void main() {
  ({DeviceRegistryImpl registry, RecordingHttpAdapter wire}) build({
    int statusCode = 200,
    Map<String, Object?> body = const {
      'id': '1',
      'platform': 'android',
      'registered_at': '2026-09-01T10:00:00Z',
    },
  }) {
    final adapter = RecordingHttpAdapter(statusCode: statusCode, body: body);
    final dio = Dio(BaseOptions(baseUrl: 'https://api.example.invalid'))
      ..httpClientAdapter = adapter;
    return (registry: DeviceRegistryImpl(api: DevicesApi(dio)), wire: adapter);
  }

  test('جسم التسجيل هو الرمز والمنصة، ولا مالك فيه', () async {
    final it = build();

    await it.registry.register(
      token: 'fcm-token-abcdef',
      platform: DevicePlatform.android,
    );

    expect(it.wire.lastRequestBody, {
      'token': 'fcm-token-abcdef',
      'platform': 'android',
    });
  });

  test('لا مفتاح يسمّي حساباً بأي صياغة', () async {
    // مكتوبة صراحةً لأنها ثغرة v1 نفسها: الاختبار الذي يقارن الخريطة كاملةً
    // يمرّ اليوم، وهذا يقول **لماذا** لمن يقرؤه غداً.
    final it = build();

    await it.registry.register(
      token: 'fcm-token-abcdef',
      platform: DevicePlatform.ios,
    );

    expect(
      it.wire.lastRequestBody.keys,
      isNot(
        anyElement(
          anyOf('user', 'user_id', 'userId', 'account', 'account_id', 'phone'),
        ),
      ),
    );
  });

  test('المنصة تُرسل كما يعرفها المخطط', () async {
    final it = build();

    await it.registry.register(
      token: 'fcm-token-abcdef',
      platform: DevicePlatform.ios,
    );

    expect(it.wire.lastRequestBody['platform'], 'ios');
  });

  test('إلغاء التسجيل يرسل الرمز وحده', () async {
    final it = build(statusCode: 204);

    await it.registry.unregister(token: 'fcm-token-abcdef');

    expect(it.wire.lastRequestBody, {'token': 'fcm-token-abcdef'});
    expect(it.wire.lastRequest.path, contains('/devices/unregister'));
  });

  test('رفض الخادم يخرج `Failure` مصنَّفاً لا `DioException`', () async {
    // لو تسرّبت `DioException` لاحتاج كل مستدعٍ أن يعرف dio.
    final it = build(
      statusCode: 403,
      body: const {
        'error': {'code': 'FORBIDDEN', 'message': 'غير مصرّح لك.'},
      },
    );

    await expectLater(
      it.registry.register(
        token: 'fcm-token-abcdef',
        platform: DevicePlatform.android,
      ),
      throwsA(
        isA<ApiFailure>()
            .having((f) => f.code, 'code', 'FORBIDDEN')
            .having((f) => f.message, 'message', 'غير مصرّح لك.'),
      ),
    );
  });
}
