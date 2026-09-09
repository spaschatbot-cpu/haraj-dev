// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, unused_import, invalid_annotation_target, unnecessary_import

import 'package:dio/dio.dart';
import 'package:retrofit/retrofit.dart';

part 'live_api.g.dart';

@RestApi()
abstract class LiveApi {
  factory LiveApi(Dio dio, {String? baseUrl}) = _LiveApi;

  /// التحديث الحي.
  ///
  /// `GET /api/v1/live/` — server-sent events for the signed-in caller.
  ///
  /// A long-lived `text/event-stream`: the client opens it once and is told when.
  /// something it may see has changed, instead of asking every two seconds. What.
  /// may be seen is `apps.bidding.live`'s decision — **the caller's own bids and.
  /// public states, never another bidder's number** — and that module's docstring.
  /// is where the reasoning lives.
  ///
  /// Streaming without Channels.
  /// --------------------------.
  /// A `StreamingHttpResponse` over the ASGI application already in.
  /// `config/asgi.py`. No Channels, no Redis, no second process: the added.
  /// infrastructure would be a second thing to deploy, monitor and get wrong, and.
  /// what it buys — push instead of a two-second re-derivation — is not.
  /// perceptible to a person.
  ///
  /// The cost is one connection held per watching customer and one small query.
  /// per connection per tick. That is a real cost and it is stated rather than.
  /// hidden: it is the number to watch when this platform gets busy, and the.
  /// moment it stops being acceptable is the moment Channels earns its place.
  ///
  /// Every stream ends.
  /// -----------------.
  /// After `MAX_STREAM_SECONDS` the server closes and the client reconnects. A.
  /// stream that lives forever outlives the deploy that replaced the code running.
  /// it, and the reconnect is what gets the customer onto the current version.
  ///
  /// ‏`renderer_classes` وسببه.
  /// -------------------------.
  /// ‏`EventSource` يرسل `Accept: text/event-stream` ولا يقبل غيره. وDRF يفاوض.
  /// على النوع **قبل** أن يصل الطلبُ هذه الدالة، فيقارنه بمُصيّراته — وليس فيها.
  /// هذا النوع — ويردّ **406** بلا أن يُنفَّذ سطرٌ هنا. والنتيجة أن الصفحة تكتب.
  /// «انقطع الاتصال» على خادمٍ سليم، وأن `curl` بلا `Accept` ينجح فيبدو العطل.
  /// في المتصفّح وحده.
  ///
  /// والمُصيّر أدناه لا يُصيّر شيئاً: الجسم `StreamingHttpResponse` يخرج كما.
  /// هو. وجودُه إعلانٌ للمفاوَضة بأن هذا النوع مقبول، لا طبقةُ تحويل.
  @GET('/api/v1/live/')
  Future<String> liveUpdates();
}
