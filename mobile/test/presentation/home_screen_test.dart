import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:haraj_mobile/data/api/api_failure_mapper.dart';
import 'package:haraj_mobile/domain/catalog/entities/auction_summary.dart';
import 'package:haraj_mobile/domain/common/failure.dart';
import 'package:haraj_mobile/domain/common/snapshot.dart';
import 'package:haraj_mobile/l10n/generated/app_localizations.dart';
import 'package:haraj_mobile/presentation/catalog/home_screen.dart';
import 'package:haraj_mobile/presentation/catalog/widgets/auction_card.dart';
import 'package:haraj_mobile/presentation/common/failure_view.dart';
import 'package:haraj_mobile/presentation/common/saudi_time.dart';
import 'package:haraj_mobile/presentation/common/stale_data_banner.dart';

import '../support/catalog_fakes.dart';
import '../support/pump_screen.dart';

/// T707 — الرئيسية: المزادات الجارية والقادمة، بعدّاد تنازلي بالتوقيت السعودي.
void main() {
  late AppLocalizations ar;

  setUp(() async {
    ar = await AppLocalizations.delegate.load(const Locale('ar'));
  });

  testWidgets('القسمان يظهران بعناوينهما كما ردّ بهما الخادم', (tester) async {
    final catalog = FakeCatalogRepository(
      home: fresh(
        HomeAuctions(
          running: <AuctionSummary>[auctionSummary(id: 'a-1', title: 'Live')],
          upcoming: <AuctionSummary>[auctionSummary(id: 'a-2', title: 'Soon')],
        ),
      ),
    );

    await pumpScreen(tester, const HomeScreen(), catalog: catalog);
    await tester.pumpAndSettle();

    expect(find.text(ar.homeRunningSection), findsOneWidget);
    expect(find.text(ar.homeUpcomingSection), findsOneWidget);
    expect(find.byType(AuctionCard), findsNWidgets(2));
  });

  testWidgets('العدّاد يعبر تغيّر اليوم بلا قفزة', (tester) async {
    // ٢٣:٥٠ بتوقيت السعودية، ومزاد يبدأ ٠٠:٣٠ من الغد بالتوقيت نفسه.
    final now = DateTime.utc(2026, 9, 3, 20, 50);
    final startsAt = DateTime.utc(2026, 9, 3, 21, 30);

    final catalog = FakeCatalogRepository(
      home: fresh(
        HomeAuctions(
          running: const <AuctionSummary>[],
          upcoming: <AuctionSummary>[
            auctionSummary(
              startsAt: startsAt,
              endsAt: startsAt.add(const Duration(hours: 6)),
            ),
          ],
        ),
      ),
    );

    await pumpScreen(tester, const HomeScreen(), catalog: catalog, now: now);
    await tester.pumpAndSettle();

    expect(
      find.text(ar.countdownToStart(ar.countdownMinutes(40))),
      findsOneWidget,
    );

    // ويوم البداية يُعرض باليوم السعودي — الرابع، لا الثالث الذي في UTC.
    final saudiStart = SaudiTime.forDisplay(startsAt);
    expect(saudiStart.day, 4);
    expect(
      find.text(ar.auctionStartsAt(saudiStart, saudiStart)),
      findsOneWidget,
    );
  });

  testWidgets('المزاد الجاري يعدّ إلى نهايته لا إلى بدايته', (tester) async {
    final catalog = FakeCatalogRepository(
      home: fresh(
        HomeAuctions(
          running: <AuctionSummary>[
            auctionSummary(
              startsAt: fixedNowUtc.subtract(const Duration(hours: 2)),
              endsAt: fixedNowUtc.add(const Duration(hours: 3)),
            ),
          ],
          upcoming: const <AuctionSummary>[],
        ),
      ),
    );

    await pumpScreen(tester, const HomeScreen(), catalog: catalog);
    await tester.pumpAndSettle();

    expect(
      find.text(ar.countdownToEnd(ar.countdownHoursMinutes(3, 0))),
      findsOneWidget,
    );
  });

  testWidgets('لا مزادات: حالة فارغة مكتوبة لا شاشة بيضاء', (tester) async {
    final catalog = FakeCatalogRepository(
      home: fresh(
        const HomeAuctions(
          running: <AuctionSummary>[],
          upcoming: <AuctionSummary>[],
        ),
      ),
    );

    await pumpScreen(tester, const HomeScreen(), catalog: catalog);
    await tester.pumpAndSettle();

    expect(find.text(ar.homeEmpty), findsOneWidget);
  });

  testWidgets('فشل الخادم يعرض رسالته العربية كما جاءت', (tester) async {
    final catalog = FakeCatalogRepository(
      homeError: ApiFailureMapper.fromDioException(
        DioException(
          requestOptions: RequestOptions(path: '/api/v1/auctions'),
          type: DioExceptionType.badResponse,
          response: Response<Object?>(
            requestOptions: RequestOptions(path: '/api/v1/auctions'),
            statusCode: 403,
            data: <String, Object?>{
              'error': <String, Object?>{
                'code': 'FORBIDDEN',
                'message': 'حسابك غير مفعّل لتصفّح المزادات.',
              },
            },
          ),
        ),
      ),
    );

    await pumpScreen(tester, const HomeScreen(), catalog: catalog);
    await tester.pumpAndSettle();

    expect(find.byType(FailureView), findsOneWidget);
    expect(find.text('حسابك غير مفعّل لتصفّح المزادات.'), findsOneWidget);
  });

  testWidgets('انقطاع الشبكة: بيانات محفوظة بعلامة «آخر تحديث»', (
    tester,
  ) async {
    final catalog = FakeCatalogRepository(
      home: Snapshot<HomeAuctions>.cached(
        HomeAuctions(
          running: <AuctionSummary>[auctionSummary()],
          upcoming: const <AuctionSummary>[],
        ),
        storedAt: fixedNowUtc,
      ),
    );

    await pumpScreen(tester, const HomeScreen(), catalog: catalog);
    await tester.pumpAndSettle();

    // H5: آخر بيانات معروفة **مع علامة**، لا شاشة خطأ.
    expect(find.byType(StaleDataBanner), findsOneWidget);
    expect(find.byType(AuctionCard), findsOneWidget);
    expect(find.byType(FailureView), findsNothing);
  });

  testWidgets('إعادة المحاولة تسأل الخادم من جديد', (tester) async {
    final catalog = FakeCatalogRepository(
      homeError: const TransportFailure(TransportProblem.offline),
    );

    await pumpScreen(tester, const HomeScreen(), catalog: catalog);
    await tester.pumpAndSettle();
    expect(catalog.homeCalls, 1);

    await tester.tap(find.text(ar.retry));
    await tester.pumpAndSettle();

    expect(catalog.homeCalls, 2);
  });
}
