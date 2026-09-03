import 'dart:async';

import 'package:haraj_mobile/data/bidding/sse_channel.dart';

/// قناة SSE مزيَّفة: كل «فتح» يأخذ البثّ التالي في الطابور.
///
/// الاختبار يصف الاتصالات المتعاقبة بالترتيب، فيصير سلوك إعادة الاتصال قابلاً
/// للوصف نصّاً: «أول اتصال يعطي إطاراً ثم ينقطع، والثاني يعطي إطاراً أحدث».
///
/// بعد نفاد الطابور يعطي بثّاً **لا يرسل ولا ينتهي**: خادمٌ صامت والمقبس
/// مفتوح. هذه أخطر حالة في الملف كله، لأنها الوحيدة التي تبدو فيها الشاشة
/// سليمة وهي تعرض أرقاماً بائتة — ومهلة النبض هي ما يجب أن يكشفها.
final class FakeSseChannel implements SseChannel {
  FakeSseChannel(this._connections);

  final List<Stream<String>> _connections;
  final List<StreamController<String>> _silent = <StreamController<String>>[];

  int opened = 0;

  @override
  Stream<String> open() {
    final index = opened++;
    if (index < _connections.length) return _connections[index];

    final controller = StreamController<String>();
    _silent.add(controller);
    return controller.stream;
  }

  /// تُستدعى في نهاية الاختبار كي لا يبقى مؤقّت معلَّقاً.
  Future<void> dispose() async {
    for (final controller in _silent) {
      await controller.close();
    }
  }
}

/// إطار `event: state` بحمولته، كما يكتبه `apps/bidding/live.py`.
String stateFrame(String data) => 'id: d1\nevent: state\ndata: $data';

/// حمولة إطار بمزايدة واحدة قائمة.
String liveBidPayload({
  String id = 'BID-1',
  String vehicleId = 'V-1',
  String amount = '12600.00',
  bool isWithdrawn = false,
  bool isSuperseded = false,
}) =>
    '{"bids":[{"id":"$id","vehicle_id":"$vehicleId","amount":"$amount",'
    '"is_withdrawn":$isWithdrawn,"is_superseded":$isSuperseded}],'
    '"vehicles":[]}';

/// نبضة — إطار تعليق لا يحمل بيانات.
const String heartbeatFrame = ': heartbeat';
