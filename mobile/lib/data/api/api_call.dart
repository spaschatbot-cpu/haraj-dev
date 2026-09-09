import 'package:dio/dio.dart';

import '../../domain/common/failure.dart';
import 'api_failure_mapper.dart';

/// المعبر الوحيد بين العميل المولَّد وطبقة النطاق.
///
/// كل نداء API يمرّ من هنا، فيخرج من `data` شيئان لا ثالث لهما: كيان نطاق، أو
/// `Failure` مصنَّف. `DioException` لا تتسرّب إلى `domain` ولا إلى
/// `presentation` أبداً — لو تسرّبت لاحتاجت كل شاشة أن تعرف dio.
Future<T> callApi<T>(Future<T> Function() request) async {
  try {
    return await request();
  } on DioException catch (error) {
    throw ApiFailureMapper.fromDioException(error);
  } on Failure {
    rethrow;
  } on Object catch (error, stackTrace) {
    // لا فرع صامت: ما لا نعرفه يُصنَّف `UnexpectedFailure` ويظهر، ولا يُبتلع
    // (المادة ٢-٢ بروحها).
    //
    // ويُكتب في سجلّ التطوير قبل أن يُغلَّف: الشاشة تعرض «حدث خطأ غير متوقع»
    // — وهي الرسالة الصحيحة للعميل وعديمةُ النفع للمطوّر. بلا هذا السطر
    // يُطارَد العطلُ بالتخمين، وقد طورد.
    assert(() {
      // ignore: avoid_print
      print('UnexpectedFailure: $error\n$stackTrace');
      return true;
    }());
    throw UnexpectedFailure(error, stackTrace: stackTrace);
  }
}
