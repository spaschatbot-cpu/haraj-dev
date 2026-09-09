import 'dart:convert';

import '../../domain/catalog/entities/auction_phase.dart';
import '../../domain/catalog/entities/auction_summary.dart';
import '../../domain/catalog/entities/vehicle_detail.dart';
import '../../domain/catalog/entities/vehicle_feed.dart';
import '../../domain/catalog/entities/vehicle_query.dart';
import '../../domain/catalog/repositories/catalog_repository.dart';
import '../../domain/common/failure.dart';
import '../../domain/common/snapshot.dart';
import '../api/api_call.dart';
import '../api/generated/clients/auctions_api.dart';
import '../api/generated/clients/vehicles_api.dart';
import '../api/generated/models/auction_page.dart' as api;
import '../api/generated/models/phase.dart' as api;
import '../api/generated/models/state.dart' as api;
import '../api/generated/models/vehicle_card.dart' as api;
import '../api/generated/models/vehicle_images.dart' as api;
import '../api/generated/models/vehicle_page.dart' as api;
import '../local/cache/response_cache.dart';
import 'catalog_mapper.dart';

/// التصفّح: الخادم أولاً، والكاش شبكة أمان عند **صمت** الخادم وحده.
///
/// القرار المنسوخ من `WalletRepositoryImpl` عمداً — وهو ما يجب أن يُنسخ، لا
/// الشكل: الكاش يعوّض صمت الخادم لا كلامه. خطأٌ ردّ به الخادم (404 لمركبة
/// حُذفت، 403 لمزاد لا يُرى) يمرّ برسالته العربية ولا يُخفى خلف صفحةٍ قديمة
/// تقول إن كل شيء على ما يرام.
final class CatalogRepositoryImpl implements CatalogRepository {
  CatalogRepositoryImpl({
    required AuctionsApi auctions,
    required VehiclesApi vehicles,
    required ResponseCache cache,
    required VehicleSpecificationLabels specificationLabels,
    DateTime Function()? clock,
  }) : _auctions = auctions,
       _vehicles = vehicles,
       _cache = cache,
       _labels = specificationLabels,
       _clock = clock ?? DateTime.now;

  /// حجم الصفحة يُرسَل صراحةً كي لا يكون سلوك التطبيق رهناً بافتراضٍ في
  /// الخادم قد يتغيّر تحت قائمةٍ ضُبط تمريرها عليه.
  static const int pageSize = 20;

  static const String _runningKey = 'running';
  static const String _upcomingKey = 'upcoming';

  final AuctionsApi _auctions;
  final VehiclesApi _vehicles;
  final ResponseCache _cache;
  final VehicleSpecificationLabels _labels;
  final DateTime Function() _clock;

  /// الترقيم على السلك `limit`/`offset` لا `page`.
  ///
  /// الصفحة مفهوم الشاشة، والإزاحة مفهوم العقد؛ والترجمة بينهما تقع هنا مرّةً
  /// بدل أن تتكرّر في كل نداء. وكانت الطبقة تُرسل `page`/`page_size` — معاملين
  /// لا يعرفهما الخادم، فيتجاهلهما ويردّ الصفحة الأولى دائماً: تمريرٌ لا ينتهي
  /// ويعيد نفسه، وهو عطلٌ يبدو «بطئاً» لا خطأً.
  static int _offsetOf(int page) => (page - 1) * pageSize;

  @override
  Future<Snapshot<HomeAuctions>> loadHomeAuctions() async {
    try {
      // الاستعلامان متوازيان: الرئيسية شاشة الإقلاع، وتسلسلُ نداءين يضاعف
      // زمن أول ما يراه العميل بلا سبب.
      final (running, upcoming) = await callApi(() async {
        final responses = await Future.wait(<Future<api.AuctionPage>>[
          _auctions.auctionsList(state: api.State.live, limit: pageSize),
          _auctions.auctionsList(state: api.State.scheduled, limit: pageSize),
        ]);
        return (responses[0], responses[1]);
      });

      final fetchedAt = _clock().toUtc();
      await _cache.write(
        CacheKeys.homeAuctions,
        jsonEncode(<String, Object?>{
          _runningKey: running.toJson(),
          _upcomingKey: upcoming.toJson(),
        }),
        fetchedAtUtc: fetchedAt,
      );

      return Snapshot.fresh(_homeAuctions(running, upcoming), at: fetchedAt);
    } on TransportFailure {
      final cached = await _readHomeAuctionsCache();
      if (cached != null) return cached;
      rethrow;
    }
  }

