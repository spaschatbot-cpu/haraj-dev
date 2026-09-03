import 'package:flutter/widgets.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:haraj_mobile/app/haraj_app.dart';
import 'package:haraj_mobile/app/providers.dart';

import 'catalog_fakes.dart';
import 'pump_screen.dart';

/// يقلع التطبيق كاملاً — بموجّهه وثيمه ولافتة بيئته — على مستودع مزيَّف.
///
/// يُستعمل حيث يكون **التنقّل** أو إقلاع التطبيق نفسه هو موضوع الاختبار. ما
/// عداه يُبنى بـ`pumpScreen` الأخفّ.
Future<void> pumpApp(
  WidgetTester tester, {
  required FakeCatalogRepository catalog,
  Locale locale = const Locale('ar'),
}) {
  usePhoneSurface(tester);
  return tester.pumpWidget(
    ProviderScope(
      overrides: [
        catalogRepositoryProvider.overrideWithValue(catalog),
        nowProvider.overrideWithValue(() => fixedNowUtc),
        countdownTickProvider.overrideWithValue(null),
      ],
      child: HarajApp(locale: locale),
    ),
  );
}
