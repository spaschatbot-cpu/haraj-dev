import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:haraj_mobile/app/theme.dart';
import 'package:haraj_mobile/domain/catalog/entities/auction_summary.dart';
import 'package:haraj_mobile/l10n/generated/app_localizations.dart';
import 'package:haraj_mobile/presentation/catalog/home_screen.dart';

import '../support/catalog_fakes.dart';
import '../support/pump_app.dart';

/// T703 — «العربية وRTL من البداية، لا كطبقة تُضاف لاحقاً».
///
/// الشاشة المفحوصة هنا هي الرئيسية (T707): أول شاشة منتج حقيقية حلّت محلّ شاشة
/// البذرة. فحصُ الاتجاه على شاشة حقيقية أصدق من فحصه على شاشة كُتبت للفحص.
void main() {
  FakeCatalogRepository catalogWithOneAuction() => FakeCatalogRepository(
    home: fresh(
      HomeAuctions(
        running: <AuctionSummary>[auctionSummary()],
        upcoming: const <AuctionSummary>[],
      ),
    ),
  );

  testWidgets('التطبيق يقلع بالعربية واتجاه RTL', (tester) async {
    await pumpApp(tester, catalog: catalogWithOneAuction());
    await tester.pumpAndSettle();

    final context = tester.element(find.byType(HomeScreen));

    expect(Localizations.localeOf(context).languageCode, 'ar');
    expect(Directionality.of(context), TextDirection.rtl);
  });

  testWidgets('الاتجاه مشتقّ من اللغة لا مفروضاً بيد', (tester) async {
    // لو كانت RTL مفروضة بـ`Directionality` ثابتة لبقيت RTL هنا أيضاً — وهذا
    // بالضبط ما يكشفه هذا الاختبار.
    await pumpApp(
      tester,
      catalog: catalogWithOneAuction(),
      locale: const Locale('en'),
    );
    await tester.pumpAndSettle();

    final context = tester.element(find.byType(HomeScreen));

    expect(Directionality.of(context), TextDirection.ltr);
  });

  testWidgets('نصّ الشاشة يأتي من ملف الترجمة', (tester) async {
    await pumpApp(tester, catalog: catalogWithOneAuction());
    await tester.pumpAndSettle();

    final context = tester.element(find.byType(HomeScreen));
    final l10n = AppLocalizations.of(context);

    expect(find.text(l10n.homeTitle), findsOneWidget);
    expect(find.text(l10n.homeRunningSection), findsOneWidget);
  });

  testWidgets('الخط العربي مبنيّ في الحزمة لا مجلوب وقت التشغيل', (
    tester,
  ) async {
    await pumpApp(tester, catalog: catalogWithOneAuction());
    await tester.pumpAndSettle();

    final context = tester.element(find.byType(HomeScreen));
    final bodyStyle = Theme.of(context).textTheme.bodyLarge;

    expect(bodyStyle?.fontFamily, HarajTheme.fontFamily);
  });
}
