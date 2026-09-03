import 'dart:convert';

import '../../domain/catalog/entities/auction_summary.dart';
import '../../domain/catalog/entities/vehicle_detail.dart';
import '../../domain/catalog/entities/vehicle_query.dart';
import '../../domain/catalog/repositories/catalog_repository.dart';
import '../../domain/common/failure.dart';
import '../../domain/common/snapshot.dart';
import '../api/api_call.dart';
import '../api/generated/clients/auctions_api.dart';
import '../api/generated/clients/vehicles_api.dart';
import '../api/generated/models/auction_status.dart';
import '../api/generated/models/paginated_auction_list.dart' as api;
import '../api/generated/models/paginated_vehicle_card_list.dart' as api;
import '../api/generated/models/vehicle.dart' as api;
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
    DateTime Function()? clock,
  }) : _auctions = auctions,
       _vehicles = vehicles,
       _cache = cache,
       _clock = clock ?? DateTime.now;

  /// حجم الصفحة يُرسَل صراحةً كي لا يكون سلوك التطبيق رهناً بافتراضٍ في
  /// الخادم قد يتغيّر تحت قائمةٍ ضُبط تمريرها عليه.
  static const int pageSize = 20;

  static const String _runningKey = 'running';
  static const String _upcomingKey = 'upcoming';

  final AuctionsApi _auctions;
  final VehiclesApi _vehicles;
  final ResponseCache _cache;
  final DateTime Function() _clock;

  @override
  Future<Snapshot<HomeAuctions>> loadHomeAuctions() async {
    try {
      // الاستعلامان متوازيان: الرئيسية شاشة الإقلاع، وتسلسلُ نداءين يضاعف
      // زمن أول ما يراه العميل بلا سبب.
      final (running, upcoming) = await callApi(() async {
        final responses = await Future.wait(<Future<api.PaginatedAuctionList>>[
          _auctions.auctionsList(
            status: AuctionStatus.running,
            page: 1,
            pageSize: pageSize,
          ),
          _auctions.auctionsList(
            status: AuctionStatus.scheduled,
            page: 1,
            pageSize: pageSize,
          ),
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
    try {
      final page = await callApi(
        () => _vehicles.auctionVehiclesList(
          auctionId: auctionId,
          search: _blankToNull(query.search),
          make: _blankToNull(query.make),
          yearFrom: query.yearFrom,
          yearTo: query.yearTo,
          page: query.page,
          pageSize: pageSize,
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
      return Snapshot.fresh(page.toDomain(), at: fetchedAt);
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
  Future<Snapshot<VehicleDetail>> loadVehicle(String vehicleId) async {
    try {
      final vehicle = await callApi(
        () => _vehicles.vehiclesRetrieve(vehicleId: vehicleId),
      );
      final fetchedAt = _clock().toUtc();
      await _cache.write(
        CacheKeys.vehicle(vehicleId),
        jsonEncode(vehicle.toJson()),
        fetchedAtUtc: fetchedAt,
      );
      return Snapshot.fresh(vehicle.toDomain(), at: fetchedAt);
    } on TransportFailure {
      final cached = await _readVehicleCache(vehicleId);
      if (cached != null) return cached;
      rethrow;
    }
  }

  HomeAuctions _homeAuctions(
    api.PaginatedAuctionList running,
    api.PaginatedAuctionList upcoming,
  ) => HomeAuctions(
    running: running.results
        .map((auction) => auction.toDomain())
        .toList(growable: false),
    upcoming: upcoming.results
        .map((auction) => auction.toDomain())
        .toList(growable: false),
  );

  Future<Snapshot<HomeAuctions>?> _readHomeAuctionsCache() async {
    final document = await _cache.read(CacheKeys.homeAuctions);
    if (document == null) return null;
    try {
      final body = document.decode();
      final running = api.PaginatedAuctionList.fromJson(
        body[_runningKey]! as Map<String, Object?>,
      );
      final upcoming = api.PaginatedAuctionList.fromJson(
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
      final page = api.PaginatedVehicleCardList.fromJson(document.decode());
      return Snapshot.cached(page.toDomain(), storedAt: document.fetchedAtUtc);
    } on Object {
      return null;
    }
  }

  Future<Snapshot<VehicleDetail>?> _readVehicleCache(String vehicleId) async {
    final document = await _cache.read(CacheKeys.vehicle(vehicleId));
    if (document == null) return null;
    try {
      final vehicle = api.Vehicle.fromJson(document.decode());
      return Snapshot.cached(
        vehicle.toDomain(),
        storedAt: document.fetchedAtUtc,
      );
    } on Object {
      return null;
    }
  }
}

/// حقلُ بحثٍ فارغ ليس ترشيحاً بقيمةٍ فارغة: إرساله `search=` يجعل الخادم يرشّح
/// على نصّ فارغ، وهو سؤالٌ آخر غير «بلا بحث».
String? _blankToNull(String? value) =>
    (value == null || value.isEmpty) ? null : value;
