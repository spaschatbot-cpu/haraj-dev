import 'dart:io';

import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:haraj_mobile/data/activity/activity_repository_impl.dart';
import 'package:haraj_mobile/data/api/generated/clients/auctions_api.dart';
import 'package:haraj_mobile/data/api/generated/clients/invoices_api.dart';
import 'package:haraj_mobile/data/api/generated/models/auction.dart';
import 'package:haraj_mobile/data/api/generated/models/auction_status.dart';
import 'package:haraj_mobile/data/api/generated/models/insurance_lock.dart'
    as api;
import 'package:haraj_mobile/data/api/generated/models/insurance_state.dart'
    as api;
import 'package:haraj_mobile/data/api/generated/models/invoice.dart' as api;
import 'package:haraj_mobile/data/api/generated/models/invoice_status.dart'
    as api;
import 'package:haraj_mobile/data/api/generated/models/paginated_auction_list.dart';
import 'package:haraj_mobile/data/api/generated/models/paginated_invoice_list.dart';
import 'package:haraj_mobile/data/api/generated/models/paginated_participation_list.dart';
import 'package:haraj_mobile/data/api/generated/models/paginated_purchase_list.dart';
import 'package:haraj_mobile/data/api/generated/models/participation.dart'
    as api;
import 'package:haraj_mobile/data/api/generated/models/purchase.dart' as api;
import 'package:haraj_mobile/data/api/generated/models/purchase_state.dart'
    as api;
import 'package:haraj_mobile/data/local/cache/response_cache.dart';
import 'package:haraj_mobile/domain/activity/entities/invoice.dart';
import 'package:haraj_mobile/domain/activity/entities/participation.dart';
import 'package:haraj_mobile/domain/common/failure.dart';
import 'package:haraj_mobile/domain/common/snapshot.dart';

import '../../support/memory_response_cache.dart';

