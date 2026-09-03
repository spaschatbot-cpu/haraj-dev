import 'package:flutter_test/flutter_test.dart';
import 'package:haraj_mobile/domain/catalog/entities/auction_summary.dart';
import 'package:haraj_mobile/domain/catalog/entities/vehicle_query.dart';
import 'package:haraj_mobile/domain/catalog/entities/vehicle_summary.dart';
import 'package:haraj_mobile/domain/common/snapshot.dart';
import 'package:haraj_mobile/presentation/catalog/auction_vehicles_screen.dart';
import 'package:haraj_mobile/presentation/catalog/vehicle_screen.dart';
import 'package:haraj_mobile/presentation/catalog/widgets/auction_card.dart';
import 'package:haraj_mobile/presentation/catalog/widgets/vehicle_card.dart';

import '../support/catalog_fakes.dart';
import '../support/pump_app.dart';

/// مسار التصفّح كاملاً عبر الموجّه المُعلَن: رئيسية ← مركبات المزاد ← المركبة.
///
/// يُختبَر عبر `GoRouter` نفسه لا بـ`Navigator.push` في الاختبار: المسار الذي
/// يفتحه الإشعار (معيار H6) هو هذا المسار المسمّى، وشاشةٌ تُفتح بطريقين لا
/// يعرف الإشعار أيّهما يقصد.
void main() {
  testWidgets('كرت المزاد يفتح مركباته، وكرت المركبة يفتح صفحتها', (
    tester,
  ) async {
    final catalog = FakeCatalogRepository(
      home: fresh(
        HomeAuctions(
          running: <AuctionSummary>[auctionSummary(id: 'a-7')],
          upcoming: const <AuctionSummary>[],
        ),
      ),
      vehiclePages: <int, Snapshot<VehiclePage>>{
        1: fresh(
          VehiclePage(
            vehicles: <VehicleSummary>[vehicleSummary(id: 'v-9')],
            totalCount: 1,
            hasMore: false,
          ),
        ),
      },
      vehicle: fresh(vehicleDetail(id: 'v-9')),
    );

    await pumpApp(tester, catalog: catalog);
    await tester.pumpAndSettle();

    await tester.tap(find.byType(AuctionCard));
    await tester.pumpAndSettle();

    expect(find.byType(AuctionVehiclesScreen), findsOneWidget);
    expect(catalog.receivedAuctionIds.single, 'a-7');

    await tester.tap(find.byType(VehicleCard));
    await tester.pumpAndSettle();

    expect(find.byType(VehicleScreen), findsOneWidget);
  });
}
