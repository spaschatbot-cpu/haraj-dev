import 'dart:convert';
import 'dart:typed_data';

import 'package:dio/dio.dart';

/// محوّل HTTP يسجّل ما أُرسل فعلاً بدل أن يرسله.
///
/// الفحص على **الطلب المُركَّب** لا على استدعاء طبقة أعلى: ما يهمّ هو ما يصل
/// إلى الشبكة، فحقلٌ يضيفه اعتراضٌ أو مصفوفٌ في العميل المولَّد يظهر هنا ولا
/// يظهر في اختبار على مستودع مزيّف.
final class RecordingHttpAdapter implements HttpClientAdapter {
  RecordingHttpAdapter({this.statusCode = 200, this.body = const {}});

  final int statusCode;
  final Map<String, Object?> body;

  final List<RequestOptions> requests = [];

  RequestOptions get lastRequest => requests.last;

  /// جسم آخر طلب كخريطة — الشكل الذي بناه العميل قبل تحويله إلى نصّ.
  Map<String, Object?> get lastRequestBody =>
      Map<String, Object?>.from(lastRequest.data as Map);

  @override
  Future<ResponseBody> fetch(
    RequestOptions options,
    Stream<Uint8List>? requestStream,
    Future<void>? cancelFuture,
  ) async {
    requests.add(options);
    return ResponseBody.fromString(
      jsonEncode(body),
      statusCode,
      headers: {
        Headers.contentTypeHeader: [Headers.jsonContentType],
      },
    );
  }

  @override
  void close({bool force = false}) {}
}
