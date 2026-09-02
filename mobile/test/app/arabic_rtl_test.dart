import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:haraj_mobile/app/haraj_app.dart';
import 'package:haraj_mobile/app/theme.dart';
import 'package:haraj_mobile/l10n/generated/app_localizations.dart';
import 'package:haraj_mobile/presentation/seed/seed_screen.dart';

/// T703 — «العربية وRTL من البداية، لا كطبقة تُضاف لاحقاً».
void main() {
  testWidgets('التطبيق يقلع بالعربية واتجاه RTL', (tester) async {
    await tester.pumpWidget(const ProviderScope(child: HarajApp()));
    await tester.pumpAndSettle();

    final context = tester.element(find.byType(SeedScreen));

    expect(Localizations.localeOf(context).languageCode, 'ar');
    expect(Directionality.of(context), TextDirection.rtl);
  });

  testWidgets('الاتجاه مشتقّ من اللغة لا مفروضاً بيد', (tester) async {
    // لو كانت RTL مفروضة بـ`Directionality` ثابتة لبقيت RTL هنا أيضاً — وهذا
    // بالضبط ما يكشفه هذا الاختبار.
    await tester.pumpWidget(
      const ProviderScope(child: HarajApp(locale: Locale('en'))),
    );
    await tester.pumpAndSettle();

    final context = tester.element(find.byType(SeedScreen));

    expect(Directionality.of(context), TextDirection.ltr);
  });

  testWidgets('نصّ الشاشة يأتي من ملف الترجمة', (tester) async {
    await tester.pumpWidget(const ProviderScope(child: HarajApp()));
    await tester.pumpAndSettle();

    final context = tester.element(find.byType(SeedScreen));
    final l10n = AppLocalizations.of(context);

    expect(find.text(l10n.seedTitle), findsOneWidget);
    expect(find.text(l10n.seedBody), findsOneWidget);
  });

  testWidgets('الخط العربي مبنيّ في الحزمة لا مجلوب وقت التشغيل', (
    tester,
  ) async {
    await tester.pumpWidget(const ProviderScope(child: HarajApp()));
    await tester.pumpAndSettle();

    final context = tester.element(find.byType(SeedScreen));
    final bodyStyle = Theme.of(context).textTheme.bodyLarge;

    expect(bodyStyle?.fontFamily, HarajTheme.fontFamily);
  });
}
