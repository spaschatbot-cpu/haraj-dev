import 'dart:convert';

import '../../domain/bidding/entities/bid_outcome.dart';
import '../../domain/bidding/entities/live_bids_update.dart';
import '../../domain/bidding/entities/placed_bid.dart';
import '../../domain/bidding/repositories/bidding_repository.dart';
import '../../domain/common/failure.dart';
import '../../domain/common/failure_codes.dart';
import '../../domain/common/snapshot.dart';
import '../api/api_call.dart';
import '../api/generated/clients/bids_api.dart';
import '../api/generated/models/bid_submission.dart';
import '../api/generated/models/live_state.dart' as api;
import '../api/generated/models/paginated_bid_list.dart' as api;
import '../local/cache/response_cache.dart';
import 'bid_mapper.dart';
import 'sse_channel.dart';

/// المزايدة: نداءٌ واحد لكل فعل، وجوابُ الخادم كما هو.
///
/// **ليس في هذا الملف شرط أهلية واحد.** لا فحص رصيد، ولا «هل المزاد مفتوح»،
/// ولا حدّ أدنى محسوب. `check_eligibility` في الخلفية نقطة القرار الوحيدة،
/// وكل ما يفعله هذا المستودع أن يرسل ويترجم الجواب. الرفض يخرج من هنا
/// `ApiFailure` برسالة الخادم العربية حرفياً، فيعرضها `FailureView` بلا صياغة
/// ثانية — وهو ما يجعل التطبيق والويب يرفضان بنفس السبب المُعدَّد (J7).
final class BiddingRepositoryImpl implements BiddingRepository {
  BiddingRepositoryImpl({
    required BidsApi api,
    required ResponseCache cache,
    required SseChannel live,
    DateTime Function()? clock,
    Future<void> Function(Duration)? pause,
    Duration reconnectDelay = const Duration(seconds: 3),
    Duration silenceTimeout = const Duration(seconds: 10),
  }) : _api = api,
       _cache = cache,
       _live = live,
       _clock = clock ?? DateTime.now,
       _pause = pause ?? Future<void>.delayed,
       _reconnectDelay = reconnectDelay,
       _silenceTimeout = silenceTimeout;

  final BidsApi _api;
  final ResponseCache _cache;
  final SseChannel _live;
  final DateTime Function() _clock;
  final Future<void> Function(Duration) _pause;

  /// كم ننتظر قبل محاولة اتصال جديدة بعد انقطاع.
  final Duration _reconnectDelay;

  /// كم من الصمت يكفي لنقول «انقطع».
  ///
  /// الخادم ينبض كل ثانيتين حتى حين لا يتغيّر شيء، فصمتٌ أطول من هذا ليس
  /// هدوءاً بل عطب. بلا هذه المهلة يبدو الاتصال الميت كالاتصال الهادئ تماماً،
  /// ويظلّ رقمٌ عمره ساعة معروضاً كأنه الآن.
  final Duration _silenceTimeout;

  @override
  Future<BidOutcome> placeBid({
    required String vehicleId,
    required String amount,
    bool confirmLower = false,
  }) async {
    try {
      final bid = await callApi(
        () => _api.bidsPlace(
          vehicleId: vehicleId,
          // المبلغ يمرّ نصّاً من حقل الإدخال إلى الجسم بلا تحويل (المادة ٣-٢)،
          // و`confirm_lower` يُرسَل دائماً بقيمته لا يُحذف أحياناً: جسمٌ يتغيّر
          // شكله حسب الفرع الذي بناه جسمٌ لا يُقرأ معناه من مكان واحد.
          body: BidSubmission(amount: amount, confirmLower: confirmLower),
        ),
      );
      return BidAccepted(bid.toDomain());
    } on ApiFailure catch (failure) {
      final confirmation = _asLowerConfirmation(failure);
      if (confirmation != null) return confirmation;
      // كل رفض آخر يبقى خطأً برسالة الخادم — لا نوع خاص ولا نصّ عندنا.
      rethrow;
    }
  }

  /// الرفض الوحيد الذي يعني «افعل شيئاً» لا «اعرض جملة».
  ///
  /// المبلغان يُقرآن من حمولة الرفض نفسه. لو قرأناهما بنداء جديد لصار الرقم
  /// المعروض في الحوار قد يخالف الرقم الذي كان الرفض عنه، فيوقّع العميل على
  /// خفضٍ لم يُسأل عنه.
  BidNeedsLowerConfirmation? _asLowerConfirmation(ApiFailure failure) {
    if (failure.code != FailureCodes.bidLowerNeedsConfirmation) return null;

    final standing = _text(failure.detail, 'standing');
    final requested = _text(failure.detail, 'requested');
    // رفضٌ بلا مبلغيه لا يصلح لحوارٍ تعريفه أنه «يذكر المبلغين». يُعرض عندها
    // كأي رفض آخر برسالته، ولا نخترع رقماً ليكتمل الشكل.
    if (standing == null || requested == null) return null;

    return BidNeedsLowerConfirmation(
      standingAmount: standing,
      requestedAmount: requested,
      message: failure.message,
    );
  }

