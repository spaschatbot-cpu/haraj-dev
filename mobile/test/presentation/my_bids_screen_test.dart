import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:haraj_mobile/app/providers.dart';
import 'package:haraj_mobile/domain/bidding/entities/live_bids_update.dart';
import 'package:haraj_mobile/domain/bidding/entities/placed_bid.dart';
import 'package:haraj_mobile/domain/common/failure.dart';
import 'package:haraj_mobile/l10n/generated/app_localizations.dart';
import 'package:haraj_mobile/presentation/bidding/my_bids_screen.dart';

import '../support/fake_bidding_repository.dart';
import '../support/pump_screen.dart';

/// T710 — شاشة «مزايداتي».
///
/// أربع حالات لا واحدة: تحميل، وفشل، وفارغة، وممتلئة — وفوقها كلها حال البثّ.
/// «شاشة تعرض دوّامة إلى الأبد عند سقوط الشبكة عطل، لا تصميم.»
void main() {
  Future<void> pumpMyBids(
    WidgetTester tester,
    FakeBiddingRepository repository, {
    bool settle = true,
  }) async {
    await pumpScreen(
      tester,
      const MyBidsScreen(),
      overrides: [biddingRepositoryProvider.overrideWithValue(repository)],
    );
    if (settle) await tester.pumpAndSettle();
  }

  AppLocalizations l10nOf(WidgetTester tester) =>
      AppLocalizations.of(tester.element(find.byType(MyBidsScreen)));

  testWidgets('التحميل يعرض دوّامة، لا شاشة بيضاء', (tester) async {
    await pumpMyBids(
      tester,
      FakeBiddingRepository(myBidsDelay: const Duration(milliseconds: 50)),
      settle: false,
    );
    await tester.pump();

    expect(find.byType(CircularProgressIndicator), findsOneWidget);
    await tester.pumpAndSettle();
  });

  testWidgets('حالة فارغة مكتوبة لا قائمة صامتة', (tester) async {
    await pumpMyBids(tester, FakeBiddingRepository());

    expect(find.text(l10nOf(tester).myBidsEmpty), findsOneWidget);
  });

  testWidgets('كل مزايدة بمبلغها ووصفها العربي من الخادم', (tester) async {
    await pumpMyBids(
      tester,
      FakeBiddingRepository(
        bids: <PlacedBid>[
          domainBid(amount: '12500.10', stateLabel: 'الأعلى حتى الآن'),
        ],
      ),
    );

    expect(find.text('تويوتا كامري 2021'), findsOneWidget);
    expect(find.text('الأعلى حتى الآن'), findsOneWidget);
    // المبلغ كما وصل: بلا فاصلة آلاف وبلا تقريب (المادة ١-٦).
    expect(find.text('12500.10 SAR'), findsOneWidget);
  });

  testWidgets('سقوط الشبكة بعد نجاح سابق: بيانات محفوظة بعلامتها لا شاشة خطأ', (
    tester,
  ) async {
    final repository = FakeBiddingRepository(bids: <PlacedBid>[domainBid()])
      ..cached = true;
    await pumpMyBids(tester, repository);

    // العلامة تحمل التاريخ والوقت، فيكفي أن نتحقق من وجود بيانات ومن أن
    // الشاشة لم تتحول إلى خطأ.
    expect(find.text('تويوتا كامري 2021'), findsOneWidget);
    expect(find.byType(CircularProgressIndicator), findsNothing);
  });

  testWidgets('الفشل يعرض جواب الخادم وزرّ إعادة', (tester) async {
    await pumpMyBids(
      tester,
      FakeBiddingRepository(
        myBidsFailure: const TransportFailure(TransportProblem.offline),
      ),
    );

    final l10n = l10nOf(tester);
    expect(find.text(l10n.errorOffline), findsOneWidget);
    expect(find.text(l10n.retry), findsOneWidget);
  });

  group('السحب', () {
    testWidgets('لا يُسحب شيء قبل تأكيد صريح', (tester) async {
      final repository = FakeBiddingRepository(bids: <PlacedBid>[domainBid()]);
      await pumpMyBids(tester, repository);

      await tester.tap(find.text(l10nOf(tester).bidWithdrawAction));
      await tester.pumpAndSettle();
      await tester.tap(find.text(l10nOf(tester).cancel));
      await tester.pumpAndSettle();

      expect(repository.withdrawn, isEmpty);
    });

    testWidgets('التأكيد يسحب المزايدة ويخبر المستخدم', (tester) async {
      final repository = FakeBiddingRepository(bids: <PlacedBid>[domainBid()]);
      await pumpMyBids(tester, repository);
      final l10n = l10nOf(tester);

      await tester.tap(find.text(l10n.bidWithdrawAction));
      await tester.pumpAndSettle();
      // زرّ الحوار هو الثاني بنفس النصّ؛ الأخير هو الذي داخل الحوار.
      await tester.tap(find.text(l10n.bidWithdrawAction).last);
      await tester.pumpAndSettle();

      expect(repository.withdrawn, <String>['BID-1']);
      expect(find.text(l10n.bidWithdrawn), findsOneWidget);
    });

    testWidgets('رفض السحب يُعرض بنصّ الخادم', (tester) async {
      const serverText = 'هذه المزايدة ليست مزايدتك.';
      final repository = FakeBiddingRepository(
        bids: <PlacedBid>[domainBid()],
        withdrawFailure: const ApiFailure(
          code: 'not_your_bid',
          message: serverText,
          statusCode: 404,
        ),
      );
      await pumpMyBids(tester, repository);
      final l10n = l10nOf(tester);

      await tester.tap(find.text(l10n.bidWithdrawAction));
      await tester.pumpAndSettle();
      await tester.tap(find.text(l10n.bidWithdrawAction).last);
      await tester.pumpAndSettle();

      expect(find.text(serverText), findsOneWidget);
    });

    testWidgets('المسحوبة لا تعرض زرّ سحب مرة ثانية', (tester) async {
      await pumpMyBids(
        tester,
        FakeBiddingRepository(
          bids: <PlacedBid>[
            domainBid(state: BidState.withdrawn, stateLabel: 'مسحوبة'),
          ],
        ),
      );

      expect(find.text('مسحوبة'), findsOneWidget);
      expect(find.text(l10nOf(tester).bidWithdrawAction), findsNothing);
    });
  });

  group('حال البثّ الحي', () {
    testWidgets('الانقطاع يُكتب فوق الأرقام ولا يُترك للتخمين', (tester) async {
      await pumpMyBids(
        tester,
        FakeBiddingRepository(
          bids: <PlacedBid>[domainBid()],
          live: Stream<LiveBidsUpdate>.value(
            const LiveBidsUpdate(
              connection: LiveConnection.lost,
              bids: <LiveStandingBid>[],
            ),
          ),
        ),
      );

      expect(find.text(l10nOf(tester).liveLost), findsOneWidget);
      // الأرقام تبقى معروضة تحت العلامة، لا تُمحى.
      expect(find.text('تويوتا كامري 2021'), findsOneWidget);
    });

    testWidgets('الاتصال الحي مكتوب أيضاً — الغياب لا يعني شيئاً', (
      tester,
    ) async {
      await pumpMyBids(tester, FakeBiddingRepository());

      expect(find.text(l10nOf(tester).liveConnected), findsOneWidget);
    });
  });
}
