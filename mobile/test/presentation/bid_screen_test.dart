import 'package:flutter_test/flutter_test.dart';
import 'package:haraj_mobile/app/providers.dart';
import 'package:haraj_mobile/domain/bidding/entities/live_bids_update.dart';
import 'package:haraj_mobile/l10n/generated/app_localizations.dart';
import 'package:haraj_mobile/presentation/bidding/bid_screen.dart';

import '../support/fake_bidding_repository.dart';
import '../support/pump_screen.dart';

/// T710 — شاشة المزايدة على مركبة.
void main() {
  Future<void> pumpBidScreen(
    WidgetTester tester,
    FakeBiddingRepository repository,
  ) async {
    await pumpScreen(
      tester,
      const BidScreen(vehicleId: 'V-1'),
      overrides: [biddingRepositoryProvider.overrideWithValue(repository)],
    );
    await tester.pumpAndSettle();
  }

  AppLocalizations l10nOf(WidgetTester tester) =>
      AppLocalizations.of(tester.element(find.byType(BidScreen)));

  LiveBidsUpdate update(
    LiveConnection connection, {
    List<LiveStandingBid> bids = const <LiveStandingBid>[],
  }) => LiveBidsUpdate(connection: connection, bids: bids);

  testWidgets('المزايدة القائمة تُعرض بمبلغها كما وصل من البثّ', (
    tester,
  ) async {
    await pumpBidScreen(
      tester,
      FakeBiddingRepository(
        live: Stream<LiveBidsUpdate>.value(
          update(
            LiveConnection.live,
            bids: const <LiveStandingBid>[
              LiveStandingBid(
                id: 'BID-1',
                vehicleId: 'V-1',
                amount: '12500.10',
                isWithdrawn: false,
                isSuperseded: false,
              ),
            ],
          ),
        ),
      ),
    );

    expect(find.text(l10nOf(tester).liveStandingBid), findsOneWidget);
    expect(find.text('12500.10'), findsOneWidget);
  });

  testWidgets('بلا مزايدة قائمة: جملة صريحة لا فراغ', (tester) async {
    await pumpBidScreen(
      tester,
      FakeBiddingRepository(
        live: Stream<LiveBidsUpdate>.value(update(LiveConnection.live)),
      ),
    );

    expect(find.text(l10nOf(tester).liveNoStandingBid), findsOneWidget);
  });

  testWidgets('انقطاع البثّ يظهر فوق الرقم لا تحته', (tester) async {
    // ترتيب مقصود: من يقرأ الرقم يحتاج أن يكون قد قرأ العلامة قبله.
    await pumpBidScreen(
      tester,
      FakeBiddingRepository(
        live: Stream<LiveBidsUpdate>.value(
          update(
            LiveConnection.lost,
            bids: const <LiveStandingBid>[
              LiveStandingBid(
                id: 'BID-1',
                vehicleId: 'V-1',
                amount: '900.00',
                isWithdrawn: false,
                isSuperseded: false,
              ),
            ],
          ),
        ),
      ),
    );

    final l10n = l10nOf(tester);
    expect(find.text(l10n.liveLost), findsOneWidget);
    expect(
      tester.getCenter(find.text(l10n.liveLost)).dy,
      lessThan(tester.getCenter(find.text('900.00')).dy),
    );
  });

  testWidgets('البثّ لا يحمل رقم منافس — لا مزايدة مركبة أخرى تظهر هنا', (
    tester,
  ) async {
    // البثّ قد يحمل مزايدات المتصل على مركبات أخرى؛ هذه الشاشة لا تعرض إلا
    // مزايدته على مركبتها. وليس في العقد أصلاً ما يحمل رقم غيره.
    await pumpBidScreen(
      tester,
      FakeBiddingRepository(
        live: Stream<LiveBidsUpdate>.value(
          update(
            LiveConnection.live,
            bids: const <LiveStandingBid>[
              LiveStandingBid(
                id: 'BID-9',
                vehicleId: 'V-2',
                amount: '77777.00',
                isWithdrawn: false,
                isSuperseded: false,
              ),
            ],
          ),
        ),
      ),
    );

    expect(find.text('77777.00'), findsNothing);
    expect(find.text(l10nOf(tester).liveNoStandingBid), findsOneWidget);
  });
}
