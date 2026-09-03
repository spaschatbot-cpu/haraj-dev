import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
// `Override` ليس في المدخل الرئيسي للحزمة — استبدال مزوّد في الاختبار يعيش في
// `misc.dart` عمداً كي لا يُستعمل في شيفرة الإنتاج.
import 'package:flutter_riverpod/misc.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:haraj_mobile/l10n/generated/app_localizations.dart';

/// يبني شاشة داخل نفس إعداد الترجمة والحجم اللذين تُشحن بهما.
///
/// المقاس مقاس جوال متوسط عمداً: شاشة تمرّ على سطح مكتب افتراضي وتنكسر على
/// جوال هي شاشة اختُبرت في مكان غير الذي تعيش فيه.
Future<void> pumpScreen(
  WidgetTester tester,
  Widget screen, {
  List<Override> overrides = const <Override>[],
  Locale locale = const Locale('ar'),
  Size size = const Size(390, 844),
}) async {
  tester.view
    ..physicalSize = size * tester.view.devicePixelRatio
    ..devicePixelRatio = tester.view.devicePixelRatio;
  addTearDown(tester.view.reset);

  await tester.pumpWidget(
    ProviderScope(
      overrides: overrides,
      child: MaterialApp(
        locale: locale,
        localizationsDelegates: AppLocalizations.localizationsDelegates,
        supportedLocales: AppLocalizations.supportedLocales,
        home: screen,
      ),
    ),
  );
}
