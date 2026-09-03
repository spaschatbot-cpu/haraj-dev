import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
// `Override` ليس في التصدير الافتراضي لـflutter_riverpod 3، وهو نوع معاملات
// `ProviderScope.overrides` — فيُستورد من `misc.dart` الذي يصدّره.
import 'package:flutter_riverpod/misc.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:haraj_mobile/app/router.dart';
import 'package:haraj_mobile/l10n/generated/app_localizations.dart';

/// يبني widget داخل نفس إعداد الترجمة الذي يستعمله التطبيق.
///
/// وجوده يمنع اختبارات تمرّ بإعداد مختلف عن الإنتاج — أشهر طريقة لاختبار
/// شيء غير الذي يُشحن.
Future<void> pumpLocalized(
  WidgetTester tester,
  Widget child, {
  Locale locale = const Locale('ar'),
}) => tester.pumpWidget(
  MaterialApp(
    locale: locale,
    localizationsDelegates: AppLocalizations.localizationsDelegates,
    supportedLocales: AppLocalizations.supportedLocales,
    home: Scaffold(body: child),
  ),
);

/// يفتح شاشةً **من مسارها الحقيقي** بموجّه التطبيق نفسه.
///
/// لا نسخة اختبار من شجرة المسارات: نسخة ثانية تفترق عن `appRoutes()` فيمرّ
/// الاختبار على شاشة ببنية لا تُشحن (T712 وما بعدها تُفتح من روابط داخلية).
Future<void> pumpRoute(
  WidgetTester tester,
  String location, {
  List<Override> overrides = const <Override>[],
  Locale locale = const Locale('ar'),
}) => tester.pumpWidget(
  ProviderScope(
    overrides: overrides,
    child: MaterialApp.router(
      locale: locale,
      localizationsDelegates: AppLocalizations.localizationsDelegates,
      supportedLocales: AppLocalizations.supportedLocales,
      routerConfig: buildRouter(initialLocation: location),
    ),
  ),
);
