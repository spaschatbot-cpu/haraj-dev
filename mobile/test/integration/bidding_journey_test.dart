import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:haraj_mobile/app/haraj_app.dart';
import 'package:haraj_mobile/app/providers.dart';
import 'package:haraj_mobile/app/router.dart';
import 'package:haraj_mobile/domain/bidding/entities/bid_outcome.dart';
import 'package:haraj_mobile/domain/bidding/entities/placed_bid.dart';
import 'package:haraj_mobile/domain/common/failure.dart';
import 'package:haraj_mobile/l10n/generated/app_localizations.dart';
import 'package:haraj_mobile/presentation/bidding/bid_screen.dart';
import 'package:haraj_mobile/presentation/bidding/my_bids_screen.dart';

import '../support/catalog_fakes.dart';
import '../support/fake_bidding_repository.dart';

/// معيار القبول H7 — «اختبار تكامل لرحلة المزايدة كاملة».
///
/// الرحلة كما يعيشها عميل، عبر التطبيق الحقيقي بموجّهه وثيمه وترجمته: يفتح
/// صفحة المزايدة، يُرفض بسبب من الخادم، يزايد فيُقبل، ثم يخفض فيُطلب منه
/// تأكيد صريح، ثم يذهب إلى مزايداته ويسحب.
///
/// ما لا يُستبدل هنا هو المهم: الموجّه، والترجمة، والاتجاه، وشجرة المزوّدات
/// كما تُشحن. المُستبدَل واحد فقط — الشبكة.
void main() {
  testWidgets('رحلة المزايدة كاملة من الرفض إلى السحب', (tester) async {
    tester.view
      ..physicalSize = const Size(390, 844) * tester.view.devicePixelRatio
      ..devicePixelRatio = tester.view.devicePixelRatio;
    addTearDown(tester.view.reset);

    final repository = FakeBiddingRepository(
      outcomes: <Object>[
        // ١) رفض بسبب من الخادم — لا نصّ عندنا.
        const ApiFailure(
          code: 'no_deposit',
          message: 'لا يوجد تأمين متاح للمزايدة.',
          statusCode: 409,
        ),
        // ٢) قبول.
        BidAccepted(domainBid(amount: '12600.00')),
        // ٣) محاولة خفض — الخادم يطلب تأكيداً.
        const BidNeedsLowerConfirmation(
          standingAmount: '12600.00',
          requestedAmount: '9000.00',
          message: 'المبلغ أقل من مزايدتك الحالية. أكّد الخفض إن كنت متأكداً.',
        ),
        // ٤) الخفض بعد التأكيد.
        BidAccepted(domainBid(amount: '9000.00')),
      ],
      bids: <PlacedBid>[domainBid(amount: '9000.00')],
    );

    final container = ProviderContainer(
      overrides: [
        biddingRepositoryProvider.overrideWithValue(repository),
        // جذر التطبيق صار الرئيسية (T707)، والرحلة تمرّ به. الشبكة وحدها هي
        // المُستبدَلة كما يقول التعليق أعلاه — ومعها نبض العدّاد، لأن مؤقّتاً
        // دورياً يجعل `pumpAndSettle` لا تستقرّ أبداً فتسقط الرحلة على مهلة
        // لا على سلوك.
        catalogRepositoryProvider.overrideWithValue(emptyCatalogRepository()),
        nowProvider.overrideWithValue(() => fixedNowUtc),
        countdownTickProvider.overrideWithValue(null),
      ],
    );
    addTearDown(container.dispose);

    await tester.pumpWidget(
      UncontrolledProviderScope(container: container, child: const HarajApp()),
    );
    await tester.pumpAndSettle();

    container.read(routerProvider).go('/vehicles/V-1/bid');
    await tester.pumpAndSettle();

    expect(find.byType(BidScreen), findsOneWidget);
    final l10n = AppLocalizations.of(tester.element(find.byType(BidScreen)));

    Future<void> bid(String amount) async {
      await tester.enterText(find.byType(TextFormField), amount);
      await tester.tap(find.text(l10n.bidSubmit));
      await tester.pumpAndSettle();
    }

    // ١) الرفض بنصّ الخادم حرفياً.
    await bid('100.00');
    expect(find.text('لا يوجد تأمين متاح للمزايدة.'), findsOneWidget);

    // ٢) القبول.
    await bid('12600.00');
    expect(find.text(l10n.bidPlaced), findsOneWidget);

    // ٣) الخفض يحتاج تأكيداً، ولا يمرّ صدفةً.
    await bid('9000.00');
    expect(find.text(l10n.bidLowerConfirmTitle), findsOneWidget);
    expect(find.text(l10n.bidLowerStandingLabel), findsOneWidget);
    expect(find.text('12600.00'), findsOneWidget);
    // المبلغ الجديد يظهر في الحوار وفي الحقل الذي كتبه العميل — ووجوده في
    // الاثنين هو المقصود: ما يؤكّده هو ما كتبه.
    expect(find.text(l10n.bidLowerRequestedLabel), findsOneWidget);
    expect(find.text('9000.00'), findsWidgets);

    // ٤) التأكيد الصريح: مربّع ثم زرّ في حوارٍ لا في مكان زرّ المزايدة.
    await tester.tap(find.byType(Checkbox));
    await tester.pumpAndSettle();
    await tester.tap(find.text(l10n.bidLowerConfirmAction));
    await tester.pumpAndSettle();

    expect(repository.submissions, hasLength(4));
    expect(repository.submissions.map((s) => s.confirmLower), <bool>[
      false,
      false,
      false,
      true,
    ]);

    // ٥) مزايداتي، ثم السحب بتأكيده.
    container.read(routerProvider).go('/bids');
    await tester.pumpAndSettle();

    expect(find.byType(MyBidsScreen), findsOneWidget);
    expect(find.text('9000.00 SAR'), findsOneWidget);

    await tester.tap(find.text(l10n.bidWithdrawAction));
    await tester.pumpAndSettle();
    await tester.tap(find.text(l10n.bidWithdrawAction).last);
    await tester.pumpAndSettle();

    expect(repository.withdrawn, <String>['BID-1']);
    expect(find.text(l10n.bidWithdrawn), findsOneWidget);

    // الاتجاه بقي RTL طوال الرحلة — العربية أصلٌ لا طبقة تُضاف.
    expect(
      Directionality.of(tester.element(find.byType(MyBidsScreen))),
      TextDirection.rtl,
    );
  });
}
