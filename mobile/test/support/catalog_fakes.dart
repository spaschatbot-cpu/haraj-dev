import 'dart:async';

import 'package:haraj_mobile/domain/catalog/entities/auction_phase.dart';
import 'package:haraj_mobile/domain/catalog/entities/auction_summary.dart';
import 'package:haraj_mobile/domain/catalog/entities/vehicle_detail.dart';
import 'package:haraj_mobile/domain/catalog/entities/vehicle_feed.dart';
import 'package:haraj_mobile/domain/catalog/entities/vehicle_query.dart';
import 'package:haraj_mobile/domain/catalog/entities/vehicle_summary.dart';
import 'package:haraj_mobile/domain/catalog/repositories/catalog_repository.dart';
import 'package:haraj_mobile/domain/common/money.dart';
import 'package:haraj_mobile/domain/common/snapshot.dart';

/// مستودع تصفّح مزيَّف — يُغني اختبارات الشاشات عن شبكة وعن قاعدة بيانات.
///
/// يسجّل ما وصله من معايير، لأن نصف ما يجب إثباته في T708 ليس ما تعرضه الشاشة
/// بل **ما ترسله**: أن البحث والترشيح والصفحة ذهبت كلها إلى الخادم.
final class FakeCatalogRepository implements CatalogRepository {
  FakeCatalogRepository({
    this.home,
    this.homeError,
    this.vehiclePages,
    this.vehiclesError,
    this.feedPages,
    this.feedError,
    this.vehicle,
    this.vehicleError,
  });

  Snapshot<HomeAuctions>? home;
  Object? homeError;

  /// صفحات مركبات مفهرسة برقم الصفحة.
  Map<int, Snapshot<VehiclePage>>? vehiclePages;
  Object? vehiclesError;

  /// صفحات الشبكة المسطّحة، مفهرسة برقم الصفحة.
  Map<int, Snapshot<VehicleFeed>>? feedPages;
  Object? feedError;

  Snapshot<VehicleDetail>? vehicle;
  Object? vehicleError;

  final List<VehicleQuery> receivedQueries = <VehicleQuery>[];

  /// ما وصل مستودعَ الشبكة من معايير — التبويب والبحث والصفحة.
  ///
  /// يُسجَّل لأن نصف ما يجب إثباته ليس ما تعرضه الشاشة بل **ما ترسله**: أن
  /// التبويب ذهب إلى الخادم، وأن العدّادات لم تُطلب في نداء ثانٍ.
  final List<VehicleQuery> receivedFeedQueries = <VehicleQuery>[];
  final List<String> receivedAuctionIds = <String>[];
  int homeCalls = 0;

  /// بوّابة تُبقي طلب صفحةٍ بعينها معلَّقاً حتى يفتحها الاختبار.
  ///
  /// بها تُختبر اللحظة التي **بين** الطلب وجوابه: ما الذي يفعله المستخدم فيها،
  /// وما الذي يبقى معلَّقاً في الشاشة بعدها.
  final Map<int, Completer<void>> heldPages = <int, Completer<void>>{};

  @override
  Future<Snapshot<HomeAuctions>> loadHomeAuctions() async {
    homeCalls++;
    final error = homeError;
    if (error != null) throw error;
    return home!;
  }

  @override
  Future<Snapshot<VehiclePage>> loadAuctionVehicles(
    String auctionId,
    VehicleQuery query,
  ) async {
    receivedAuctionIds.add(auctionId);
    receivedQueries.add(query);
    await heldPages[query.page]?.future;
    final error = vehiclesError;
    if (error != null) throw error;
    return vehiclePages![query.page]!;
  }

  @override
  Future<Snapshot<VehicleFeed>> loadVehicleFeed(VehicleQuery query) async {
    receivedFeedQueries.add(query);
    await heldPages[query.page]?.future;
    final error = feedError;
    if (error != null) throw error;
    return feedPages![query.page]!;
  }

  @override
  Future<Snapshot<VehicleDetail>> loadVehicle(String vehicleId) async {
    final error = vehicleError;
    if (error != null) throw error;
    return vehicle!;
  }
}

/// مستودع تصفّح بلا مزادات — جذرٌ صامت لاختبارٍ لا يعني التصفّح في شيء.
FakeCatalogRepository emptyCatalogRepository() => FakeCatalogRepository(
  home: Snapshot<HomeAuctions>.fresh(
    const HomeAuctions(
      running: <AuctionSummary>[],
      upcoming: <AuctionSummary>[],
    ),
    at: fixedNowUtc,
  ),
  feedPages: <int, Snapshot<VehicleFeed>>{1: fresh(vehicleFeed())},
);

/// لحظة ثابتة تُبنى منها كل الأوقات في الاختبارات، بتوقيت UTC.
final DateTime fixedNowUtc = DateTime.utc(2026, 9, 3, 20, 50);

AuctionSummary auctionSummary({
  String id = 'a-1',
  String title = 'Riyadh weekly',
  DateTime? startsAt,
  DateTime? endsAt,
  int vehiclesCount = 12,
}) => AuctionSummary(
  id: id,
  title: title,
  startsAt: startsAt ?? fixedNowUtc.add(const Duration(hours: 1)),
  endsAt: endsAt ?? fixedNowUtc.add(const Duration(hours: 5)),
  vehiclesCount: vehiclesCount,
);

VehicleSummary vehicleSummary({
  String id = 'v-1',
  String lotNumber = '17',
  String title = 'Toyota Camry 2021',
  String? thumbnailUrl,
  String? reservePrice = '50000.10',
  int bidsCount = 3,
  String auctionId = 'a-1',
  AuctionPhase phase = AuctionPhase.active,
  DateTime? auctionEndsAt,
}) => VehicleSummary(
  id: id,
  lotNumber: lotNumber,
  title: title,
  thumbnailUrl: thumbnailUrl,
  reservePrice: reservePrice == null
      ? null
      : Money(amount: reservePrice, currency: 'SAR'),
  bidsCount: bidsCount,
  auctionId: auctionId,
  phase: phase,
  auctionEndsAt: auctionEndsAt ?? fixedNowUtc.add(const Duration(hours: 5)),
);

/// عدّادات التبويبات كما ترد من الخادم.
PhaseCounts phaseCounts({int upcoming = 0, int active = 0, int ended = 0}) =>
    PhaseCounts(upcoming: upcoming, active: active, ended: ended);

/// صفحة شبكةٍ وعدّاداتها — كما يصلان في ردٍّ واحد.
VehicleFeed vehicleFeed({
  List<VehicleSummary> vehicles = const <VehicleSummary>[],
  int? totalCount,
  bool hasMore = false,
  PhaseCounts? counts,
}) => VehicleFeed(
  page: VehiclePage(
    vehicles: vehicles,
    totalCount: totalCount ?? vehicles.length,
    hasMore: hasMore,
  ),
  counts: counts ?? phaseCounts(),
);

VehicleDetail vehicleDetail({
  String id = 'v-1',
  String lotNumber = '17',
  String title = 'Toyota Camry 2021',
  List<String> imageUrls = const <String>[],
  List<VehicleSpecification> specifications = const <VehicleSpecification>[],
  String? reservePrice = '50000.10',
  bool biddingOpen = true,
}) => VehicleDetail(
  id: id,
  lotNumber: lotNumber,
  title: title,
  imageUrls: imageUrls,
  specifications: specifications,
  reservePrice: reservePrice == null
      ? null
      : Money(amount: reservePrice, currency: 'SAR'),
  biddingOpen: biddingOpen,
);

Snapshot<T> fresh<T>(T value) => Snapshot<T>.fresh(value, at: fixedNowUtc);
