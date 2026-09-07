import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
// `Override` ليس في المدخل الرئيسي للحزمة — استبدال مزوّد في الاختبار يعيش في
// `misc.dart` عمداً كي لا يُستعمل في شيفرة الإنتاج.
import 'package:flutter_riverpod/misc.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:haraj_mobile/app/providers.dart';
import 'package:haraj_mobile/l10n/generated/app_localizations.dart';

import 'catalog_fakes.dart';

/// مقاس جوال، لا مقاس سطح المكتب الافتراضي في الاختبارات.
///
/// معيار القبول في الفيز 008 ينصّ على اختبار **على مقاس جوال**: شاشةٌ تُختبَر
/// على 800×600 وتُشحن إلى 390×844 تُختبَر بعرضٍ لا يراه أحد، وأول ما يظهر عند
/// المستخدم هو ما لم يُقَس — تجاوز عمودي أو صفٌّ انكسر.
void usePhoneSurface(WidgetTester tester, {Size size = const Size(390, 844)}) {
  tester.view
    ..physicalSize = size * tester.view.devicePixelRatio
    ..devicePixelRatio = tester.view.devicePixelRatio;
  addTearDown(tester.view.reset);
}

/// يبني شاشة داخل نفس إعداد الترجمة والحجم اللذين تُشحن بهما، بوقتٍ ثابت.
///
/// **الوقت الثابت ليس تفصيلاً:** العدّاد التنازلي في الرئيسية ينبض كل ثانية،
/// و`pumpAndSettle` مع مؤقّت دوري لا تستقرّ أبداً. إطفاء النبض هنا (لا في كل
/// اختبار) يجعل السبب مكتوباً مرة واحدة بدل أن يُكتشف بمهلةٍ غامضة.
///
/// [catalog] لمن كان موضوعه التصفّح، و[overrides] لكل استبدال آخر. ما يمرّره
/// الاختبار يعلو على الافتراضي.
Future<void> pumpScreen(
  WidgetTester tester,
  Widget screen, {
  FakeCatalogRepository? catalog,
  List<Override> overrides = const <Override>[],
  DateTime? now,
  Locale locale = const Locale('ar'),
  Size size = const Size(390, 844),
}) async {
  usePhoneSurface(tester, size: size);

  await tester.pumpWidget(
    ProviderScope(
      overrides: <Override>[
        if (catalog != null)
          catalogRepositoryProvider.overrideWithValue(catalog),
        nowProvider.overrideWithValue(() => now ?? fixedNowUtc),
        countdownTickProvider.overrideWithValue(null),
        ...overrides,
      ],
      child: MaterialApp(
        locale: locale,
        localizationsDelegates: AppLocalizations.localizationsDelegates,
        supportedLocales: AppLocalizations.supportedLocales,
        home: screen,
      ),
    ),
  );
}
