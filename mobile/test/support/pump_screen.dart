import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:haraj_mobile/app/providers.dart';
import 'package:haraj_mobile/l10n/generated/app_localizations.dart';

import 'catalog_fakes.dart';

/// مقاس جوال، لا مقاس سطح المكتب الافتراضي في الاختبارات.
///
/// معيار القبول في الفيز 008 ينصّ على اختبار **على مقاس جوال**: شاشةٌ تُختبَر
/// على 800×600 وتُشحن إلى 390×844 تُختبَر بعرضٍ لا يراه أحد، وأول ما يظهر عند
/// المستخدم هو ما لم يُقَس — تجاوز عمودي أو صفٌّ انكسر.
void usePhoneSurface(WidgetTester tester) {
  tester.view
    ..physicalSize = const Size(1170, 2532)
    ..devicePixelRatio = 3;
  addTearDown(tester.view.reset);
}

/// يبني شاشة داخل نفس إعداد الترجمة الذي يستعمله التطبيق، بوقتٍ ثابت وعلى
/// مقاس جوال.
///
/// **الوقت الثابت ليس تفصيلاً:** العدّاد التنازلي في الرئيسية ينبض كل ثانية،
/// و`pumpAndSettle` مع مؤقّت دوري لا تستقرّ أبداً. إطفاء النبض هنا (لا في كل
/// اختبار) يجعل السبب مكتوباً مرة واحدة بدل أن يُكتشف بمهلةٍ غامضة.
Future<void> pumpScreen(
  WidgetTester tester,
  Widget screen, {
  required FakeCatalogRepository catalog,
  DateTime? now,
  Locale locale = const Locale('ar'),
}) {
  usePhoneSurface(tester);
  return tester.pumpWidget(
    ProviderScope(
      overrides: [
        catalogRepositoryProvider.overrideWithValue(catalog),
        nowProvider.overrideWithValue(() => now ?? fixedNowUtc),
        countdownTickProvider.overrideWithValue(null),
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
