import 'dart:convert';
import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:haraj_mobile/data/api/interceptors/auth_interceptor.dart';
import 'package:haraj_mobile/data/local/secure/secure_token_store.dart';

/// T706 — «التجديد التلقائي، وإعادة التوجيه عند 401».
///
/// إعادة التوجيه نفسها مسؤولية الموجّه؛ ما يُختبر هنا هو مصدرها: من يقرّر أن
/// الجلسة سقطت، وكم مرة يحاول قبل أن يقرّر.
void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  late SecureTokenStore tokens;

  setUp(() async {
    FlutterSecureStorage.setMockInitialValues(<String, String>{});
    tokens = SecureTokenStore.platformDefault();
    await tokens.save(access: 'old-access', refresh: 'refresh-token');
  });

  Dio buildClient({
    required Future<bool> Function() refreshSession,
    required void Function() onSessionLost,
    required _RecordingAdapter adapter,
  }) {
    final retryClient = Dio(BaseOptions(baseUrl: 'https://api.invalid'))
      ..httpClientAdapter = adapter;
    return Dio(BaseOptions(baseUrl: 'https://api.invalid'))
      ..httpClientAdapter = adapter
      ..interceptors.add(
        AuthInterceptor(
          tokens: tokens,
          refreshSession: refreshSession,
          retryClient: retryClient,
          onSessionLost: onSessionLost,
        ),
      );
  }

  test('401 مع تجديد ناجح يعيد الطلب مرة واحدة بالرمز الجديد', () async {
    final adapter = _RecordingAdapter(failFirst: 1);
    var lost = 0;

    final client = buildClient(
      refreshSession: () async {
        await tokens.save(access: 'new-access', refresh: 'refresh-token');
        return true;
      },
      onSessionLost: () => lost++,
      adapter: adapter,
    );

    final response = await client.get<Object?>('/api/v1/profile/');

    expect(response.statusCode, 200);
    expect(adapter.authorizations, <String>[
      'Bearer old-access',
      'Bearer new-access',
    ]);
    // الجلسة لم تسقط: التجديد الصامت هو بالضبط ما يمنع إزعاج المستخدم.
    expect(lost, 0);
  });

  test('فشل التجديد يمحو الرموز ويرفع الإشارة مرة واحدة', () async {
    final adapter = _RecordingAdapter(failFirst: 99);
    var lost = 0;

    final client = buildClient(
      refreshSession: () async => false,
      onSessionLost: () => lost++,
      adapter: adapter,
    );

    await expectLater(
      client.get<Object?>('/api/v1/profile/'),
      throwsA(isA<DioException>()),
    );

    expect(await tokens.hasSession(), isFalse);
    expect(lost, 1);
    // محاولة واحدة لا حلقة: رمز تحديث منتهٍ يعني 401 على التجديد نفسه، ودورة
    // بلا سقف هي «الاستردادات المكرَّرة من الكرون» في v1 بطبقة أخرى.
    expect(adapter.authorizations.length, 1);
  });
}

/// محوّل يسجّل ترويسة المصادقة، ويردّ 401 لأول [failFirst] طلبات.
final class _RecordingAdapter implements HttpClientAdapter {
  _RecordingAdapter({required this.failFirst});

  final int failFirst;
  final List<String> authorizations = <String>[];

  @override
  Future<ResponseBody> fetch(
    RequestOptions options,
    Stream<Uint8List>? requestStream,
    Future<void>? cancelFuture,
  ) async {
    authorizations.add(options.headers['Authorization'] as String? ?? '');
    final unauthorized = authorizations.length <= failFirst;

    return ResponseBody.fromString(
      jsonEncode(<String, Object?>{
        if (unauthorized)
          'error': <String, Object?>{
            'code': 'not_authenticated',
            'message': 'يلزم تسجيل الدخول',
            'detail': <String, Object?>{},
          },
      }),
      unauthorized ? 401 : 200,
      headers: <String, List<String>>{
        Headers.contentTypeHeader: <String>[Headers.jsonContentType],
      },
    );
  }

  @override
  void close({bool force = false}) {}
}
