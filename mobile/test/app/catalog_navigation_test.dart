import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:haraj_mobile/domain/catalog/entities/auction_phase.dart';
import 'package:haraj_mobile/domain/catalog/entities/vehicle_feed.dart';
import 'package:haraj_mobile/domain/catalog/entities/vehicle_query.dart';
import 'package:haraj_mobile/domain/catalog/entities/vehicle_summary.dart';
import 'package:haraj_mobile/domain/common/snapshot.dart';
import 'package:haraj_mobile/l10n/generated/app_localizations.dart';
import 'package:haraj_mobile/presentation/catalog/auction_vehicles_screen.dart';
import 'package:haraj_mobile/presentation/catalog/home_screen.dart';
import 'package:haraj_mobile/presentation/catalog/vehicle_screen.dart';
import 'package:haraj_mobile/presentation/catalog/widgets/vehicle_card.dart';

import '../support/catalog_fakes.dart';
import '../support/pump_app.dart';

/// مسار التصفّح كاملاً عبر الموجّه المُعلَن: الشبكة المسطّحة ← المركبة،
/// ومركبات مزادٍ بعينه ← المركبة.
///
/// يُختبَر عبر `GoRouter` نفسه لا بـ`Navigator.push` في الاختبار: المسار الذي
/// يفتحه الإشعار (معيار H6) هو هذا المسار المسمّى، وشاشةٌ تُفتح بطريقين لا
/// يعرف الإشعار أيّهما يقصد.
void main() {
  late AppLocalizations ar;

  setUp(() async {
    ar = await AppLocalizations.delegate.load(const Locale('ar'));
  });

  FakeCatalogRepository browsableCatalog() => FakeCatalogRepository(
    feedPages: <int, Snapshot<VehicleFeed>>{
      1: fresh(
        vehicleFeed(
          vehicles: <VehicleSummary>[vehicleSummary(id: 'v-9')],
          counts: phaseCounts(upcoming: 2, active: 1, ended: 5),
        ),
      ),
    },
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

  testWidgets('كرت المركبة في الشبكة يفتح صفحتها', (tester) async {
    final catalog = browsableCatalog();

    await pumpApp(tester, catalog: catalog);
    await tester.pumpAndSettle();

    expect(find.byType(HomeScreen), findsOneWidget);

    await tester.tap(find.byType(VehicleCard));
    await tester.pumpAndSettle();

    expect(find.byType(VehicleScreen), findsOneWidget);
  });

  testWidgets('التبويب يعيش في العنوان — يُشارَك ويصمد', (tester) async {
    final catalog = browsableCatalog();

    final container = await pumpApp(tester, catalog: catalog);
    await tester.pumpAndSettle();
    expect(catalog.receivedFeedQueries.single.phase, AuctionPhase.active);

    await tester.tap(find.text(ar.homeTabWithCount(ar.homeTabEnded, 5)));
    await tester.pumpAndSettle();

    // التبويب في العنوان لا في حالة الشاشة وحدها: الرابط يُشارَك، وإعادة فتحه
    // تعيد التبويب نفسه.
    expect(currentLocation(container), '/?phase=ended');
    expect(catalog.receivedFeedQueries.last.phase, AuctionPhase.ended);
  });

  testWidgets('عنوانٌ بتبويبٍ صريح يفتحه مباشرةً', (tester) async {
    final catalog = browsableCatalog();

    await pumpApp(tester, catalog: catalog, location: '/?phase=upcoming');
    await tester.pumpAndSettle();

    expect(catalog.receivedFeedQueries.last.phase, AuctionPhase.upcoming);
  });

  testWidgets('تبويبٌ لا نعرفه يفتح الافتراضي ولا يُسقط الشاشة', (
    tester,
  ) async {
    // رابطٌ من إصدارٍ أحدث، أو من إشعار: يجب أن يفتح شيئاً لا أن يعرض عطباً.
    final catalog = browsableCatalog();

    await pumpApp(tester, catalog: catalog, location: '/?phase=martian');
    await tester.pumpAndSettle();

    expect(find.byType(HomeScreen), findsOneWidget);
    expect(catalog.receivedFeedQueries.last.phase, AuctionPhase.defaultTab);
  });

  testWidgets('مسار مزادٍ بعينه ما زال يفتح مركباته', (tester) async {
    // التبويبات مدخل جديد لا حذف لما يعمل: الإشعار يفتح `/auctions/:id`.
    final catalog = browsableCatalog();

    await pumpApp(tester, catalog: catalog, location: '/auctions/a-7');
    await tester.pumpAndSettle();

    expect(find.byType(AuctionVehiclesScreen), findsOneWidget);
    expect(catalog.receivedAuctionIds.single, 'a-7');

    await tester.tap(find.byType(VehicleCard));
    await tester.pumpAndSettle();

    expect(find.byType(VehicleScreen), findsOneWidget);
  });
}
