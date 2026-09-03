import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:haraj_mobile/app/providers.dart';
import 'package:haraj_mobile/domain/bidding/entities/bid_outcome.dart';
import 'package:haraj_mobile/domain/common/failure.dart';
import 'package:haraj_mobile/l10n/generated/app_localizations.dart';
import 'package:haraj_mobile/presentation/bidding/place_bid_panel.dart';

import '../support/fake_bidding_repository.dart';
import '../support/pump_screen.dart';

/// T710 — صندوق المزايدة.
///
/// ما يُختبر هنا شيئان: أن الشاشة **لا تقرّر** (فلا شرط أهلية ولا حدّ أدنى ولا
/// استنتاج للخفض)، وأن الخفض **لا يمرّ صدفةً** (F3).
void main() {
  Future<void> pumpPanel(
    WidgetTester tester,
    FakeBiddingRepository repository,
  ) => pumpScreen(
    tester,
    const Scaffold(body: PlaceBidPanel(vehicleId: 'V-1')),
    overrides: [biddingRepositoryProvider.overrideWithValue(repository)],
  );

  AppLocalizations l10nOf(WidgetTester tester) =>
      AppLocalizations.of(tester.element(find.byType(PlaceBidPanel)));

  Future<void> typeAndBid(WidgetTester tester, String amount) async {
    await tester.enterText(find.byType(TextFormField), amount);
    await tester.tap(find.text(l10nOf(tester).bidSubmit));
    await tester.pumpAndSettle();
  }

  testWidgets('الصندوق يظهر بلا سؤال عن أهلية — والمبلغ يخرج كما كُتب', (
    tester,
  ) async {
    final repository = FakeBiddingRepository(
      outcomes: <Object>[BidAccepted(domainBid())],
    );
    await pumpPanel(tester, repository);

    await typeAndBid(tester, '12500.10');

    expect(repository.submissions.single.amount, '12500.10');
    expect(repository.submissions.single.confirmLower, isFalse);
    expect(find.text(l10nOf(tester).bidPlaced), findsOneWidget);
  });

  testWidgets('سبب الرفض يُعرض بنصّ الخادم حرفياً', (tester) async {
    // لا نبحث عن نصّ عندنا: نبحث عن نصّ الخادم بعينه. لو استبدلته الشاشة
    // برسالة عامة لسقط هذا الاختبار — وهو معنى J7 في هذه الطبقة.
    const serverText = 'لا يوجد تأمين متاح للمزايدة.';
    final repository = FakeBiddingRepository(
      outcomes: <Object>[
        const ApiFailure(
          code: 'no_deposit',
          message: serverText,
          statusCode: 409,
        ),
      ],
    );
    await pumpPanel(tester, repository);

    await typeAndBid(tester, '100.00');

    expect(find.text(serverText), findsOneWidget);
  });

  testWidgets('حقل فارغ لا يُرسِل نداءً', (tester) async {
    final repository = FakeBiddingRepository();
    await pumpPanel(tester, repository);

    await tester.tap(find.text(l10nOf(tester).bidSubmit));
    await tester.pumpAndSettle();

    expect(repository.submissions, isEmpty);
    expect(find.text(l10nOf(tester).bidAmountMissing), findsOneWidget);
  });

  group('خفض المزايدة (F3)', () {
    FakeBiddingRepository lowering() => FakeBiddingRepository(
      outcomes: <Object>[
        const BidNeedsLowerConfirmation(
          standingAmount: '12600.00',
          requestedAmount: '9000.00',
          message: 'المبلغ أقل من مزايدتك الحالية. أكّد الخفض إن كنت متأكداً.',
        ),
        BidAccepted(domainBid(amount: '9000.00')),
      ],
    );

    testWidgets('الحوار يذكر المبلغين كما جاءا في الرفض', (tester) async {
      final repository = lowering();
      await pumpPanel(tester, repository);

      await typeAndBid(tester, '9000.00');

      final l10n = l10nOf(tester);
      expect(find.text(l10n.bidLowerConfirmTitle), findsOneWidget);
      expect(find.text('12600.00'), findsOneWidget);
      expect(find.text(l10n.bidLowerStandingLabel), findsOneWidget);
      expect(find.text(l10n.bidLowerRequestedLabel), findsOneWidget);
      expect(
        find.text('المبلغ أقل من مزايدتك الحالية. أكّد الخفض إن كنت متأكداً.'),
        findsOneWidget,
      );
    });

    testWidgets('زرّ التأكيد معطَّل حتى يُؤشَّر المربّع', (tester) async {
      final repository = lowering();
      await pumpPanel(tester, repository);

      await typeAndBid(tester, '9000.00');

      final l10n = l10nOf(tester);
      final button = tester.widget<FilledButton>(
        find.widgetWithText(FilledButton, l10n.bidLowerConfirmAction),
      );
      expect(button.onPressed, isNull);
      // مربّع مؤشَّر سلفاً ليس تأكيداً؛ هو المحاولة الأولى ومعها حقل زائد.
      expect(tester.widget<Checkbox>(find.byType(Checkbox)).value, isFalse);
    });

    testWidgets('التأكيد يُعيد الإرسال بعلم الخفض — والمبلغ كما هو', (
      tester,
    ) async {
      final repository = lowering();
      await pumpPanel(tester, repository);

      await typeAndBid(tester, '9000.00');
      await tester.tap(find.byType(Checkbox));
      await tester.pumpAndSettle();
      await tester.tap(find.text(l10nOf(tester).bidLowerConfirmAction));
      await tester.pumpAndSettle();

      expect(repository.submissions, hasLength(2));
      expect(repository.submissions.first.confirmLower, isFalse);
      expect(repository.submissions.last.confirmLower, isTrue);
      expect(repository.submissions.last.amount, '9000.00');
    });

    testWidgets('الإلغاء لا يخفض شيئاً', (tester) async {
      final repository = lowering();
      await pumpPanel(tester, repository);

      await typeAndBid(tester, '9000.00');
      await tester.tap(find.text(l10nOf(tester).cancel));
      await tester.pumpAndSettle();

      expect(repository.submissions, hasLength(1));
      expect(find.text(l10nOf(tester).bidPlaced), findsNothing);
    });

    testWidgets('زرّ التأكيد ليس زرّ المزايدة في مكانه', (tester) async {
      // «لا تجعل زرّ التأكيد هو نفسه زرّ المزايدة في مكانه»: الحوار يقطع إيقاع
      // النقر، ونقرةٌ ثانية في موضع «زايد» لا تصادف تأكيداً.
      final repository = lowering();
      await pumpPanel(tester, repository);

      await typeAndBid(tester, '9000.00');

      final submit = tester.getCenter(find.text(l10nOf(tester).bidSubmit));
      final confirm = tester.getCenter(
        find.text(l10nOf(tester).bidLowerConfirmAction),
      );
      expect(confirm, isNot(submit));
    });
  });
}
