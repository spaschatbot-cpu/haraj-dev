import 'dart:io';

import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:haraj_mobile/data/api/generated/clients/auctions_api.dart';
import 'package:haraj_mobile/data/api/generated/clients/vehicles_api.dart';
import 'package:haraj_mobile/data/api/generated/models/auction.dart';
import 'package:haraj_mobile/data/api/generated/models/auction_status.dart';
import 'package:haraj_mobile/data/api/generated/models/paginated_auction_list.dart';
import 'package:haraj_mobile/data/api/generated/models/paginated_participation_list.dart';
import 'package:haraj_mobile/data/api/generated/models/paginated_vehicle_card_list.dart';
import 'package:haraj_mobile/data/api/generated/models/specification.dart';
import 'package:haraj_mobile/data/api/generated/models/vehicle.dart';
import 'package:haraj_mobile/data/api/generated/models/vehicle_card.dart';
import 'package:haraj_mobile/data/catalog/catalog_repository_impl.dart';
import 'package:haraj_mobile/data/local/cache/response_cache.dart';
import 'package:haraj_mobile/domain/catalog/entities/vehicle_query.dart';
import 'package:haraj_mobile/domain/common/failure.dart';
import 'package:haraj_mobile/domain/common/snapshot.dart';

import '../support/memory_response_cache.dart';

