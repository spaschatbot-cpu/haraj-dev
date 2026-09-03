// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, unused_import, invalid_annotation_target, unnecessary_import

import 'package:dio/dio.dart';
import 'package:retrofit/retrofit.dart';

part 'live_api.g.dart';

@RestApi()
abstract class LiveApi {
  factory LiveApi(Dio dio, {String? baseUrl}) = _LiveApi;

  /// البثّ الحي — مزايدات المتصل وحده.
  ///
  /// بثّ SSE (`text/event-stream`). كل إطار `event: state` يحمل في `data` كائن LiveState. لا يحمل رقم أحد غيرك: المزاد مغلق ولا نقطة تسرد مزايدات مركبة.
  @GET('/api/v1/live')
  Future<String> liveUpdates();
}