/// القوائم الثلاث تحت نفس عقد T704: الخادم أولاً، والكاش عند صمته وحده (H5).
void main() {
  final fetchedAt = DateTime.utc(2026, 9, 1, 10);

  final participations = PaginatedParticipationList(
    count: 1,
    results: <api.Participation>[
      api.Participation(
        auctionId: 'AUC-91',
        auctionTitle: 'مزاد الرياض ١٢',
        auctionStatusLabel: 'جارٍ الآن',
        endsAt: DateTime.utc(2026, 9, 3, 17),
        bidsCount: 3,
        insuranceState: api.InsuranceState.held,
        insuranceStateLabel: 'محجوز لهذا المزاد',
        insuranceAmount: '2500.00',
        currency: 'SAR',
      ),
    ],
  );

  final invoice = api.Invoice(
    id: 'INV-7',
    number: 'F-2026-7',
    totalAmount: '12600.00',
    paidAmount: '0.00',
    dueAmount: '12600.00',
    currency: 'SAR',
    status: api.InvoiceStatus.open,
    statusLabel: 'غير مسدَّدة',
    issuedAt: DateTime.utc(2026, 9, 1, 6),
    insuranceLock: const api.InsuranceLock(
      amount: '2500.00',
      currency: 'SAR',
      note: 'تأمينك مقفول على هذه الفاتورة حتى السداد.',
    ),
  );

  final purchases = PaginatedPurchaseList(
    count: 1,
    results: <api.Purchase>[
      api.Purchase(
        id: 'P-1',
        vehicleId: 'V-55',
        lotNumber: '14',
        title: 'تويوتا كامري ٢٠٢٢',
        auctionTitle: 'مزاد الرياض ١٢',
        awardedAmount: '12600.00',
        currency: 'SAR',
        awardedAt: DateTime.utc(2026, 9, 1, 5),
        state: api.PurchaseState.invoiced,
        stateLabel: 'صدرت فاتورتها',
        invoice: invoice,
      ),
    ],
  );

  final invoices = PaginatedInvoiceList(
    count: 1,
    results: <api.Invoice>[invoice],
  );

  ActivityRepositoryImpl buildRepository({
    required _FakeAuctionsApi auctions,
    required _FakeInvoicesApi invoices,
    ResponseCache? cache,
  }) => ActivityRepositoryImpl(
    auctions: auctions,
    invoices: invoices,
    cache: cache ?? MemoryResponseCache(),
    clock: () => fetchedAt,
  );

  test('النجاح يرجع نسخة طازجة ويكتب كل قائمة بمفتاحها', () async {
    final cache = MemoryResponseCache();
    final repository = buildRepository(
      auctions: _FakeAuctionsApi(participations: participations),
      invoices: _FakeInvoicesApi(invoices: invoices, purchases: purchases),
      cache: cache,
    );

    final mine = await repository.loadParticipations();
    await repository.loadPurchases();
    await repository.loadInvoices();

    expect(mine.origin, DataOrigin.network);
    expect(mine.fetchedAt, fetchedAt);
    // مفتاح لكل قائمة: قائمتان بمفتاح واحد تدوس إحداهما الأخرى في الكاش.
    expect(await cache.read(CacheKeys.participations), isNotNull);
    expect(await cache.read(CacheKeys.purchases), isNotNull);
    expect(await cache.read(CacheKeys.invoices), isNotNull);
  });

  test('المبالغ تصل نصّاً كما أرسلها الخادم، والمتبقّي لا يُطرح', () async {
    final repository = buildRepository(
      auctions: _FakeAuctionsApi(participations: participations),
      invoices: _FakeInvoicesApi(invoices: invoices, purchases: purchases),
    );

    final mine = (await repository.loadInvoices()).value.single;

    expect(mine.total.amount, '12600.00');
    expect(mine.paid.amount, '0.00');
    expect(mine.due.amount, '12600.00');
    expect(mine.total.currency, 'SAR');
  });

  test('حالة الفاتورة تصل من الخادم بحرفها ولا تُشتق هنا', () async {
    // الحالة ووصفها العربي ينتقلان كما هما. اشتقاقها في العميل هو بالضبط ما
    // جعل شاشات v1 تختلف عن الفاتورة نفسها.
    final paidLabelButOpenState = api.Invoice(
      id: 'INV-9',
      number: 'F-2026-9',
      totalAmount: '12600.00',
      paidAmount: '12600.00',
      dueAmount: '600.00',
      currency: 'SAR',
      status: api.InvoiceStatus.open,
      statusLabel: 'غير مسدَّدة',
      issuedAt: DateTime.utc(2026, 9, 1, 6),
    );

    final repository = buildRepository(
      auctions: _FakeAuctionsApi(participations: participations),
      invoices: _FakeInvoicesApi(
        invoices: PaginatedInvoiceList(
          count: 1,
          results: <api.Invoice>[paidLabelButOpenState],
        ),
        purchases: purchases,
      ),
    );

    final mine = (await repository.loadInvoices()).value.single;

    expect(mine.state, InvoiceState.open);
    expect(mine.stateLabel, 'غير مسدَّدة');
    expect(mine.due.amount, '600.00');
  });

  test('حالة التأمين في كل مزاد تصل مسمّاة بمبلغها', () async {
    final repository = buildRepository(
      auctions: _FakeAuctionsApi(participations: participations),
      invoices: _FakeInvoicesApi(invoices: invoices, purchases: purchases),
    );

    final mine = (await repository.loadParticipations()).value.single;

    expect(mine.insuranceState, InsuranceState.held);
    expect(mine.insuranceStateLabel, 'محجوز لهذا المزاد');
    expect(mine.insuranceMoney?.amount, '2500.00');
  });

  test('مبلغ تأمين بلا عملة لا يُعرض رقماً ناقصاً', () async {
    final halfAmount = PaginatedParticipationList(
      count: 1,
      results: <api.Participation>[
        api.Participation(
          auctionId: 'AUC-92',
          auctionTitle: 'مزاد جدة ٣',
          auctionStatusLabel: 'منتهٍ',
          endsAt: DateTime.utc(2026, 8, 30, 17),
          bidsCount: 1,
          insuranceState: api.InsuranceState.released,
          insuranceStateLabel: 'فُكّ بعد نهاية المزاد',
        ),
      ],
    );

    final repository = buildRepository(
      auctions: _FakeAuctionsApi(participations: halfAmount),
      invoices: _FakeInvoicesApi(invoices: invoices, purchases: purchases),
    );

    final mine = (await repository.loadParticipations()).value.single;

    expect(mine.insuranceMoney, isNull);
    expect(mine.insuranceStateLabel, 'فُكّ بعد نهاية المزاد');
  });

  test('انقطاع الشبكة بعد نجاح سابق يعرض المحفوظ بطابعه', () async {
    final cache = MemoryResponseCache();
    final invoicesApi = _FakeInvoicesApi(
      invoices: invoices,
      purchases: purchases,
    );
    final repository = buildRepository(
      auctions: _FakeAuctionsApi(participations: participations),
      invoices: invoicesApi,
      cache: cache,
    );

    await repository.loadPurchases();
    invoicesApi.failWith = _offlineException();

    final snapshot = await repository.loadPurchases();

    expect(snapshot.isStale, isTrue);
    expect(snapshot.fetchedAt, fetchedAt);
    // الفاتورة المتداخلة تنجو من دورة الحفظ والقراءة — وهي أول ما يسقط حين
    // تُحفظ خريطة `toJson()` بلا ترميز نصّي.
    expect(snapshot.value.single.invoice?.number, 'F-2026-7');
    expect(
      snapshot.value.single.invoice?.insuranceLock?.note,
      'تأمينك مقفول على هذه الفاتورة حتى السداد.',
    );
  });

  test('انقطاع الشبكة بلا كاش يرمي العطب ولا يرجع قائمة فارغة', () async {
    final repository = buildRepository(
      auctions: _FakeAuctionsApi(participations: participations)
        ..failWith = _offlineException(),
      invoices: _FakeInvoicesApi(invoices: invoices, purchases: purchases),
    );

    // «ما عندك فواتير» أسوأ من «تعذّر التحديث»: قارئها يظنّ ما عليه سقط عنه.
    await expectLater(
      repository.loadParticipations(),
      throwsA(isA<TransportFailure>()),
    );
  });

  test('خطأ ردّ به الخادم لا يُخفى خلف بيانات قديمة', () async {
    final cache = MemoryResponseCache();
    final invoicesApi = _FakeInvoicesApi(
      invoices: invoices,
      purchases: purchases,
    );
    final repository = buildRepository(
      auctions: _FakeAuctionsApi(participations: participations),
      invoices: invoicesApi,
      cache: cache,
    );

    await repository.loadInvoices();
    invoicesApi.failWith = DioException(
      requestOptions: RequestOptions(path: '/api/v1/invoices'),
      type: DioExceptionType.badResponse,
      response: Response<Object?>(
        requestOptions: RequestOptions(path: '/api/v1/invoices'),
        statusCode: 403,
        data: <String, Object?>{
          'error': <String, Object?>{
            'code': 'FORBIDDEN',
            'message': 'لا تملك صلاحية عرض هذه الفواتير.',
          },
        },
      ),
    );

    await expectLater(repository.loadInvoices(), throwsA(isA<ApiFailure>()));
  });
}