/// T707/T708/T709 في طبقة البيانات: ما يُرسَل، وما يُحفظ، وماذا يحدث عند
/// صمت الخادم.
void main() {
  final fetchedAt = DateTime.utc(2026, 9, 3, 20, 50);

  Auction auction(String id, AuctionStatus status) => Auction(
    id: id,
    title: 'Auction $id',
    status: status,
    startsAt: DateTime.utc(2026, 9, 4, 6),
    endsAt: DateTime.utc(2026, 9, 4, 12),
    vehiclesCount: 7,
  );

  VehicleCard card(String id, {String? reservePrice = '50000.10'}) =>
      VehicleCard(
        id: id,
        lotNumber: '17',
        title: 'Toyota Camry 2021',
        thumbnailUrl: null,
        reservePrice: reservePrice,
        currentBidAmount: '12500.00',
        currency: 'SAR',
        bidsCount: 3,
      );

  PaginatedVehicleCardList page(
    List<VehicleCard> results, {
    int count = 200,
    String? next = 'page=2',
  }) => PaginatedVehicleCardList(count: count, results: results, next: next);

  CatalogRepositoryImpl build(
    _FakeAuctionsApi auctions,
    _FakeVehiclesApi vehicles,
    ResponseCache cache,
  ) => CatalogRepositoryImpl(
    auctions: auctions,
    vehicles: vehicles,
    cache: cache,
    clock: () => fetchedAt,
  );

  group('الرئيسية', () {
    test('القسمة من الخادم: استعلامان بحالتين لا تصنيف في التطبيق', () async {
      final auctions = _FakeAuctionsApi(
        byStatus: <AuctionStatus, PaginatedAuctionList>{
          AuctionStatus.running: PaginatedAuctionList(
            count: 1,
            results: <Auction>[auction('a-1', AuctionStatus.running)],
          ),
          AuctionStatus.scheduled: PaginatedAuctionList(
            count: 1,
            results: <Auction>[auction('a-2', AuctionStatus.scheduled)],
          ),
        },
      );
      final repository = build(
        auctions,
        _FakeVehiclesApi(),
        MemoryResponseCache(),
      );

      final snapshot = await repository.loadHomeAuctions();

      expect(auctions.requestedStatuses, <AuctionStatus>{
        AuctionStatus.running,
        AuctionStatus.scheduled,
      });
      expect(snapshot.value.running.single.id, 'a-1');
      expect(snapshot.value.upcoming.single.id, 'a-2');
      expect(snapshot.origin, DataOrigin.network);
    });

    test('انقطاع الشبكة بعد نجاح سابق يعرض المحفوظ بطابعه', () async {
      final cache = MemoryResponseCache();
      final auctions = _FakeAuctionsApi(
        byStatus: <AuctionStatus, PaginatedAuctionList>{
          AuctionStatus.running: PaginatedAuctionList(
            count: 1,
            results: <Auction>[auction('a-1', AuctionStatus.running)],
          ),
          AuctionStatus.scheduled: const PaginatedAuctionList(
            count: 0,
            results: <Auction>[],
          ),
        },
      );
      final repository = build(auctions, _FakeVehiclesApi(), cache);

      await repository.loadHomeAuctions();
      auctions.failWith = _offline('/api/v1/auctions');

      final snapshot = await repository.loadHomeAuctions();

      expect(snapshot.isStale, isTrue);
      expect(snapshot.fetchedAt, fetchedAt);
      expect(snapshot.value.running.single.id, 'a-1');
      // الأوقات تعود UTC من الكاش كما ذهبت — لا انزياح ثلاث ساعات في كل دورة.
      expect(snapshot.value.running.single.startsAt.isUtc, isTrue);
      expect(
        snapshot.value.running.single.startsAt,
        DateTime.utc(2026, 9, 4, 6),
      );
    });

    test('انقطاع بلا كاش يرمي العطب ولا يرجع رئيسية فارغة', () async {
      final auctions = _FakeAuctionsApi(byStatus: const {})
        ..failWith = _offline('/api/v1/auctions');

      final repository = build(
        auctions,
        _FakeVehiclesApi(),
        MemoryResponseCache(),
      );

      // «لا مزادات» جوابٌ عن سؤال آخر: من يقرؤه يظنّ المنصة فارغة.
      await expectLater(
        repository.loadHomeAuctions(),
        throwsA(isA<TransportFailure>()),
      );
    });
  });

  group('مركبات المزاد', () {
    test('البحث والترشيح والصفحة تذهب كلها إلى الخادم', () async {
      final vehicles = _FakeVehiclesApi(
        pages: <int, PaginatedVehicleCardList>{
          2: page(<VehicleCard>[card('v-1')]),
        },
      );
      final repository = build(
        _FakeAuctionsApi(byStatus: const {}),
        vehicles,
        MemoryResponseCache(),
      );

      await repository.loadAuctionVehicles(
        'a-1',
        const VehicleQuery(
          search: 'camry',
          make: 'Toyota',
          yearFrom: 2018,
          yearTo: 2022,
          page: 2,
        ),
      );

      expect(vehicles.lastAuctionId, 'a-1');
      expect(vehicles.lastSearch, 'camry');
      expect(vehicles.lastMake, 'Toyota');
      expect(vehicles.lastYearFrom, 2018);
      expect(vehicles.lastYearTo, 2022);
      expect(vehicles.lastPage, 2);
      expect(vehicles.lastPageSize, CatalogRepositoryImpl.pageSize);
    });

    test('حقل بحث فارغ لا يُرسَل — «بلا بحث» غير «ابحث عن فراغ»', () async {
      final vehicles = _FakeVehiclesApi(
        pages: <int, PaginatedVehicleCardList>{
          1: page(<VehicleCard>[card('v-1')], next: null),
        },
      );
      final repository = build(
        _FakeAuctionsApi(byStatus: const {}),
        vehicles,
        MemoryResponseCache(),
      );

      await repository.loadAuctionVehicles(
        'a-1',
        const VehicleQuery(search: '', make: ''),
      );

      expect(vehicles.lastSearch, isNull);
      expect(vehicles.lastMake, isNull);
    });

    test('«هل من مزيد؟» جواب الخادم لا حساب هنا', () async {
      final repository = build(
        _FakeAuctionsApi(byStatus: const {}),
        _FakeVehiclesApi(
          pages: <int, PaginatedVehicleCardList>{
            1: page(<VehicleCard>[card('v-1')], count: 1, next: null),
          },
        ),
        MemoryResponseCache(),
      );

      final result = await repository.loadAuctionVehicles(
        'a-1',
        const VehicleQuery(),
      );

      expect(result.value.hasMore, isFalse);
      expect(result.value.totalCount, 1);
    });

    test('الصفحة الأولى بلا ترشيح وحدها تُحفظ', () async {
      final cache = MemoryResponseCache();
      final repository = build(
        _FakeAuctionsApi(byStatus: const {}),
        _FakeVehiclesApi(
          pages: <int, PaginatedVehicleCardList>{
            1: page(<VehicleCard>[card('v-1')]),
            2: page(<VehicleCard>[card('v-2')]),
          },
        ),
        cache,
      );

      await repository.loadAuctionVehicles('a-1', const VehicleQuery());
      expect(cache.writeCount, 1);

      await repository.loadAuctionVehicles('a-1', const VehicleQuery(page: 2));
      await repository.loadAuctionVehicles(
        'a-1',
        const VehicleQuery(search: 'camry'),
      );
      expect(cache.writeCount, 1);
    });

    test('بحثٌ بلا خادم يفشل ولا يُجاب بقائمة محفوظة لم تُبحث', () async {
      final cache = MemoryResponseCache();
      final vehicles = _FakeVehiclesApi(
        pages: <int, PaginatedVehicleCardList>{
          1: page(<VehicleCard>[card('v-1')]),
        },
      );
      final repository = build(
        _FakeAuctionsApi(byStatus: const {}),
        vehicles,
        cache,
      );

      await repository.loadAuctionVehicles('a-1', const VehicleQuery());
      vehicles.failWith = _offline('/api/v1/auctions/a-1/vehicles');

      // الصفحة الأولى بلا ترشيح: المحفوظ جوابٌ صادق عن السؤال نفسه.
      final cached = await repository.loadAuctionVehicles(
        'a-1',
        const VehicleQuery(),
      );
      expect(cached.isStale, isTrue);

      // بحثٌ آخر: لا جواب محفوظ له، والردّ بقائمة لم تُبحث كذبٌ أوضح من الخطأ.
      await expectLater(
        repository.loadAuctionVehicles('a-1', const VehicleQuery(search: 'x')),
        throwsA(isA<TransportFailure>()),
      );
    });
  });

  group('المركبة', () {
    test('السعر يصل نصّاً كما هو، ومركبة بلا سعر وقوف تصل بلا سعر', () async {
      final repository = build(
        _FakeAuctionsApi(byStatus: const {}),
        _FakeVehiclesApi(
          vehicle: const Vehicle(
            id: 'v-1',
            lotNumber: '17',
            title: 'Toyota Camry 2021',
            images: <String>['https://example.invalid/1.jpg'],
            specifications: <Specification>[
              Specification(label: 'الممشى', value: '80,000 كم'),
            ],
            reservePrice: '50000.10',
            currentBidAmount: '12500.00',
            currency: 'SAR',
            biddingOpen: true,
          ),
        ),
        MemoryResponseCache(),
      );

      final vehicle = (await repository.loadVehicle('v-1')).value;

      // بلا تقريب ولا تطبيع: `50000.10` تبقى كما أرسلها الخادم (المادة ٣-٢).
      expect(vehicle.reservePrice?.amount, '50000.10');
      expect(vehicle.reservePrice?.currency, 'SAR');
      expect(vehicle.specifications.single.label, 'الممشى');
      expect(vehicle.biddingOpen, isTrue);
    });

    test('غياب سعر الوقوف يبقى غياباً لا صفراً', () async {
      final repository = build(
        _FakeAuctionsApi(byStatus: const {}),
        _FakeVehiclesApi(
          vehicle: const Vehicle(
            id: 'v-1',
            lotNumber: '17',
            title: 'Toyota Camry 2021',
            images: <String>[],
            specifications: <Specification>[],
            reservePrice: null,
            currentBidAmount: '0.00',
            currency: 'SAR',
            biddingOpen: false,
          ),
        ),
        MemoryResponseCache(),
      );

      expect((await repository.loadVehicle('v-1')).value.reservePrice, isNull);
    });

    test('خطأ ردّ به الخادم لا يُخفى خلف نسخة محفوظة', () async {
      final cache = MemoryResponseCache();
      final vehicles = _FakeVehiclesApi(
        vehicle: const Vehicle(
          id: 'v-1',
          lotNumber: '17',
          title: 'Toyota Camry 2021',
          images: <String>[],
          specifications: <Specification>[],
          reservePrice: '50000.10',
          currentBidAmount: '0.00',
          currency: 'SAR',
          biddingOpen: true,
        ),
      );
      final repository = build(
        _FakeAuctionsApi(byStatus: const {}),
        vehicles,
        cache,
      );

      await repository.loadVehicle('v-1');
      vehicles.failWith = DioException(
        requestOptions: RequestOptions(path: '/api/v1/vehicles/v-1'),
        type: DioExceptionType.badResponse,
        response: Response<Object?>(
          requestOptions: RequestOptions(path: '/api/v1/vehicles/v-1'),
          statusCode: 404,
          data: <String, Object?>{
            'error': <String, Object?>{
              'code': 'NOT_FOUND',
              'message': 'المركبة لم تعد معروضة.',
            },
          },
        ),
      );

      // الخادم تكلّم: رسالته هي الحقيقة، وإخفاؤها خلف كاش يكذب على المستخدم.
      await expectLater(
        repository.loadVehicle('v-1'),
        throwsA(isA<ApiFailure>()),
      );
    });
  });
}

