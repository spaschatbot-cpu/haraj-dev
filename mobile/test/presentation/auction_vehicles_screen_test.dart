import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:haraj_mobile/domain/catalog/entities/vehicle_query.dart';
import 'package:haraj_mobile/domain/catalog/entities/vehicle_summary.dart';
import 'package:haraj_mobile/domain/common/failure.dart';
import 'package:haraj_mobile/domain/common/snapshot.dart';
import 'package:haraj_mobile/l10n/generated/app_localizations.dart';
import 'package:haraj_mobile/presentation/catalog/auction_vehicles_screen.dart';
import 'package:haraj_mobile/presentation/catalog/widgets/vehicle_card.dart';
import 'package:haraj_mobile/presentation/common/failure_view.dart';
import 'package:haraj_mobile/presentation/common/stale_data_banner.dart';

import '../support/catalog_fakes.dart';
import '../support/pump_screen.dart';

/// T708 — قائمة مركبات المزاد: بحث وترشيح وترقيم صفحات، **كلها من الخادم**.
void main() {
  late AppLocalizations ar;

  setUp(() async {
    ar = await AppLocalizations.delegate.load(const Locale('ar'));
  });

  Snapshot<VehiclePage> pageOf(
    List<VehicleSummary> vehicles, {
    int totalCount = 200,
    bool hasMore = true,
  }) => fresh(
    VehiclePage(vehicles: vehicles, totalCount: totalCount, hasMore: hasMore),
  );

  testWidgets('الصفحة الأولى تُطلب من الخادم عند الفتح', (tester) async {
    final catalog = FakeCatalogRepository(
      vehiclePages: <int, Snapshot<VehiclePage>>{
        1: pageOf(<VehicleSummary>[vehicleSummary()], hasMore: false),
      },
    );

    await pumpScreen(
      tester,
      const AuctionVehiclesScreen(auctionId: 'a-1'),
      catalog: catalog,
    );
    await tester.pumpAndSettle();

    expect(catalog.receivedAuctionIds.single, 'a-1');
    expect(catalog.receivedQueries.single.page, 1);
    expect(find.byType(VehicleCard), findsOneWidget);
  });

  testWidgets('العدد المعروض هو العدد الكلي من الخادم لا طول الصفحة', (
    tester,
  ) async {
    final catalog = FakeCatalogRepository(
      vehiclePages: <int, Snapshot<VehiclePage>>{
        1: pageOf(
          <VehicleSummary>[vehicleSummary()],
          totalCount: 200,
          hasMore: false,
        ),
      },
    );

    await pumpScreen(
      tester,
      const AuctionVehiclesScreen(auctionId: 'a-1'),
      catalog: catalog,
    );
    await tester.pumpAndSettle();

    expect(find.text(ar.vehiclesResultsCount(200)), findsOneWidget);
  });

  testWidgets('البحث يُرسَل إلى الخادم ولا يُطبَّق في التطبيق', (tester) async {
    // النتيجة التي يردّ بها الخادم لا تطابق نصّ البحث حرفياً — عمداً: لو رشّح
    // التطبيق محلياً لاختفت، ولاختلف جوابه عن جواب الويب لنفس المعايير.
    final catalog = FakeCatalogRepository(
      vehiclePages: <int, Snapshot<VehiclePage>>{
        1: pageOf(
          <VehicleSummary>[vehicleSummary(title: 'Toyota Camry 2021')],
          totalCount: 1,
          hasMore: false,
        ),
      },
    );

    await pumpScreen(
      tester,
      const AuctionVehiclesScreen(auctionId: 'a-1'),
      catalog: catalog,
    );
    await tester.pumpAndSettle();

    await tester.enterText(find.byType(TextField).first, 'لكزس');
    await tester.tap(find.text(ar.filterApply));
    await tester.pumpAndSettle();

    expect(catalog.receivedQueries.last.search, 'لكزس');
    expect(catalog.receivedQueries.last.page, 1);
    expect(find.byType(VehicleCard), findsOneWidget);
  });

  testWidgets('الترشيح بالماركة والسنة يعبر إلى الخادم كما هو', (tester) async {
    final catalog = FakeCatalogRepository(
      vehiclePages: <int, Snapshot<VehiclePage>>{
        1: pageOf(
          <VehicleSummary>[vehicleSummary()],
          totalCount: 1,
          hasMore: false,
        ),
      },
    );

    await pumpScreen(
      tester,
      const AuctionVehiclesScreen(auctionId: 'a-1'),
      catalog: catalog,
    );
    await tester.pumpAndSettle();

    await tester.enterText(
      find.widgetWithText(TextField, ar.filterMake),
      'Toyota',
    );
    await tester.enterText(
      find.widgetWithText(TextField, ar.filterYearFrom),
      '2018',
    );
    await tester.enterText(
      find.widgetWithText(TextField, ar.filterYearTo),
      '2022',
    );
    await tester.tap(find.text(ar.filterApply));
    await tester.pumpAndSettle();

    final query = catalog.receivedQueries.last;
    expect(query.make, 'Toyota');
    expect(query.yearFrom, 2018);
    expect(query.yearTo, 2022);
  });

  testWidgets('نهاية القائمة تطلب الصفحة التالية وتضيفها لا تستبدلها', (
    tester,
  ) async {
    final catalog = FakeCatalogRepository(
      vehiclePages: <int, Snapshot<VehiclePage>>{
        1: pageOf(<VehicleSummary>[
          vehicleSummary(id: 'v-1', title: 'First'),
        ], totalCount: 2),
        2: pageOf(
          <VehicleSummary>[vehicleSummary(id: 'v-2', title: 'Second')],
          totalCount: 2,
          hasMore: false,
        ),
      },
    );

    await pumpScreen(
      tester,
      const AuctionVehiclesScreen(auctionId: 'a-1'),
      catalog: catalog,
    );
    await tester.pumpAndSettle();

    expect(catalog.receivedQueries.map((query) => query.page), <int>[1, 2]);
    expect(find.text('First'), findsOneWidget);

    // الثانية أسفل الشاشة: القائمة تبني عناصرها عند الوصول إليها، وهو نصف
    // معيار H2 — فالتحقق منها يبدأ بالتمرير إليها.
    await tester.drag(find.byType(ListView), const Offset(0, -600));
    await tester.pumpAndSettle();
    expect(find.text('Second'), findsOneWidget);
  });

  testWidgets('لا نتائج: حالة فارغة مكتوبة، والترشيح يبقى قابلاً للإزالة', (
    tester,
  ) async {
    final catalog = FakeCatalogRepository(
      vehiclePages: <int, Snapshot<VehiclePage>>{
        1: pageOf(const <VehicleSummary>[], totalCount: 0, hasMore: false),
      },
    );

    await pumpScreen(
      tester,
      const AuctionVehiclesScreen(auctionId: 'a-1'),
      catalog: catalog,
    );
    await tester.pumpAndSettle();

    expect(find.text(ar.vehiclesEmpty), findsOneWidget);

    await tester.enterText(find.byType(TextField).first, 'لكزس');
    await tester.tap(find.text(ar.filterApply));
    await tester.pumpAndSettle();

    // زرّ إزالة الترشيح يظهر بعد الترشيح — وإلا وقف العميل أمام قائمة فارغة
    // بلا طريق للرجوع.
    expect(find.text(ar.filterClear), findsOneWidget);
  });

  testWidgets('فشل الصفحة الأولى يعرض الخطأ مع زرّ إعادة محاولة', (
    tester,
  ) async {
    final catalog = FakeCatalogRepository(
      vehiclesError: const TransportFailure(TransportProblem.offline),
    );

    await pumpScreen(
      tester,
      const AuctionVehiclesScreen(auctionId: 'a-1'),
      catalog: catalog,
    );
    await tester.pumpAndSettle();

    expect(find.byType(FailureView), findsOneWidget);
    expect(find.text(ar.errorOffline), findsOneWidget);

    await tester.tap(find.text(ar.retry));
    await tester.pumpAndSettle();

    expect(catalog.receivedQueries, hasLength(2));
  });

  testWidgets('البيانات المحفوظة تظهر بعلامة «آخر تحديث»', (tester) async {
    final catalog = FakeCatalogRepository(
      vehiclePages: <int, Snapshot<VehiclePage>>{
        1: Snapshot<VehiclePage>.cached(
          VehiclePage(
            vehicles: <VehicleSummary>[vehicleSummary()],
            totalCount: 1,
            hasMore: false,
          ),
          storedAt: fixedNowUtc,
        ),
      },
    );

    await pumpScreen(
      tester,
      const AuctionVehiclesScreen(auctionId: 'a-1'),
      catalog: catalog,
    );
    await tester.pumpAndSettle();

    expect(find.byType(StaleDataBanner), findsOneWidget);
    expect(find.byType(VehicleCard), findsOneWidget);
  });
}
