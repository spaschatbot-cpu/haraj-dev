import 'package:dio/dio.dart';

/// إنشاء عميل HTTP بإعداد واحد للتطبيق كله.
///
/// المهلات قصيرة عمداً: «الغياب ليس دليلاً» (المادة ٢-٤) — انتظار طويل يجعل
/// المستخدم يعيد الإرسال ظانّاً أن شيئاً لم يحدث، وهذا بالضبط ما ولّد حركات
/// مكرّرة في v1. مهلة واضحة + رسالة «تعذّر الوصول» أأمن من انتظار مفتوح.
abstract final class DioFactory {
  static const Duration _connectTimeout = Duration(seconds: 10);
  static const Duration _readTimeout = Duration(seconds: 20);

  static Dio build({
    required String baseUrl,
    List<Interceptor> interceptors = const [],
  }) {
    final dio = Dio(
      BaseOptions(
        baseUrl: baseUrl,
        connectTimeout: _connectTimeout,
        receiveTimeout: _readTimeout,
        sendTimeout: _readTimeout,
        // الخادم يردّ الشكل الموحّد للأخطاء بحالة 4xx/5xx، ونريد جسمه.
        responseType: ResponseType.json,
        headers: const {'Accept': 'application/json'},
      ),
    );
    dio.interceptors.addAll(interceptors);
    return dio;
  }
}
