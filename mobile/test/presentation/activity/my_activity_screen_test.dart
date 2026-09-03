import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:haraj_mobile/app/providers.dart';
import 'package:haraj_mobile/domain/activity/entities/invoice.dart';
import 'package:haraj_mobile/domain/activity/entities/participation.dart';
import 'package:haraj_mobile/domain/activity/entities/purchase.dart';
import 'package:haraj_mobile/domain/activity/repositories/activity_repository.dart';
import 'package:haraj_mobile/domain/common/failure.dart';
import 'package:haraj_mobile/domain/common/money.dart';
import 'package:haraj_mobile/domain/common/snapshot.dart';
import 'package:haraj_mobile/l10n/generated/app_localizations.dart';
import 'package:haraj_mobile/presentation/activity/my_activity_screen.dart';

/// T714 — «اختبار widget لكل حالة فارغة وكل حالة ممتلئة»، وما هو أهم منها:
/// أن حالة الفاتورة تأتي من الخادم، وأن الفاتورة غير المسدَّدة تشرح ما تعنيه
/// لتأمين صاحبها.
void main() {
  final fetchedAt = DateTime.utc(2026, 9, 1, 7);

  final participation = Participation(
    auctionId: 'AUC-91',
    auctionTitle: 'مزاد الرياض ١٢',
    auctionStatusLabel: 'جارٍ الآن',
    endsAt: DateTime.utc(2026, 9, 3, 17),
    bidsCount: 3,
    insuranceState: InsuranceState.held,
    insuranceStateLabel: 'محجوز لهذا المزاد حتى نهايته',
    insuranceMoney: const Money(amount: '2500.00', currency: 'SAR'),
  );

  final unpaidInvoice = Invoice(
    id: 'INV-7',
    number: 'F-2026-7',
    total: const Money(amount: '12600.00', currency: 'SAR'),
    paid: const Money(amount: '0.00', currency: 'SAR'),
    due: const Money(amount: '12600.00', currency: 'SAR'),
    state: InvoiceState.open,
    stateLabel: 'غير مسدَّدة',
    issuedAt: DateTime.utc(2026, 9, 1, 6),
    insuranceLock: const InsuranceLock(
      money: Money(amount: '2500.00', currency: 'SAR'),
      note: 'تأمينك مقفول على هذه الفاتورة حتى السداد، ولا يمكن سحبه قبله.',
    ),
  );

  final purchase = Purchase(
    id: 'P-1',
    vehicleId: 'V-55',
    lotNumber: '14',
    title: 'تويوتا كامري ٢٠٢٢',
    auctionTitle: 'مزاد الرياض ١٢',
    awardedPrice: const Money(amount: '12600.00', currency: 'SAR'),
    awardedAt: DateTime.utc(2026, 9, 1, 5),
    state: PurchaseState.invoiced,
    stateLabel: 'صدرت فاتورتها',
    invoice: unpaidInvoice,
  );

  Future<void> pumpScreen(
    WidgetTester tester,
    _FakeActivityRepository repository, {
    MyActivityTab tab = MyActivityTab.participations,
  }) async {
    // مقاس جوال متوسط: الشاشة تُختبر على ما تُشحن عليه، لا على سطح مكتب.
    tester.view.physicalSize = const Size(1080, 2340);
    tester.view.devicePixelRatio = 3;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    await tester.pumpWidget(
      ProviderScope(
        overrides: [activityRepositoryProvider.overrideWithValue(repository)],
        child: MaterialApp(
          locale: const Locale('ar'),
          localizationsDelegates: AppLocalizations.localizationsDelegates,
          supportedLocales: AppLocalizations.supportedLocales,
          home: MyActivityScreen(initialTab: tab),
        ),
      ),
    );
    await tester.pumpAndSettle();
  }

  group('مشاركاتي', () {
    testWidgets('الحالة الفارغة تقول ذلك، ولا تُترك بيضاء', (tester) async {
      await pumpScreen(tester, _FakeActivityRepository(at: fetchedAt));

      expect(find.text('لم تدخل أي مزاد حتى الآن.'), findsOneWidget);
    });

    testWidgets('كل مشاركة تعرض حالة تأميني فيها بنصّ الخادم ومبلغه', (
      tester,
    ) async {
      await pumpScreen(
        tester,
        _FakeActivityRepository(
          at: fetchedAt,
          participations: <Participation>[participation],
        ),
      );

      expect(find.text('مزاد الرياض ١٢'), findsOneWidget);
      expect(find.text('جارٍ الآن'), findsOneWidget);
      expect(find.text('محجوز لهذا المزاد حتى نهايته'), findsOneWidget);
      // المبلغ كما وصل: بلا فاصلة آلاف ولا تقريب ولا جمع.
      expect(find.text('2500.00 SAR'), findsOneWidget);
      expect(find.text('عدد مزايداتي: 3'), findsOneWidget);
    });
  });

  group('مشترياتي', () {
    testWidgets('الحالة الفارغة تقول ذلك', (tester) async {
      await pumpScreen(
        tester,
        _FakeActivityRepository(at: fetchedAt),
        tab: MyActivityTab.purchases,
      );

      expect(find.text('لم ترسُ عليك أي مركبة حتى الآن.'), findsOneWidget);
    });

    testWidgets('المركبة تعرض حالتها من الخادم ومعها فاتورتها', (tester) async {
      await pumpScreen(
        tester,
        _FakeActivityRepository(at: fetchedAt, purchases: <Purchase>[purchase]),
        tab: MyActivityTab.purchases,
      );

      expect(find.text('تويوتا كامري ٢٠٢٢'), findsOneWidget);
      expect(find.text('صدرت فاتورتها'), findsOneWidget);
      expect(find.text('اللوت 14'), findsOneWidget);
      expect(find.text('فاتورة رقم F-2026-7'), findsOneWidget);
    });

    testWidgets('غياب الفاتورة حالة تُعرض، لا فراغ', (tester) async {
      final awaited = Purchase(
        id: purchase.id,
        vehicleId: purchase.vehicleId,
        lotNumber: purchase.lotNumber,
        title: purchase.title,
        auctionTitle: purchase.auctionTitle,
        awardedPrice: purchase.awardedPrice,
        awardedAt: purchase.awardedAt,
        state: PurchaseState.awarded,
        stateLabel: 'بانتظار الفاتورة',
      );

      await pumpScreen(
        tester,
        _FakeActivityRepository(at: fetchedAt, purchases: <Purchase>[awaited]),
        tab: MyActivityTab.purchases,
      );

      expect(find.text('لم تصدر فاتورة لهذه المركبة بعد.'), findsOneWidget);
    });
  });

  group('فواتيري', () {
    testWidgets('الحالة الفارغة تقول ذلك', (tester) async {
      await pumpScreen(
        tester,
        _FakeActivityRepository(at: fetchedAt),
        tab: MyActivityTab.invoices,
      );

      expect(find.text('لا توجد فواتير على حسابك.'), findsOneWidget);
    });

    testWidgets('المبلغ والمسدَّد والمتبقّي تُعرض كما وصلت', (tester) async {
      await pumpScreen(
        tester,
        _FakeActivityRepository(
          at: fetchedAt,
          invoices: <Invoice>[unpaidInvoice],
        ),
        tab: MyActivityTab.invoices,
      );

      expect(find.text('الإجمالي'), findsOneWidget);
      expect(find.text('المسدَّد'), findsOneWidget);
      expect(find.text('المتبقّي'), findsOneWidget);
      expect(find.text('0.00 SAR'), findsOneWidget);
      expect(find.text('12600.00 SAR'), findsWidgets);
    });

    testWidgets('الحالة من الخادم لا تُحسب من المبلغ والمسدَّد', (
      tester,
    ) async {
      // فاتورة سُدِّدت بالكامل بحساب ساذج (المسدَّد = الإجمالي) والخادم يقول
      // إنها ما زالت غير مسدَّدة، والمتبقّي عنده ليس الفرق. هذه ليست حالة
      // مفتعلة: في v1 كان عمود الحالة يُكتب مرة عند الإدراج فيتجمّد، وكل شاشة
      // اشتقّت الحالة بنفسها اختلفت عن الفاتورة. الشاشة تنقل ولا تجتهد.
      final disagreeing = Invoice(
        id: 'INV-9',
        number: 'F-2026-9',
        total: const Money(amount: '12600.00', currency: 'SAR'),
        paid: const Money(amount: '12600.00', currency: 'SAR'),
        due: const Money(amount: '600.00', currency: 'SAR'),
        state: InvoiceState.open,
        stateLabel: 'غير مسدَّدة',
        issuedAt: DateTime.utc(2026, 9, 1, 6),
      );

      await pumpScreen(
        tester,
        _FakeActivityRepository(
          at: fetchedAt,
          invoices: <Invoice>[disagreeing],
        ),
        tab: MyActivityTab.invoices,
      );

      expect(find.text('غير مسدَّدة'), findsOneWidget);
      expect(find.text('600.00 SAR'), findsOneWidget);
    });

    testWidgets('الفاتورة غير المسدَّدة تشرح أثرها على التأمين بنصّ الخادم', (
      tester,
    ) async {
      await pumpScreen(
        tester,
        _FakeActivityRepository(
          at: fetchedAt,
          invoices: <Invoice>[unpaidInvoice],
        ),
        tab: MyActivityTab.invoices,
      );

      expect(find.text('أثرها على تأميني'), findsOneWidget);
      expect(
        find.text(
          'تأمينك مقفول على هذه الفاتورة حتى السداد، ولا يمكن سحبه قبله.',
        ),
        findsOneWidget,
      );
      expect(find.text('2500.00 SAR'), findsOneWidget);
    });

    testWidgets('بلا شرح من الخادم لا يُخترع شرح في الشاشة', (tester) async {
      final withoutLock = Invoice(
        id: 'INV-8',
        number: 'F-2026-8',
        total: const Money(amount: '500.00', currency: 'SAR'),
        paid: const Money(amount: '500.00', currency: 'SAR'),
        due: const Money(amount: '0.00', currency: 'SAR'),
        state: InvoiceState.paid,
        stateLabel: 'مسدَّدة',
        issuedAt: DateTime.utc(2026, 8, 30, 6),
      );

      await pumpScreen(
        tester,
        _FakeActivityRepository(
          at: fetchedAt,
          invoices: <Invoice>[withoutLock],
        ),
        tab: MyActivityTab.invoices,
      );

      expect(find.text('أثرها على تأميني'), findsNothing);
    });
  });

  group('حالات الشاشة الأخرى', () {
    testWidgets('فشل ردّ به الخادم يُعرض برسالته العربية ومعه إعادة المحاولة', (
      tester,
    ) async {
      await pumpScreen(
        tester,
        _FakeActivityRepository(
          at: fetchedAt,
          failure: const ApiFailure(
            code: 'TOKEN_EXPIRED',
            message: 'انتهت الجلسة، سجّل الدخول من جديد.',
          ),
        ),
      );

      expect(find.text('انتهت الجلسة، سجّل الدخول من جديد.'), findsOneWidget);
      expect(find.text('إعادة المحاولة'), findsOneWidget);
    });

    testWidgets('البيانات المحفوظة تظهر بعلامة «آخر تحديث»', (tester) async {
      await pumpScreen(
        tester,
        _FakeActivityRepository(
          at: fetchedAt,
          participations: <Participation>[participation],
          fromCache: true,
        ),
      );

      // 07:00 بتوقيت UTC هي 10:00 بالسعودي — التحويل عند حافة العرض وحدها.
      expect(find.textContaining('بيانات محفوظة — آخر تحديث'), findsOneWidget);
      expect(find.textContaining('10:00'), findsOneWidget);
    });

    testWidgets('رابط الإشعار يفتح التبويب المطلوب مباشرةً', (tester) async {
      await pumpScreen(
        tester,
        _FakeActivityRepository(
          at: fetchedAt,
          invoices: <Invoice>[unpaidInvoice],
        ),
        tab: MyActivityTab.invoices,
      );

      expect(find.text('فاتورة رقم F-2026-7'), findsOneWidget);
    });
  });

  test('اسم تبويب غير معروف يفتح الأول ولا يُسقط الشاشة', () {
    expect(MyActivityTab.fromSlug('invoices'), MyActivityTab.invoices);
    expect(MyActivityTab.fromSlug(null), MyActivityTab.participations);
    // إشعار من نسخة خادم أحدث يجب أن يفتح شيئاً، لا أن يعرض عطباً.
    expect(MyActivityTab.fromSlug('refunds'), MyActivityTab.participations);
  });
}

