import 'dart:io';

import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:haraj_mobile/data/api/api_failure_mapper.dart';
import 'package:haraj_mobile/domain/common/failure.dart';

/// T705 — المعالجة الموحّدة تقرأ `{"error": {code, message}}`.
void main() {
  final request = RequestOptions(path: '/api/v1/wallet');

  DioException badResponse(Object? body, {int status = 400}) => DioException(
    requestOptions: request,
    type: DioExceptionType.badResponse,
    response: Response<Object?>(
      requestOptions: request,
      statusCode: status,
      data: body,
    ),
  );

  group('ردّ الخادم بالشكل الموحّد', () {
    test('الرسالة تُنقل كما جاءت حرفاً بحرف', () {
      const serverMessage = 'رصيدك المتاح لا يكفي لهذه المزايدة.';

      final failure = ApiFailureMapper.fromDioException(
        badResponse(<String, Object?>{
          'error': <String, Object?>{
            'code': 'INSUFFICIENT_FREE_INSURANCE',
            'message': serverMessage,
          },
        }, status: 403),
      );

      expect(failure, isA<ApiFailure>());
      failure as ApiFailure;
      // لو استبدلها التطبيق بنصّ عنده، صار له نسخة ثانية من القاعدة.
      expect(failure.message, serverMessage);
      expect(failure.code, 'INSUFFICIENT_FREE_INSURANCE');
      expect(failure.statusCode, 403);
    });

    test('رمز 409 لخفض المزايدة يصل بالرمز كي يتفرّع عليه العرض', () {
      final failure =
          ApiFailureMapper.fromDioException(
                badResponse(<String, Object?>{
                  'error': <String, Object?>{
                    'code': 'BID_LOWER_NEEDS_CONFIRMATION',
                    'message': 'مزايدتك أقل من الحالية. هل تريد المتابعة؟',
                  },
                }, status: 409),
              )
              as ApiFailure;

      expect(failure.code, 'BID_LOWER_NEEDS_CONFIRMATION');
      expect(failure.statusCode, 409);
    });
  });

  group('الخادم لم يتكلّم', () {
    test('انقطاع الشبكة يُصنَّف offline', () {
      final failure = ApiFailureMapper.fromDioException(
        DioException(
          requestOptions: request,
          type: DioExceptionType.connectionError,
          error: const SocketException('no route to host'),
        ),
      );

      expect(failure, isA<TransportFailure>());
      expect((failure as TransportFailure).problem, TransportProblem.offline);
    });

    test('انقضاء المهلة يُصنَّف timeout', () {
      final failure = ApiFailureMapper.fromDioException(
        DioException(
          requestOptions: request,
          type: DioExceptionType.receiveTimeout,
        ),
      );

      expect((failure as TransportFailure).problem, TransportProblem.timeout);
    });
  });

  group('ردّ لا يطابق الشكل الموحّد', () {
    test('جسم نصّي يُصنَّف malformed ولا يُبتلع', () {
      final failure = ApiFailureMapper.fromDioException(
        badResponse('<html>502 Bad Gateway</html>', status: 502),
      );

      expect(failure, isA<TransportFailure>());
      expect(
        (failure as TransportFailure).problem,
        TransportProblem.malformedResponse,
      );
    });

    test('JSON بلا مفتاح error يُصنَّف malformed', () {
      final failure = ApiFailureMapper.fromDioException(
        badResponse(<String, Object?>{'detail': 'not found'}, status: 404),
      );

      expect(
        (failure as TransportFailure).problem,
        TransportProblem.malformedResponse,
      );
    });
  });

  test('خطأ ليس من dio يُصنَّف ولا يُسقط المسار', () {
    final failure = ApiFailureMapper.fromError(
      StateError('boom'),
      StackTrace.current,
    );

    expect(failure, isA<UnexpectedFailure>());
  });
}
