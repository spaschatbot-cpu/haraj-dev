import 'package:dio/dio.dart';

import '../../local/secure/secure_token_store.dart';

/// يُلحق رمز الوصول بكل طلب، ويجدّده مرة واحدة عند 401.
///
/// **مرة واحدة بالضبط:** العلم `_retriedFlag` على الطلب يمنع حلقة تجديد لا
/// تنتهي حين يكون رمز التحديث نفسه منتهياً. دورة إعادة محاولة بلا سقف هي أصل
/// «الاستردادات المكرَّرة من الكرون» في v1 — نفس الخطأ، طبقة أخرى.
final class AuthInterceptor extends Interceptor {
  AuthInterceptor({
    required SecureTokenStore tokens,
    required Future<bool> Function() refreshSession,
    required Dio retryClient,
    required void Function() onSessionLost,
  }) : _tokens = tokens,
       _refreshSession = refreshSession,
       _retryClient = retryClient,
       _onSessionLost = onSessionLost;

  static const String _retriedFlag = 'haraj.retried_after_refresh';

  final SecureTokenStore _tokens;
  final Future<bool> Function() _refreshSession;

  /// يُنادى مرة واحدة عند سقوط الجلسة، فيعيد الموجّه المستخدم إلى الدخول.
  ///
  /// هنا لا في الشاشات: من يعرف أن الجلسة انتهت هو هذا الاعتراض وحده، وشاشة
  /// تكتشفها بنفسها هي شاشة تعرف 401 — ثم تكتشفها كل شاشة على حدة، وتُنسى في
  /// واحدة.
  final void Function() _onSessionLost;

  /// عميل بلا هذا الاعتراض — إعادة المحاولة لا تمرّ من هنا مرة ثانية.
  final Dio _retryClient;

  @override
  Future<void> onRequest(
    RequestOptions options,
    RequestInterceptorHandler handler,
  ) async {
    final access = await _tokens.readAccessToken();
    if (access != null) {
      options.headers['Authorization'] = 'Bearer $access';
    }
    handler.next(options);
  }

  @override
  Future<void> onError(
    DioException err,
    ErrorInterceptorHandler handler,
  ) async {
    final alreadyRetried = err.requestOptions.extra[_retriedFlag] == true;
    if (err.response?.statusCode != 401 || alreadyRetried) {
      handler.next(err);
      return;
    }

    final refreshed = await _refreshSession();
    if (!refreshed) {
      // فشل التجديد: تُمحى الرموز، ويُبلَّغ الموجّه فيعيد المستخدم إلى الدخول،
      // ويمرّ الخطأ كما هو برسالة الخادم — لا رسالة نخترعها نحن.
      await _tokens.clear();
      _onSessionLost();
      handler.next(err);
      return;
    }

    final access = await _tokens.readAccessToken();
    final options = err.requestOptions
      ..extra[_retriedFlag] = true
      ..headers['Authorization'] = 'Bearer $access';

    try {
      final response = await _retryClient.fetch<Object?>(options);
      handler.resolve(response);
    } on DioException catch (retryError) {
      handler.next(retryError);
    }
  }
}