DioException _offline(String path) => DioException(
  requestOptions: RequestOptions(path: path),
  type: DioExceptionType.connectionError,
  error: const SocketException('offline'),
);

final class _FakeAuctionsApi implements AuctionsApi {
  _FakeAuctionsApi({required this.byStatus});

  final Map<AuctionStatus, PaginatedAuctionList> byStatus;
  final Set<AuctionStatus> requestedStatuses = <AuctionStatus>{};
  DioException? failWith;

  @override
  Future<PaginatedAuctionList> auctionsList({
    AuctionStatus? status,
    int? page,
    int? pageSize,
  }) async {
    final failure = failWith;
    if (failure != null) throw failure;
    if (status != null) requestedStatuses.add(status);
    return byStatus[status] ??
        const PaginatedAuctionList(count: 0, results: <Auction>[]);
  }

  // «مشاركاتي» (T714) على نفس العميل المولَّد، ولا تعني اختبارات التصفّح في
  // شيء. ترمي بدل أن ترجع فارغاً كي ينكشف أي استدعاء غير متوقَّع.
  @override
  Future<PaginatedParticipationList> participationsList({
    int? page,
    int? pageSize,
  }) => throw UnimplementedError();

  @override
  Future<Auction> auctionsRetrieve({required String auctionId}) =>
      throw UnimplementedError();
}

final class _FakeVehiclesApi implements VehiclesApi {
  _FakeVehiclesApi({this.pages, this.vehicle});

  final Map<int, PaginatedVehicleCardList>? pages;
  final Vehicle? vehicle;
  DioException? failWith;

  String? lastAuctionId;
  String? lastSearch;
  String? lastMake;
  int? lastYearFrom;
  int? lastYearTo;
  int? lastPage;
  int? lastPageSize;

  @override
  Future<PaginatedVehicleCardList> auctionVehiclesList({
    required String auctionId,
    String? search,
    String? make,
    int? yearFrom,
    int? yearTo,
    int? page,
    int? pageSize,
  }) async {
    lastAuctionId = auctionId;
    lastSearch = search;
    lastMake = make;
    lastYearFrom = yearFrom;
    lastYearTo = yearTo;
    lastPage = page;
    lastPageSize = pageSize;

    final failure = failWith;
    if (failure != null) throw failure;
    return pages![page ?? 1]!;
  }

  @override
  Future<Vehicle> vehiclesRetrieve({required String vehicleId}) async {
    final failure = failWith;
    if (failure != null) throw failure;
    return vehicle!;
  }
}