  static String? _text(Map<String, Object?>? detail, String key) {
    final value = detail?[key];
    return value is String && value.isNotEmpty ? value : null;
  }

  @override
  Future<PlacedBid> withdrawBid(String bidId) async {
    final bid = await callApi(() => _api.bidsWithdraw(bidId: bidId));
    return bid.toDomain();
  }

  @override
  Future<Snapshot<List<PlacedBid>>> myBids() async {
    try {
      final page = await callApi(() => _api.bidsMineList());
      final fetchedAt = _clock().toUtc();
      await _cache.write(
        CacheKeys.myBids,
        jsonEncode(page.toJson()),
        fetchedAtUtc: fetchedAt,
      );
      return Snapshot.fresh(_toDomain(page), at: fetchedAt);
    } on TransportFailure {
      // الخادم لم يتكلّم: آخر ما نعرف مع علامة «آخر تحديث» (H5). قائمة فارغة
      // هنا تُقرأ «ما زايدتَ على شيء»، وهي كذبة لمن زايد قبل دقيقة.
      final cached = await _readCache();
      if (cached != null) return cached;
      rethrow;
    }
    // `ApiFailure` تمرّ كما هي: الخادم تكلّم، ورسالته هي الحقيقة.
  }

  Future<Snapshot<List<PlacedBid>>?> _readCache() async {
    final document = await _cache.read(CacheKeys.myBids);
    if (document == null) return null;
    try {
      final page = api.PaginatedBidList.fromJson(document.decode());
      return Snapshot.cached(_toDomain(page), storedAt: document.fetchedAtUtc);
    } on Object {
      // كاش من نسخة مخطط أقدم لم يعد يُفكّ: غياب كاش، لا عطب.
      return null;
    }
  }

  static List<PlacedBid> _toDomain(api.PaginatedBidList page) =>
      page.results.map((bid) => bid.toDomain()).toList(growable: false);

  @override
  Stream<LiveBidsUpdate> watchLive() async* {
    var bids = const <LiveStandingBid>[];
    var connection = LiveConnection.connecting;
    yield LiveBidsUpdate(connection: connection, bids: bids);

    while (true) {
      try {
        // المهلة على **الإطارات** لا على الاتصال: خادم توقّف عن النبض وترك
        // المقبس مفتوحاً يبدو حياً على مستوى الشبكة، وهو أخطر من انقطاع صريح.
        await for (final frame in _live.open().timeout(_silenceTimeout)) {
          var changed = false;

          if (connection != LiveConnection.live) {
            connection = LiveConnection.live;
            changed = true;
          }

          final state = _bidsIn(frame);
          if (state != null) {
            bids = state;
            changed = true;
          }

          // النبضة وحدها لا تُصدر تحديثاً: إعادة بناء الشاشة كل ثانيتين بلا
          // تغيّر تكلفة بلا مقابل يراه أحد.
          if (changed) yield LiveBidsUpdate(connection: connection, bids: bids);
        }
      } on Object {
        // انقطاع، أو صمت، أو ردّ لا يُقرأ — ثلاثتها تعني «لا تصدّق ما ترى».
        // ولا تُرمى للشاشة: البثّ رفاهية فوق البيانات المحمَّلة، وسقوطه لا
        // يجوز أن يُسقط شاشة تعمل.
      }

      connection = LiveConnection.lost;
      // الأرقام تبقى معروضة مع العلامة. محوها يخفي عن العميل ما زايد به فعلاً.
      yield LiveBidsUpdate(connection: connection, bids: bids);

      await _pause(_reconnectDelay);

      connection = LiveConnection.connecting;
      yield LiveBidsUpdate(connection: connection, bids: bids);
    }
  }

  /// المزايدات داخل إطار `event: state`، أو `null` لأي إطار آخر.
  List<LiveStandingBid>? _bidsIn(String frame) {
    String? event;
    final data = <String>[];

    for (final line in frame.split('\n')) {
      // `:` وحدها تعليق SSE — النبضة تصل بهذا الشكل.
      if (line.startsWith(':')) continue;
      if (line.startsWith('event:')) {
        event = line.substring('event:'.length).trim();
      } else if (line.startsWith('data:')) {
        data.add(line.substring('data:'.length).trim());
      }
    }

    if (event != 'state' || data.isEmpty) return null;

    try {
      final decoded = jsonDecode(data.join('\n'));
      if (decoded is! Map<String, Object?>) return null;
      return api.LiveState.fromJson(decoded).toDomainBids();
    } on Object {
      // إطارٌ لا يُقرأ لا يمحو آخر ما نعرف: آخر قيمة صالحة تبقى، وحالةُ
      // الاتصال هي التي تقول للعميل كم يصدّقها.
      return null;
    }
  }
}