/// مستودع مزيَّف يردّ ما نضعه فيه، أو يفشل بما نضعه في `failure`.
final class _FakeActivityRepository implements ActivityRepository {
  _FakeActivityRepository({
    required this.at,
    this.participations = const <Participation>[],
    this.purchases = const <Purchase>[],
    this.invoices = const <Invoice>[],
    this.failure,
    this.fromCache = false,
  });

  final DateTime at;
  final List<Participation> participations;
  final List<Purchase> purchases;
  final List<Invoice> invoices;
  final Failure? failure;
  final bool fromCache;

  Snapshot<List<T>> _snapshot<T>(List<T> value) => fromCache
      ? Snapshot<List<T>>.cached(value, storedAt: at)
      : Snapshot<List<T>>.fresh(value, at: at);

  @override
  Future<Snapshot<List<Participation>>> loadParticipations() async {
    final problem = failure;
    if (problem != null) throw problem;
    return _snapshot(participations);
  }

  @override
  Future<Snapshot<List<Purchase>>> loadPurchases() async {
    final problem = failure;
    if (problem != null) throw problem;
    return _snapshot(purchases);
  }

  @override
  Future<Snapshot<List<Invoice>>> loadInvoices() async {
    final problem = failure;
    if (problem != null) throw problem;
    return _snapshot(invoices);
  }
}
