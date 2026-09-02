import 'dart:io' show SocketException;

import 'package:dio/dio.dart';

import '../../domain/common/failure.dart';
import 'generated/models/api_error_envelope.dart';

/// يحوّل أي عطب في النقل إلى `Failure` مصنَّف (T705).
///
/// نقطة القرار الوحيدة لقراءة الشكل الموحّد `{"error": {code, message}}` في
/// التطبيق كله. أي مكان آخر يفتح جسم الخطأ بيده يُرفض في المراجعة: نسخة ثانية
/// من قاعدة العرض ستفترق عن هذه (المادة ٤-٥).
///
/// ملاحظة مقصودة: التحويل يستعمل `ApiErrorEnvelope` **المولَّد من المخطط**، لا
/// قراءة يدوية للمفاتيح — فيسقط البناء إن غيّر الخادم شكل الخطأ، بدل أن يسقط
/// صامتاً عند المستخدم.
abstract final class ApiFailureMapper {
  static Failure fromDioException(DioException exception) {
    return switch (exception.type) {
      DioExceptionType.connectionError => _transport(
        exception,
        _problemForConnectionError(exception),
      ),
      DioExceptionType.connectionTimeout ||
      DioExceptionType.sendTimeout ||
      DioExceptionType.receiveTimeout ||
      DioExceptionType.transformTimeout => _transport(
        exception,
        TransportProblem.timeout,
      ),
      DioExceptionType.cancel => _transport(
        exception,
        TransportProblem.timeout,
      ),
      DioExceptionType.badCertificate => _transport(
        exception,
        TransportProblem.offline,
      ),
      DioExceptionType.badResponse => _fromResponse(exception),
      DioExceptionType.unknown => _fromUnknown(exception),
    };
  }

  /// خطأ غير آتٍ من dio أصلاً — يُصنَّف ولا يُبتلع.
  static Failure fromError(Object error, StackTrace stackTrace) {
    if (error is Failure) return error;
    if (error is DioException) return fromDioException(error);
    return UnexpectedFailure(error, stackTrace: stackTrace);
  }

  static Failure _fromResponse(DioException exception) {
    final response = exception.response;
    final body = response?.data;
    if (body is! Map) {
      // ردّ خطأ بلا الشكل الموحّد: لا نخترع له رسالة عربية، ولا نبتلعه.
      return TransportFailure(
        TransportProblem.malformedResponse,
        cause: exception,
      );
    }

    final ApiErrorEnvelope envelope;
    try {
      envelope = ApiErrorEnvelope.fromJson(
        body.map((key, value) => MapEntry(key.toString(), value)),
      );
    } on Object {
      return TransportFailure(
        TransportProblem.malformedResponse,
        cause: exception,
      );
    }

    final details = exception.response?.data;
    return ApiFailure(
      code: envelope.error.code,
      // تُعرض كما جاءت. لا `if (code == ...) return 'نص عندنا'`.
      message: envelope.error.message,
      statusCode: response?.statusCode,
      details: details is Map<String, Object?> ? details : null,
    );
  }

  static Failure _fromUnknown(DioException exception) {
    if (exception.error is SocketException) {
      return TransportFailure(TransportProblem.offline, cause: exception.error);
    }
    return UnexpectedFailure(
      exception.error ?? exception,
      stackTrace: exception.stackTrace,
    );
  }

  static Failure _transport(DioException exception, TransportProblem problem) =>
      TransportFailure(problem, cause: exception.error ?? exception);

  static TransportProblem _problemForConnectionError(DioException exception) =>
      exception.error is SocketException
      ? TransportProblem.offline
      : TransportProblem.timeout;
}
