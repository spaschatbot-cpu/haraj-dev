import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:haraj_mobile/data/api/api_failure_mapper.dart';
import 'package:haraj_mobile/domain/catalog/entities/auction_phase.dart';
import 'package:haraj_mobile/domain/catalog/entities/vehicle_feed.dart';
import 'package:haraj_mobile/domain/catalog/entities/vehicle_summary.dart';
import 'package:haraj_mobile/domain/common/failure.dart';
import 'package:haraj_mobile/domain/common/snapshot.dart';
import 'package:haraj_mobile/l10n/generated/app_localizations.dart';
import 'package:haraj_mobile/presentation/catalog/home_screen.dart';
import 'package:haraj_mobile/presentation/catalog/widgets/countdown_text.dart';
import 'package:haraj_mobile/presentation/catalog/widgets/vehicle_card.dart';
import 'package:haraj_mobile/presentation/common/failure_view.dart';
import 'package:haraj_mobile/presentation/common/stale_data_banner.dart';

import '../support/catalog_fakes.dart';
import '../support/pump_screen.dart';

/// الرئيسية بعد التبويبات: شبكة مركبات مسطّحة عبر المزادات، وتبويبٌ بطور
/// المزاد بعدّادٍ لكل تبويب — كلاهما من الخادم.
void main() {
  late AppLocalizations ar;

  setUp(() async {
    ar = await AppLocalizations.delegate.load(const Locale('ar'));
  });

  FakeCatalogRepository catalogWith(VehicleFeed feed) => FakeCatalogRepository(
    feedPages: <int, Snapshot<VehicleFeed>>{1: fresh(feed)},
  );

  testWidgets('التبويبات الثلاثة تظهر بعدّاداتها كما ردّ بها الخادم', (
    tester,
  ) async {
    final catalog = catalogWith(
      vehicleFeed(
        vehicles: <VehicleSummary>[vehicleSummary(id: 'v-1')],
        totalCount: 9,
        counts: phaseCounts(upcoming: 4, active: 9, ended: 31),
      ),
    );

    await pumpScreen(tester, const HomeScreen(), catalog: catalog);
    await tester.pumpAndSettle();

    expect(
      find.text(ar.homeTabWithCount(ar.homeTabUpcoming, 4)),
      findsOneWidget,
    );
    expect(find.text(ar.homeTabWithCount(ar.homeTabActive, 9)), findsOneWidget);
    expect(find.text(ar.homeTabWithCount(ar.homeTabEnded, 31)), findsOneWidget);
  });

  testWidgets('العدّادات من الخادم لا من طول القائمة المعروضة', (tester) async {
    // مركبةٌ واحدة وصلت، والعدّاد يقول تسعاً: الفرق بين «كم وصلني» و«كم هناك».
    final catalog = catalogWith(
      vehicleFeed(
        vehicles: <VehicleSummary>[vehicleSummary(id: 'v-1')],
        totalCount: 9,
        counts: phaseCounts(upcoming: 4, active: 9, ended: 31),
      ),
    );

    await pumpScreen(tester, const HomeScreen(), catalog: catalog);
    await tester.pumpAndSettle();

    expect(find.byType(VehicleCard), findsOneWidget);
    expect(find.text(ar.homeTabWithCount(ar.homeTabActive, 9)), findsOneWidget);
    expect(find.text(ar.vehiclesResultsCount(9)), findsOneWidget);
  });

  testWidgets('طلب واحد يجيب الشبكة والعدّادات معاً', (tester) async {
    final catalog = catalogWith(
      vehicleFeed(vehicles: <VehicleSummary>[vehicleSummary()]),
    );

    await pumpScreen(tester, const HomeScreen(), catalog: catalog);
    await tester.pumpAndSettle();

    expect(catalog.receivedFeedQueries, hasLength(1));
  });

  testWidgets('التبويب المفتوح يذهب إلى الخادم كما هو', (tester) async {
    final catalog = catalogWith(vehicleFeed());

    await pumpScreen(
      tester,
      const HomeScreen(phase: AuctionPhase.ended),
      catalog: catalog,
    );
    await tester.pumpAndSettle();

    expect(catalog.receivedFeedQueries.single.phase, AuctionPhase.ended);
  });

  testWidgets('العدّاد التنازلي على الكرت إلى لحظة انتهاء مزاده', (
    tester,
  ) async {
    final catalog = catalogWith(
      vehicleFeed(
        vehicles: <VehicleSummary>[
          vehicleSummary(
            auctionEndsAt: fixedNowUtc.add(const Duration(hours: 3)),
          ),
        ],
      ),
    );

    await pumpScreen(tester, const HomeScreen(), catalog: catalog);
    await tester.pumpAndSettle();

    expect(find.byType(CountdownText), findsOneWidget);
    expect(
      find.text(ar.countdownToEnd(ar.countdownHoursMinutes(3, 0))),
      findsOneWidget,
    );
  });

  testWidgets('«منتهي» من الخادم لا من ساعة الجهاز', (tester) async {
    // مزادٌ قال عنه الخادم «انتهى» ونهايته في المستقبل بحسب ساعة الجهاز:
    // الكرت يصدّق الخادم. هذه بعينها علّة v1 معكوسةً — هناك صدّق الساعة.
    final catalog = catalogWith(
      vehicleFeed(
        vehicles: <VehicleSummary>[
          vehicleSummary(
            phase: AuctionPhase.ended,
            auctionEndsAt: fixedNowUtc.add(const Duration(hours: 3)),
          ),
        ],
      ),
    );

    await pumpScreen(
      tester,
      const HomeScreen(phase: AuctionPhase.ended),
      catalog: catalog,
    );
    await tester.pumpAndSettle();

    expect(find.text(ar.vehicleAuctionEnded), findsOneWidget);
    expect(find.byType(CountdownText), findsNothing);
  });

  testWidgets('طورٌ لا نعرفه لا يُقال عنه «منتهي»', (tester) async {
    // المادة ٢-٣: قيمة لم نرها من قبل تُعرض ولا تُسقط الاستجابة، والجهل ليس
    // نفياً — مركبةٌ بطورٍ مجهول تُعامَل معاملة القائمة لا المنتهية.
    final catalog = catalogWith(
      vehicleFeed(
        vehicles: <VehicleSummary>[vehicleSummary(phase: AuctionPhase.unknown)],
      ),
    );

    await pumpScreen(tester, const HomeScreen(), catalog: catalog);
    await tester.pumpAndSettle();

    expect(find.text(ar.vehicleAuctionEnded), findsNothing);
    expect(find.byType(CountdownText), findsOneWidget);
  });

  testWidgets('التبويب الفارغ يقول لماذا هو فارغ، لكل تبويب سببه', (
    tester,
  ) async {
    for (final (phase, message) in <(AuctionPhase, String)>[
      (AuctionPhase.upcoming, ar.homeEmptyUpcoming),
      (AuctionPhase.active, ar.homeEmptyActive),
      (AuctionPhase.ended, ar.homeEmptyEnded),
    ]) {
      await pumpScreen(
        tester,
        HomeScreen(phase: phase),
        catalog: catalogWith(vehicleFeed()),
      );
      await tester.pumpAndSettle();

      expect(
        find.text(message),
        findsOneWidget,
        reason: 'التبويب ${phase.slug}',
      );
    }
  });

  testWidgets('بحثٌ بلا نتائج يقول «لا مطابق» لا «لا مزاد»', (tester) async {
    // فراغُ بحثٍ غير فراغِ تبويب: «لا مزاد نشط» أمام من بحث عن لكزس تقول له
    // إن المزاد مقفل وهو مفتوح.
    final catalog = catalogWith(vehicleFeed());

    await pumpScreen(tester, const HomeScreen(), catalog: catalog);
    await tester.pumpAndSettle();

    await tester.enterText(find.byType(TextField).first, 'lexus');
    await tester.tap(find.text(ar.filterApply));
    await tester.pumpAndSettle();

    expect(find.text(ar.vehiclesEmpty), findsOneWidget);
    expect(find.text(ar.homeEmptyActive), findsNothing);
    expect(catalog.receivedFeedQueries.last.search, 'lexus');
    // والتبويب يبقى تبويبه: البحث يضيّق داخل التبويب ولا ينقل منه.
    expect(catalog.receivedFeedQueries.last.phase, AuctionPhase.active);
  });

  testWidgets('فشل الخادم يعرض رسالته العربية كما جاءت', (tester) async {
    final catalog = FakeCatalogRepository(
      feedError: ApiFailureMapper.fromDioException(
        DioException(
          requestOptions: RequestOptions(path: '/api/v1/vehicles/'),
          type: DioExceptionType.badResponse,
          response: Response<Object?>(
            requestOptions: RequestOptions(path: '/api/v1/vehicles/'),
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

  testWidgets('انقطاع الشبكة: تبويب محفوظ بعدّاداته وبعلامة «آخر تحديث»', (
    tester,
  ) async {
    final catalog = FakeCatalogRepository(
      feedPages: <int, Snapshot<VehicleFeed>>{
        1: Snapshot<VehicleFeed>.cached(
          vehicleFeed(
            vehicles: <VehicleSummary>[vehicleSummary()],
            counts: phaseCounts(upcoming: 4, active: 9, ended: 31),
          ),
          storedAt: fixedNowUtc,
        ),
      },
    );

    await pumpScreen(tester, const HomeScreen(), catalog: catalog);
    await tester.pumpAndSettle();

    // H5: آخر ما نعرف **مع علامة**، لا شبكة بيضاء ولا شاشة خطأ.
    expect(find.byType(StaleDataBanner), findsOneWidget);
    expect(find.byType(VehicleCard), findsOneWidget);
    expect(find.text(ar.homeTabWithCount(ar.homeTabActive, 9)), findsOneWidget);
    expect(find.byType(FailureView), findsNothing);
  });

  testWidgets('إعادة المحاولة تسأل الخادم من جديد', (tester) async {
    final catalog = FakeCatalogRepository(
      feedError: const TransportFailure(TransportProblem.offline),
    );

    await pumpScreen(tester, const HomeScreen(), catalog: catalog);
    await tester.pumpAndSettle();
    expect(catalog.receivedFeedQueries, hasLength(1));

    await tester.tap(find.text(ar.retry));
    await tester.pumpAndSettle();

    expect(catalog.receivedFeedQueries, hasLength(2));
  });

  testWidgets('الشبكة تتّسع على مقاس جوال بلا تجاوز تخطيط', (tester) async {
    // خليّة شبكةٍ بارتفاع ثابت تقصّ ما لا يتّسع، والقصّ يقع أولاً على آخر سطر
    // في الكرت — وهو العدّاد، ثم السعر. يُقاس على أضيق ما نشحن إليه.
    final catalog = catalogWith(
      vehicleFeed(
        vehicles: <VehicleSummary>[
          for (var index = 0; index < 6; index++)
            vehicleSummary(
              id: 'v-$index',
              title: 'تويوتا كامري جراند ٢٠٢١ فل كامل بصمة',
            ),
        ],
        totalCount: 6,
      ),
    );

    await pumpScreen(
      tester,
      const HomeScreen(),
      catalog: catalog,
      size: const Size(320, 640),
    );
    await tester.pumpAndSettle();

    expect(tester.takeException(), isNull);
    expect(find.byType(VehicleCard), findsWidgets);
  });
}
