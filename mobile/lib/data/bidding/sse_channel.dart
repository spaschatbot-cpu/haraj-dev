import 'dart:async';
import 'dart:convert';

import 'package:dio/dio.dart';

/// اتصال SSE واحد، مقسَّماً إلى إطارات.
///
/// **لماذا هذا الملف مكتوب بيد وليس مولَّداً:** البثّ ليس طلباً وردّاً. مولّد
/// OpenAPI يعطي `Future<String> liveUpdates()` — نداءً يحجز الاتصال خمس عشرة
/// دقيقة ثم يعيد نصّ البثّ كله دفعةً واحدة، وهو ما لا ينفع أحداً. المولَّد يبقى
/// موجوداً لأن المخطط يصف النقطة فعلاً، ولا يُستدعى.
///
/// وما **لا** يُكتب بيد هنا: الحمولة. `data:` تُفكّ إلى `LiveState` المولَّد من
/// المخطط، فلو غيّر الخادم شكل الإطار سقط البناء بدل أن يسقط صامتاً عند
/// المستخدم. المكتوب هنا هو التغليف وحده — أسطر `event:` و`data:`.
abstract interface class SseChannel {
  /// يفتح اتصالاً ويبثّ إطاراته حتى يُغلقه الخادم أو ينقطع.
  ///
  /// كل عنصر إطارٌ كامل بأسطره، بلا السطر الفارغ الفاصل. الإطار غير المفهوم
  /// يمرّ كما هو — من يقرؤه يقرّر، وهذه الطبقة لا تُسقط شيئاً بصمت.
  Stream<String> open();
}

/// تنفيذ فوق dio نفسه الذي تمرّ منه بقية النداءات.
///
/// نفس العميل عمداً: الرمز يُلحق باعتراض المصادقة القائم، فلا يوجد في التطبيق
/// مكانٌ ثانٍ يعرف كيف يُصادَق طلب (المادة ٤-٥).
final class DioSseChannel implements SseChannel {
  const DioSseChannel(this._dio, {String path = '/api/v1/live'}) : _path = path;

  final Dio _dio;
  final String _path;

  @override
  Stream<String> open() async* {
    final response = await _dio.get<ResponseBody>(
      _path,
      options: Options(
        responseType: ResponseType.stream,
        headers: <String, String>{
          'Accept': 'text/event-stream',
          // بثّ يُخزَّن في وسيط هو بثّ يصل دفعةً واحدة بعد انتهائه.
          'Cache-Control': 'no-cache',
        },
        // البثّ يعيش دقائق: مهلة الاستقبال المعتادة تقطعه وهو سليم. الصمت
        // نفسه تكشفه مهلةُ النبض في المستودع، وهي التي تعني «انقطع».
        receiveTimeout: Duration.zero,
      ),
    );

    final body = response.data;
    if (body == null) return;

    // `utf8.decoder` فوق البثّ لا `utf8.decode` لكل قطعة: القطع تُقسَّم على
    // حدود بايتات لا حدود حروف، وحرف عربي مقسوم بين قطعتين يخرج مشوَّهاً.
    yield* utf8.decoder.bind(body.stream).transform(const _SseFrames());
  }
}

/// يجمع القطع إلى إطارات مفصولة بسطر فارغ.
final class _SseFrames extends StreamTransformerBase<String, String> {
  const _SseFrames();

  @override
  Stream<String> bind(Stream<String> stream) async* {
    var buffer = '';
    await for (final chunk in stream) {
      // `\r\n` يُطبَّع أولاً كي لا يصير الفصل قاعدتين تختلفان بين وسيط وآخر.
      buffer += chunk.replaceAll('\r\n', '\n');
      var separator = buffer.indexOf('\n\n');
      while (separator != -1) {
        final frame = buffer.substring(0, separator);
        buffer = buffer.substring(separator + 2);
        if (frame.isNotEmpty) yield frame;
        separator = buffer.indexOf('\n\n');
      }
    }
  }
}
