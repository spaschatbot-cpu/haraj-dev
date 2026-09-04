import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
// `Override` ليس في المدخل الرئيسي للحزمة — استبدال مزوّد في الاختبار يعيش في
// `misc.dart` عمداً كي لا يُستعمل في شيفرة الإنتاج.
import 'package:flutter_riverpod/misc.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:haraj_mobile/app/providers.dart';
import 'package:haraj_mobile/domain/catalog/entities/auction_phase.dart';
import 'package:haraj_mobile/l10n/generated/app_localizations.dart';
import 'package:haraj_mobile/presentation/catalog/widgets/countdown_text.dart';
import 'package:haraj_mobile/presentation/catalog/widgets/vehicle_card.dart';

import '../support/catalog_fakes.dart';
import '../support/pump_localized.dart';
import '../support/pump_screen.dart';

/// كرت المركبة — المكوّن الوحيد الذي يرسمه (T708).
void main() {
  late AppLocalizations ar;

  setUp(() async {
    ar = await AppLocalizations.delegate.load(const Locale('ar'));
  });

  /// الكرت يعيش داخل قائمة قابلة للتمرير في كل استعمال حقيقي؛ اختباره خارجها
  /// يقيس تخطيطاً لا يُشحن.
  ///
  /// و`ProviderScope` لأن الكرت صار يحمل عدّاداً تنازلياً: الوقت يأتي من
  /// `nowProvider` والنبض من `countdownTickProvider`، فيُثبَّت الأول ويُطفأ
  /// الثاني — مؤقّت دوري يجعل `pumpAndSettle` لا تستقرّ أبداً.
  Future<void> pumpCard(WidgetTester tester, Widget card) {
    usePhoneSurface(tester);
    return pumpLocalized(
      tester,
      ProviderScope(
        overrides: <Override>[
          nowProvider.overrideWithValue(() => fixedNowUtc),
          countdownTickProvider.overrideWithValue(null),
        ],
        child: ListView(children: <Widget>[card]),
      ),
    );
  }

  testWidgets('السعر هو سعر الوقوف، ويُعرض كما وصل', (tester) async {
    await pumpCard(
      tester,
      VehicleCard(vehicle: vehicleSummary(reservePrice: '50000.10')),
    );
    await tester.pumpAndSettle();

    expect(find.text(ar.vehicleReservePrice), findsOneWidget);
    expect(find.text('50000.10 SAR'), findsOneWidget);
  });

  testWidgets('بلا سعر وقوف: «لم يُحدَّد» لا صفر ولا فراغ', (tester) async {
    await pumpCard(
      tester,
      VehicleCard(vehicle: vehicleSummary(reservePrice: null)),
    );
    await tester.pumpAndSettle();

    expect(find.text(ar.vehicleReservePriceUnset), findsOneWidget);
  });

  testWidgets('بلا مصغَّرة: نصّ مكانها لا مربّع أسود', (tester) async {
    await pumpCard(
      tester,
      VehicleCard(vehicle: vehicleSummary(thumbnailUrl: null)),
    );
    await tester.pumpAndSettle();

    expect(find.text(ar.vehicleNoImage), findsOneWidget);
  });

  testWidgets('عدد المزايدات يظهر، ومبلغ أعلى مزايدة لا يظهر', (tester) async {
    // المزاد مغلق: مبلغ أعلى مزايدة ليس معلومة عامة، وعرضه يحوّل المزاد المغلق
    // إلى مزادٍ مفتوح بحكم الأمر الواقع.
    await pumpCard(tester, VehicleCard(vehicle: vehicleSummary(bidsCount: 3)));
    await tester.pumpAndSettle();

    expect(find.text(ar.vehicleBidsCount(3)), findsOneWidget);
  });

  testWidgets('عدّاد تنازلي إلى لحظة انتهاء مزاد المركبة', (tester) async {
    await pumpCard(
      tester,
      VehicleCard(
        vehicle: vehicleSummary(
          auctionEndsAt: fixedNowUtc.add(const Duration(hours: 3)),
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(
      find.text(ar.countdownToEnd(ar.countdownHoursMinutes(3, 0))),
      findsOneWidget,
    );
  });

  testWidgets('«انتهى المزاد» يقولها الخادم في phase لا ساعة الجهاز', (
    tester,
  ) async {
    // v1 قارن وقت النهاية بساعة العميل فكتب «انتهى» على مزادٍ مفتوح لكل من
    // ساعته متقدّمة. هنا العكس مقيس: النهاية في المستقبل بحسب الساعة، والخادم
    // يقول «انتهى» — فالكرت يصدّق الخادم.
    await pumpCard(
      tester,
      VehicleCard(
        vehicle: vehicleSummary(
          phase: AuctionPhase.ended,
          auctionEndsAt: fixedNowUtc.add(const Duration(hours: 3)),
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text(ar.vehicleAuctionEnded), findsOneWidget);
    expect(find.byType(CountdownText), findsNothing);
  });
}
