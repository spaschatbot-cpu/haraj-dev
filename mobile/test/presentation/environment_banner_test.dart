import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:haraj_mobile/app/haraj_app.dart';
import 'package:haraj_mobile/app/providers.dart';
import 'package:haraj_mobile/core/environment.dart';
import 'package:haraj_mobile/l10n/generated/app_localizations.dart';
import 'package:haraj_mobile/presentation/common/environment_banner.dart';
import 'package:haraj_mobile/presentation/seed/seed_screen.dart';

import '../support/pump_localized.dart';

/// T718 — «لافتة ظاهرة في أي بناء غير إنتاجي» (المادة ٥-٦).
void main() {
  Future<void> pumpApp(WidgetTester tester, AppEnvironment environment) =>
      tester.pumpWidget(
        ProviderScope(
          overrides: [
            appConfigProvider.overrideWithValue(
              AppConfig(
                environment: environment,
                apiBaseUrl: 'https://api.example.invalid',
              ),
            ),
          ],
          child: const HarajApp(),
        ),
      );

  testWidgets('بناء التطوير يعرّف نفسه على الشاشة', (tester) async {
    await pumpApp(tester, AppEnvironment.development);
    await tester.pumpAndSettle();

    final l10n = AppLocalizations.of(tester.element(find.byType(SeedScreen)));
    final banner = tester.widget<Banner>(find.byType(Banner));

    expect(banner.message, l10n.environmentBanner(l10n.environmentDevelopment));
  });

  testWidgets('بناء التجريب يعرّف نفسه باسمه هو', (tester) async {
    // «تجريب» لا «تطوير»: مختبِر يقرأ الاسم الخطأ يظنّ نفسه على بيئة غير التي
    // هو عليها، وهو ما تمنعه المادة ٥-٦ أصلاً.
    await pumpApp(tester, AppEnvironment.staging);
    await tester.pumpAndSettle();

    final l10n = AppLocalizations.of(tester.element(find.byType(SeedScreen)));
    final banner = tester.widget<Banner>(find.byType(Banner));

    expect(banner.message, l10n.environmentBanner(l10n.environmentStaging));
  });

  testWidgets('الإنتاج بلا لافتة — لا شيء يعترض شاشة عميل حقيقي', (
    tester,
  ) async {
    await pumpApp(tester, AppEnvironment.production);
    await tester.pumpAndSettle();

    expect(find.byType(Banner), findsNothing);
  });

  testWidgets('اللافتة لا تحجب المحتوى بل تلتفّ حوله', (tester) async {
    // لافتة تحلّ محلّ الشاشة تُطفأ في أول أسبوع، ثم لا تعود.
    await pumpLocalized(
      tester,
      const EnvironmentBanner(
        environment: AppEnvironment.staging,
        child: Text('محتوى'),
      ),
    );

    final ours = tester
        .widgetList<Banner>(find.byType(Banner))
        // `MaterialApp` في المساعد يرسم لافتة DEBUG خاصة به؛ نحن نسأل عن لافتتنا.
        .where((banner) => banner.message.contains('تجريب'));

    expect(find.text('محتوى'), findsOneWidget);
    expect(ours, hasLength(1));
  });
}
