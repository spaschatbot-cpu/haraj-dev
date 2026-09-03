import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
// `Override` يسكن في مدخل `misc` من riverpod 3، لا في المدخل الرئيسي.
import 'package:flutter_riverpod/misc.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:haraj_mobile/app/haraj_app.dart';
import 'package:haraj_mobile/app/router.dart';

/// يشغّل التطبيق كاملاً — بموجّهه وترجمته وثيمه — على **مقاس جوال**.
///
/// التطبيق كاملاً لا الشاشة وحدها: نصف ما تختبره هذه الشاشات هو إعادة التوجيه
/// (سقوط الجلسة، شاشة رمز بلا رمز)، وشاشةٌ مركَّبة وحدها لا موجِّه لها تمرّ
/// بينما التطبيق يتعطّل.
///
/// والمقاس جوال لأن هذه شاشات جوال: مقاس سطح المكتب الافتراضي في الاختبارات
/// يخفي كل تجاوز تخطيط يقع عند 390 عرضاً (قاعدة الشاشات 5 في تعليمات الفيز).
Future<ProviderContainer> pumpApp(
  WidgetTester tester, {
  List<Override> overrides = const <Override>[],
  String location = '/',
}) async {
  tester.view
    ..physicalSize = const Size(390 * 3, 844 * 3)
    ..devicePixelRatio = 3;
  addTearDown(tester.view.reset);

  final container = ProviderContainer(overrides: overrides);
  addTearDown(container.dispose);

  await tester.pumpWidget(
    UncontrolledProviderScope(container: container, child: const HarajApp()),
  );
  await tester.pumpAndSettle();

  if (location != '/') {
    container.read(routerProvider).go(location);
    await tester.pumpAndSettle();
  }

  return container;
}

/// المسار المعروض الآن — يُقرأ للتحقّق من إعادة التوجيه.
String currentLocation(ProviderContainer container) => container
    .read(routerProvider)
    .routerDelegate
    .currentConfiguration
    .uri
    .toString();
