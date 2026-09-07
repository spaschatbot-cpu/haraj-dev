import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:haraj_mobile/domain/catalog/entities/vehicle_query.dart';
import 'package:haraj_mobile/domain/catalog/entities/vehicle_summary.dart';
import 'package:haraj_mobile/domain/common/snapshot.dart';
import 'package:haraj_mobile/presentation/catalog/auction_vehicles_screen.dart';
import 'package:haraj_mobile/presentation/catalog/widgets/remote_image.dart';
import 'package:haraj_mobile/presentation/catalog/widgets/vehicle_card.dart';

import '../support/catalog_fakes.dart';
import '../support/pump_screen.dart';

/// H2 — مئتا مركبة لا تُبنى دفعةً واحدة، وما يُبنى منها لا يفكّ صورة كاملة.
///
/// معيار H2 مكتوب قياساً: «٦٠ إطاراً بمئتي مركبة على جهاز متوسط». لا جهاز في
/// هذه البيئة، ولن يوجد في CI؛ فالتاسك عاد إلى 🟡 والقياس بند مفتوح. لكن
/// **الشرطين البنيويين اللذين ينهار المعيار بدونهما يمكن قياسهما هنا**، وبقاؤهما
/// بلا اختبار كان النصف الثاني من الملاحظة: لا شيء يفشل حين يضيف أحدهم عنصراً
/// ثقيلاً إلى `vehicle_card.dart` أو يستبدل القائمة الكسولة بقائمة تركّب الكل.
///
/// ما يُقاس هنا عددٌ ثابت لا زمن: زمنُ بناءٍ على مضيف تطوير مشترك رقمٌ يتقلّب
/// مع حمل الجهاز، واختبارٌ يتقلّب يُطفأ بعد ثالث إنذار كاذب فلا يحرس شيئاً.
/// العدد لا يتقلّب: إمّا القائمة كسولة أو ليست كذلك.
///
/// والعدّ على ما **رُكّب** في الشجرة لا على ما أُنشئ منه widget: قائمةٌ تصنع
/// مئتي كائن خفيف ثم تركّب ثلاثة ليست هي المشكلة، والمشكلة أن تُقاس المئتان
/// وتُرسم وتُفكّ صورها. شوهدت الثلاثة تفشل فعلاً بـ`Column` داخل
/// `SingleChildScrollView` بدل القائمة الكسولة: «رُكّب 200 من 200».
void main() {
  /// العدد الذي يذكره المعيار بعينه. الاختبار الذي يقيس عشرة عناصر يمرّ على
  /// قائمةٍ تبني كل شيء دفعة واحدة.
  const h2VehicleCount = 200;

  /// سقفٌ سخيّ بأضعاف: شاشة 390×844 لا تُظهر أكثر من ثلاثة كروت بنسبة 4:3
  /// وارتفاعها، و`ListView.builder` يبني ما حول النافذة (cacheExtent). فوق هذا
  /// السقف بكثير يعني أن الكسل ذهب، لا أن الحساب اختلف بعنصر.
  const builtCeiling = 20;

  List<VehicleSummary> manyVehicles() => <VehicleSummary>[
    for (var index = 0; index < h2VehicleCount; index++)
      vehicleSummary(
        id: 'v-$index',
        lotNumber: '$index',
        title: 'مركبة $index',
        thumbnailUrl: 'https://example.invalid/$index.jpg',
      ),
  ];

  Future<void> pumpTheList(WidgetTester tester) async {
    final catalog = FakeCatalogRepository(
      vehiclePages: <int, Snapshot<VehiclePage>>{
        1: fresh(
          VehiclePage(
            vehicles: manyVehicles(),
            totalCount: h2VehicleCount,
            hasMore: false,
          ),
        ),
      },
    );

    await pumpScreen(
      tester,
      const AuctionVehiclesScreen(auctionId: 'a-1'),
      catalog: catalog,
    );
    await tester.pumpAndSettle();
  }

  testWidgets('مئتا مركبة لا تبني مئتي كرت — القائمة كسولة', (tester) async {
    await pumpTheList(tester);

    final built = tester
        .widgetList<VehicleCard>(find.byType(VehicleCard))
        .length;

    expect(
      built,
      lessThanOrEqualTo(builtCeiling),
      reason:
          'رُكّب $built كرتاً من $h2VehicleCount عند أول إطار. القائمة كفّت عن '
          'أن تكون كسولة — `Column` داخل `SingleChildScrollView` مثلاً — '
          'فمئتان تُرسَم وتُقاس وتُفكّ صورها كلها قبل أن يرى المستخدم الثالثة.',
    );
    expect(
      built,
      greaterThan(0),
      reason: 'لم يُبنَ شيء — الاختبار يقيس فراغاً',
    );
  });

  testWidgets('ولا تفكّ مئتي صورة بحجمها الأصلي', (tester) async {
    await pumpTheList(tester);

    final images = tester.widgetList<Image>(find.byType(Image)).toList();

    expect(
      images,
      isNotEmpty,
      reason: 'لا صورة في القائمة — الاختبار يقيس فراغاً',
    );
    expect(
      images.length,
      lessThanOrEqualTo(builtCeiling),
      reason: 'عدد الصور المبنية تبع عدد الكروت المبنية، وقد فارقه',
    );
    for (final image in images) {
      // بلا `cacheWidth` تُفكّ الصورة بأبعادها الأصلية في الذاكرة مهما صغر
      // مكانها على الشاشة، ومصغَّرة واحدة بحجم كامل تكلف أضعاف الكرت كله.
      // `cacheWidth` يظهر في الشجرة بوصفه `ResizeImage` حول المزوّد — وهذا ما
      // يُفحص، لا خاصية على الـwidget: الأخيرة أبعادُ العرض لا أبعاد الفكّ.
      expect(
        image.image,
        isA<ResizeImage>(),
        reason: 'مصغَّرة تُفكّ بحجمها الأصلي — راجع `RemoteImage.decodeWidth`',
      );
      expect((image.image as ResizeImage).width, isNotNull);
    }
  });

  testWidgets('التمرير عبر القائمة يبقي المبنيّ محدوداً', (tester) async {
    // الاختبار الأول يقيس أول إطار وحده؛ قائمةٌ تحتفظ بكل ما مرّ عليه تمرّ فيه
    // وتنهار في اليد. هذا يمرّر مسافة طويلة ثم يعيد العدّ.
    await pumpTheList(tester);

    await tester.fling(
      find.byType(VehicleCard).first,
      const Offset(0, -8000),
      2000,
    );
    await tester.pumpAndSettle();

    final built = tester
        .widgetList<VehicleCard>(find.byType(VehicleCard))
        .length;

    expect(
      built,
      lessThanOrEqualTo(builtCeiling),
      reason: 'بعد التمرير بقي $built كرتاً مبنيّاً — الكسل يُفقد بالتمرير',
    );
  });

  testWidgets('ولا تمويه في القائمة — قاعدة التصميم 5', (tester) async {
    // الفحص النصّي في `test/architecture/no_blur_in_lists_test.dart` يمنع كتابة
    // التمويه؛ هذا يثبت غيابه في الشجرة المبنيّة فعلاً، فمرشِّحٌ يأتي من ثيم أو
    // من مكوّن ثالث لا يفلت من الاثنين معاً.
    await pumpTheList(tester);

    expect(find.byType(BackdropFilter), findsNothing);
    expect(find.byType(ImageFiltered), findsNothing);
  });

  testWidgets('كرت المركبة صورة واحدة لا معرض', (tester) async {
    // انحدارُ H2 الأرجح ليس القائمة بل الكرت: صورتان في كل كرت تضاعفان كل شيء
    // فوق. `RemoteImage` واحد لكل كرت، ومن أراد أكثر يغيّر هذا الرقم عامداً.
    await pumpTheList(tester);

    final cards = find.byType(VehicleCard).evaluate().length;
    final thumbnails = find.byType(RemoteImage).evaluate().length;

    expect(thumbnails, cards, reason: 'صورة واحدة لكل كرت، لا أكثر');
  });
}