  @override
  Future<Snapshot<VehiclePage>> loadAuctionVehicles(
    String auctionId,
    VehicleQuery query,
  ) async {
    final id = int.tryParse(auctionId);
    if (id == null) throw ArgumentError.value(auctionId, 'auctionId');

    try {
      final page = await callApi(
        () => _auctions.auctionsVehiclesList(
          id: id,
          search: _blankToNull(query.search),
          make: _blankToNull(query.make),
          yearFrom: query.yearFrom,
          yearTo: query.yearTo,
          limit: pageSize,
          offset: _offsetOf(query.page),
        ),
      );

      final fetchedAt = _clock().toUtc();
      if (query.isFirstUnfilteredPage) {
        await _cache.write(
          CacheKeys.auctionVehicles(auctionId),
          jsonEncode(page.toJson()),
          fetchedAtUtc: fetchedAt,
        );
      }
      return Snapshot.fresh(page.toPage(), at: fetchedAt);
    } on TransportFailure {
      // بحثٌ بلا خادم لا جواب له: الردّ على «ابحث عن كامري» بقائمةٍ محفوظة لم
      // تُبحث كذبٌ أوضح من رسالة الخطأ. فالمحفوظ يُقرأ للصفحة الأولى بلا
      // ترشيح وحدها.
      if (!query.isFirstUnfilteredPage) rethrow;
      final cached = await _readVehiclesCache(auctionId);
      if (cached != null) return cached;
      rethrow;
    }
  }

  @override
  Future<Snapshot<VehicleFeed>> loadVehicleFeed(VehicleQuery query) async {
    final phase = query.phase;
    // برمجيّاً لا للمستخدم: العرض يبني الاستعلام من تبويبٍ مختار دائماً، وطلبٌ
    // بلا تبويب خطأُ استدعاء يجب أن ينكسر عند كاتبه لا أن يصير طلباً بلا معنى.
    assert(phase != null, 'loadVehicleFeed needs a phase');

    try {
      // نداء **واحد** للصفحة والعدّادات الثلاثة. الأرقام الثلاثة من لحظة
      // الصفحة نفسها، وإلا قال التبويب رقماً لا يصف ما يُفتح فيه.
      final feed = await callApi(
        () => _vehicles.vehiclesList(
          phase: _apiPhaseOf(phase),
          search: _blankToNull(query.search),
          make: _blankToNull(query.make),
          yearFrom: query.yearFrom,
          yearTo: query.yearTo,
          limit: pageSize,
          offset: _offsetOf(query.page),
        ),
      );

      final fetchedAt = _clock().toUtc();
      if (query.isFirstUnfilteredPage && phase != null) {
        await _cache.write(
          CacheKeys.vehicleFeed(phase.slug),
          jsonEncode(feed.toJson()),
          fetchedAtUtc: fetchedAt,
        );
      }
      return Snapshot.fresh(feed.toDomain(), at: fetchedAt);
    } on TransportFailure {
      // نفس قرار قائمة مركبات المزاد: المحفوظ يجيب عن «وريني التبويب» ولا
      // يجيب عن «ابحث عن كامري» — بحثٌ لم يُبحث ليس نتيجة.
      if (!query.isFirstUnfilteredPage || phase == null) rethrow;
      final cached = await _readFeedCache(phase.slug);
      if (cached != null) return cached;
      rethrow;
    }
  }

  @override
  Future<Snapshot<VehicleDetail>> loadVehicle(String vehicleId) async {
    final id = int.tryParse(vehicleId);
    if (id == null) throw ArgumentError.value(vehicleId, 'vehicleId');

    try {
      // الكرت وصورُه معاً: نداءان متوازيان لا متتاليان — الصفحة لا تُرسم قبل
      // وصول الاثنين على أي حال، فتسلسلُهما يضيف زمناً بلا مقابل.
      final (card, images) = await callApi(() async {
        final vehicle = _vehicles.vehiclesRetrieve(id: id);
        final gallery = _vehicles.vehiclesImagesList(id: id);
        return (await vehicle, await gallery);
      });

      final fetchedAt = _clock().toUtc();
      await _cache.write(
        CacheKeys.vehicle(vehicleId),
        jsonEncode(<String, Object?>{
          _cardKey: card.toJson(),
          _imagesKey: images.toJson(),
        }),
        fetchedAtUtc: fetchedAt,
      );
      return Snapshot.fresh(_detail(card, images), at: fetchedAt);
    } on TransportFailure {
      final cached = await _readVehicleCache(vehicleId);
      if (cached != null) return cached;
      rethrow;
    }
  }