DioException _offlineException() => DioException(
  requestOptions: RequestOptions(path: '/api/v1/participations'),
  type: DioExceptionType.connectionError,
  error: const SocketException('offline'),
);

final class _FakeAuctionsApi implements AuctionsApi {
  _FakeAuctionsApi({required this.participations});

  final PaginatedParticipationList participations;
  DioException? failWith;

  @override
  Future<PaginatedParticipationList> participationsList({
    int? page,
    int? pageSize,
  }) async {
    final failure = failWith;
    if (failure != null) throw failure;
    return participations;
  }

  @override
  Future<PaginatedAuctionList> auctionsList({
    AuctionStatus? status,
    int? page,
    int? pageSize,
  }) => throw UnimplementedError();

  @override
  Future<Auction> auctionsRetrieve({required String auctionId}) =>
      throw UnimplementedError();
}

final class _FakeInvoicesApi implements InvoicesApi {
  _FakeInvoicesApi({required this.invoices, required this.purchases});

  final PaginatedInvoiceList invoices;
  final PaginatedPurchaseList purchases;
  DioException? failWith;

  @override
  Future<PaginatedInvoiceList> invoicesList({int? page, int? pageSize}) async {
    final failure = failWith;
    if (failure != null) throw failure;
    return invoices;
  }

  @override
  Future<PaginatedPurchaseList> purchasesList({
    int? page,
    int? pageSize,
  }) async {
    final failure = failWith;
    if (failure != null) throw failure;
    return purchases;
  }
}
