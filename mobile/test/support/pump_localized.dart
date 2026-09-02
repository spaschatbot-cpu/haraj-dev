import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
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