  static const String _cardKey = 'card';
  static const String _imagesKey = 'images';

  VehicleDetail _detail(api.VehicleCard card, api.VehicleImages images) =>
      VehicleDetail(
        card: card.toDomain(),
        imageUrls: images.toDomain(),
        specifications: card.specifications(_labels),
      );

  HomeAuctions _homeAuctions(
    api.AuctionPage running,
    api.AuctionPage upcoming,
  ) => HomeAuctions(running: running.toDomain(), upcoming: upcoming.toDomain());

  Future<Snapshot<HomeAuctions>?> _readHomeAuctionsCache() async {
    final document = await _cache.read(CacheKeys.homeAuctions);
    if (document == null) return null;
    try {
      final body = document.decode();
      final running = api.AuctionPage.fromJson(
        body[_runningKey]! as Map<String, Object?>,
      );
      final upcoming = api.AuctionPage.fromJson(
        body[_upcomingKey]! as Map<String, Object?>,
      );
      return Snapshot.cached(
        _homeAuctions(running, upcoming),
        storedAt: document.fetchedAtUtc,
      );
    } on Object {
      // كاشٌ من نسخة مخطط أقدم لم يعد يُفكّ: يُعامل كغياب كاش، لا كعطب.
      return null;
    }
  }

  Future<Snapshot<VehiclePage>?> _readVehiclesCache(String auctionId) async {
    final document = await _cache.read(CacheKeys.auctionVehicles(auctionId));
    if (document == null) return null;
    try {
      final page = api.VehiclePage.fromJson(document.decode());
      return Snapshot.cached(page.toPage(), storedAt: document.fetchedAtUtc);
    } on Object {
      return null;
    }
  }

  Future<Snapshot<VehicleFeed>?> _readFeedCache(String phaseSlug) async {
    final document = await _cache.read(CacheKeys.vehicleFeed(phaseSlug));
    if (document == null) return null;
    try {
      final feed = api.VehiclePage.fromJson(document.decode());
      // العدّادات المحفوظة تُعرض كما حُفظت، بعلامة «آخر تحديث» فوقها: رقمٌ
      // قديمٌ معلَّمٌ بلحظته أصدق من تبويبٍ بلا رقم أو من شبكة بيضاء.
      return Snapshot.cached(feed.toDomain(), storedAt: document.fetchedAtUtc);
    } on Object {
      return null;
    }
  }

  Future<Snapshot<VehicleDetail>?> _readVehicleCache(String vehicleId) async {
    final document = await _cache.read(CacheKeys.vehicle(vehicleId));
    if (document == null) return null;
    try {
      final body = document.decode();
      final card = api.VehicleCard.fromJson(
        body[_cardKey]! as Map<String, Object?>,
      );
      final images = api.VehicleImages.fromJson(
        body[_imagesKey]! as Map<String, Object?>,
      );
      return Snapshot.cached(
        _detail(card, images),
        storedAt: document.fetchedAtUtc,
      );
    } on Object {
      return null;
    }
  }
}

/// الطور الذي يُسأل عنه الخادم.
///
/// `unknown` لا يُرسَل: لا معنى لسؤال «وريني ما لا أفهمه»، وإرسال نصٍّ فارغ
/// يجعل الخادم يرشّح على قيمة لا وجود لها فيردّ فراغاً بلا سبب مكتوب.
api.Phase? _apiPhaseOf(AuctionPhase? phase) => switch (phase) {
  AuctionPhase.upcoming => api.Phase.soon,
  AuctionPhase.active => api.Phase.active,
  AuctionPhase.ended => api.Phase.ended,
  AuctionPhase.unknown || null => null,
};

/// حقلُ بحثٍ فارغ ليس ترشيحاً بقيمةٍ فارغة: إرساله `search=` يجعل الخادم يرشّح
/// على نصّ فارغ، وهو سؤالٌ آخر غير «بلا بحث».
String? _blankToNull(String? value) =>
    (value == null || value.isEmpty) ? null : value;
