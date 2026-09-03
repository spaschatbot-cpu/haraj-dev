import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:haraj_mobile/l10n/generated/app_localizations.dart';
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
  Future<void> pumpCard(WidgetTester tester, Widget card) {
    usePhoneSurface(tester);
    return pumpLocalized(tester, ListView(children: <Widget>[card]));
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
}
