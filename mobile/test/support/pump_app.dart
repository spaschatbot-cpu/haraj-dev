import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
// `Override` يسكن في مدخل `misc` من riverpod 3، لا في المدخل الرئيسي.
import 'package:flutter_riverpod/misc.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:haraj_mobile/app/haraj_app.dart';
import 'package:haraj_mobile/app/providers.dart';
import 'package:haraj_mobile/app/router.dart';

import 'catalog_fakes.dart';
import 'pump_screen.dart';

/// يشغّل التطبيق كاملاً — بموجّهه وترجمته وثيمه ولافتة بيئته — على **مقاس جوال**.
///
/// التطبيق كاملاً لا الشاشة وحدها: نصف ما تختبره هذه الشاشات هو إعادة التوجيه
/// (سقوط الجلسة، شاشة رمز بلا رمز)، وشاشةٌ مركَّبة وحدها لا موجِّه لها تمرّ
/// بينما التطبيق يتعطّل.
///
/// والمقاس جوال لأن هذه شاشات جوال: مقاس سطح المكتب الافتراضي في الاختبارات
/// يخفي كل تجاوز تخطيط يقع عند 390 عرضاً (قاعدة الشاشات 5 في تعليمات الفيز).
///
/// **لماذا يُزيَّف مستودع التصفّح دائماً:** جذر التطبيق صار الرئيسية (T707)، وهي
/// تسأل المستودع أول ما تُبنى. اختبارُ دخولٍ أو ملفٍ شخصي لا يعني التصفّح في شيء
/// لكنه يمرّ بالجذر، فبلا تزييفٍ افتراضي يتحدّث كل اختبارِ توجيهٍ إلى الشبكة.
/// وإطفاء نبض العدّاد لنفس السبب الذي في `pumpScreen`: مؤقّت دوري يجعل
/// `pumpAndSettle` لا تستقرّ أبداً.
Future<ProviderContainer> pumpApp(
  WidgetTester tester, {
  List<Override> overrides = const <Override>[],
  String location = '/',
  FakeCatalogRepository? catalog,
  Locale locale = const Locale('ar'),
}) async {
  usePhoneSurface(tester);

  final container = ProviderContainer(
    overrides: <Override>[
      catalogRepositoryProvider.overrideWithValue(
        catalog ?? emptyCatalogRepository(),
      ),
      nowProvider.overrideWithValue(() => fixedNowUtc),
      countdownTickProvider.overrideWithValue(null),
      // ما يمرّره الاختبار بعينه يعلو على الافتراضي أعلاه.
      ...overrides,
    ],
  );
  addTearDown(container.dispose);

  await tester.pumpWidget(
    UncontrolledProviderScope(
      container: container,
      child: HarajApp(locale: locale),
    ),
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
