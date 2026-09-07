import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:haraj_mobile/domain/catalog/entities/vehicle_detail.dart';
import 'package:haraj_mobile/domain/common/failure.dart';
import 'package:haraj_mobile/l10n/generated/app_localizations.dart';
import 'package:haraj_mobile/presentation/catalog/vehicle_screen.dart';
import 'package:haraj_mobile/presentation/common/failure_view.dart';

import '../support/catalog_fakes.dart';
import '../support/pump_screen.dart';

/// T709 — صفحة المركبة. معيار القبول: اختبار widget يغطّي **بلا صور**،
/// و**بمواصفات ناقصة**، و**مزاد منتهٍ**.
void main() {
  late AppLocalizations ar;

  setUp(() async {
    ar = await AppLocalizations.delegate.load(const Locale('ar'));
  });

  testWidgets('السعر المعروض هو سعر الوقوف كما وصل نصّاً', (tester) async {
    final catalog = FakeCatalogRepository(
      vehicle: fresh(vehicleDetail(reservePrice: '50000.10')),
    );

    await pumpScreen(
      tester,
      const VehicleScreen(vehicleId: 'v-1'),
      catalog: catalog,
    );
    await tester.pumpAndSettle();

    expect(find.text(ar.vehicleReservePrice), findsOneWidget);
    // بلا فواصل آلاف وبلا تقريب: `50000.10` كما أرسلها الخادم (المادة ١-٦).
    expect(find.text('50000.10 SAR'), findsOneWidget);
  });

  testWidgets('مركبة بلا سعر وقوف تقول ذلك ولا تعرض صفراً', (tester) async {
    final catalog = FakeCatalogRepository(
      vehicle: fresh(vehicleDetail(reservePrice: null)),
    );

    await pumpScreen(
      tester,
      const VehicleScreen(vehicleId: 'v-1'),
      catalog: catalog,
    );
    await tester.pumpAndSettle();

    expect(find.text(ar.vehicleReservePriceUnset), findsOneWidget);
    expect(find.textContaining('0.00'), findsNothing);
  });

  testWidgets('بلا صور: نصّ يقول ذلك، لا مربّع فارغ ولا شاشة خطأ', (
    tester,
  ) async {
    final catalog = FakeCatalogRepository(
      vehicle: fresh(vehicleDetail(imageUrls: const <String>[])),
    );

    await pumpScreen(
      tester,
      const VehicleScreen(vehicleId: 'v-1'),
      catalog: catalog,
    );
    await tester.pumpAndSettle();

    expect(find.text(ar.vehicleNoImages), findsOneWidget);
    expect(find.byType(FailureView), findsNothing);
  });

  testWidgets('صورة تسقط تبقى وحدها ساقطة والمركبة تُعرض', (tester) async {
    // عميل HTTP في الاختبار يردّ 400 على كل طلب، فالصورة تفشل فعلاً — وهذا هو
    // السيناريو المقصود: ملفٌ ناقص على التخزين لا يحجب المركبة كلها.
    final catalog = FakeCatalogRepository(
      vehicle: fresh(
        vehicleDetail(
          imageUrls: const <String>['https://example.invalid/1.jpg'],
        ),
      ),
    );

    await pumpScreen(
      tester,
      const VehicleScreen(vehicleId: 'v-1'),
      catalog: catalog,
    );
    await tester.pumpAndSettle();

    expect(find.text(ar.vehicleImageFailed), findsOneWidget);
    expect(find.text('Toyota Camry 2021'), findsWidgets);
    expect(find.byType(FailureView), findsNothing);
  });

  testWidgets('مواصفات ناقصة تُعرض ناقصة ولا تُخترع', (tester) async {
    final catalog = FakeCatalogRepository(
      vehicle: fresh(
        vehicleDetail(specifications: const <VehicleSpecification>[]),
      ),
    );

    await pumpScreen(
      tester,
      const VehicleScreen(vehicleId: 'v-1'),
      catalog: catalog,
    );
    await tester.pumpAndSettle();

    expect(find.text(ar.vehicleNoSpecifications), findsOneWidget);
  });

  testWidgets('تسميات المواصفات تُعرض كما جاءت من الخادم', (tester) async {
    final catalog = FakeCatalogRepository(
      vehicle: fresh(
        vehicleDetail(
          specifications: const <VehicleSpecification>[
            VehicleSpecification(label: 'الممشى', value: '80,000 كم'),
            VehicleSpecification(label: 'ناقل الحركة', value: 'أوتوماتيك'),
          ],
        ),
      ),
    );

    await pumpScreen(
      tester,
      const VehicleScreen(vehicleId: 'v-1'),
      catalog: catalog,
    );
    await tester.pumpAndSettle();

    // لا خريطة أسماء في التطبيق: التسمية العربية من الخادم حرفياً.
    expect(find.text('الممشى'), findsOneWidget);
    expect(find.text('ناقل الحركة'), findsOneWidget);
    expect(find.text('أوتوماتيك'), findsOneWidget);
  });

  testWidgets('مزاد منتهٍ: الخادم يقول إن المزايدة مقفلة والشاشة تعرض قوله', (
    tester,
  ) async {
    final catalog = FakeCatalogRepository(
      vehicle: fresh(vehicleDetail(biddingOpen: false)),
    );

    await pumpScreen(
      tester,
      const VehicleScreen(vehicleId: 'v-1'),
      catalog: catalog,
    );
    await tester.pumpAndSettle();

    expect(find.text(ar.vehicleBiddingClosed), findsOneWidget);
    expect(find.text(ar.vehicleBiddingOpen), findsNothing);
  });

  testWidgets('فشل التحميل يعرض الخطأ بزرّ إعادة محاولة', (tester) async {
    final catalog = FakeCatalogRepository(
      vehicleError: const TransportFailure(TransportProblem.timeout),
    );

    await pumpScreen(
      tester,
      const VehicleScreen(vehicleId: 'v-1'),
      catalog: catalog,
    );
    await tester.pumpAndSettle();

    expect(find.text(ar.errorTimeout), findsOneWidget);
    expect(find.text(ar.retry), findsOneWidget);
  });
}
