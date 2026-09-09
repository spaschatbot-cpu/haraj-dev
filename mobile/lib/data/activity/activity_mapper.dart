import '../../domain/activity/entities/invoice.dart';
import '../../domain/activity/entities/participation.dart';
import '../../domain/activity/entities/purchase.dart';
import '../../domain/common/money.dart';
import '../api/generated/models/invoice.dart' as api;
import '../api/generated/models/invoice_state_enum.dart' as api;
import '../api/generated/models/paginated_invoice_list.dart' as api;
import '../api/generated/models/paginated_purchase_list.dart' as api;
import '../api/generated/models/participation.dart' as api;
import '../api/generated/models/participation_page.dart' as api;
import '../api/generated/models/purchase.dart' as api;
import '../wallet/wallet_mapper.dart' show walletCurrency;

/// تحويل نماذج المخطط المولَّدة إلى كيانات النطاق.
///
/// المبلغ يُحفظ **نصّاً** كما وصل — لا `double.parse` ولا تنسيق (المادة ٣-٢).
extension ParticipationMapper on api.Participation {
  Participation toDomain() {
    final amount = insurance.amount;
    return Participation(
      auctionId: '${auction.id}',
      auctionTitle: auction.title,
      // نصُّ الخادم لا نصُّنا: `state` رمزٌ و`state_label` هو ما يُقرأ.
      auctionStatusLabel: auction.stateLabel,
      endsAt: auction.endsAt.toUtc(),
      bidsCount: bidsCount,
      insuranceState: _insuranceStateOf(insurance.state),
      insuranceStateLabel: insurance.stateLabel,
      // غياب المبلغ غياب: «لا تأمين» ليس «تأمينٌ صفر».
      insuranceMoney: amount == null
          ? null
          : Money(
              amount: amount,
              currency: insurance.currency ?? walletCurrency,
            ),
    );
  }
}

extension ParticipationPageMapper on api.ParticipationPage {
  List<Participation> toDomain() =>
      results.map((row) => row.toDomain()).toList(growable: false);
}

/// حال التأمين **نصٌّ في العقد** لا تعداد؛ وقيمةٌ لم نرها تصير `unknown`
/// ويبقى `state_label` هو ما يُعرض (المادتان ٢-٣ و٣-٥).
InsuranceState _insuranceStateOf(String state) => switch (state) {
  'none' => InsuranceState.none,
  'held' => InsuranceState.held,
  'locked' => InsuranceState.locked,
  'released' => InsuranceState.released,
  _ => InsuranceState.unknown,
};

extension PurchaseMapper on api.Purchase {
  Purchase toDomain() => Purchase(
    id: '$id',
    // المشترى **هو** المركبة في هذا العقد: صفٌّ واحد بمعرّفٍ واحد.
    vehicleId: '$id',
    lotNumber: '$lotNumber',
    title: '$make $model $year',
    auctionTitle: '${auction['title'] ?? ''}',
    awardedPrice: Money(amount: awardedPrice, currency: walletCurrency),
    awardedAt: awardedAt.toUtc(),
    state: _purchaseStateOf(state),
    // لا `state_label` على المشترى في العقد — النصّ من ملفّ الترجمة في طبقة
    // العرض، حيث تعيش نصوص الواجهة (المعيار H3).
    stateLabel: '',
    // الفاتورة على المشترى **ملخَّصٌ** لا فاتورةٌ كاملة: العقد يرسل خريطةً
    // فيها معرّفها ورقمها. والفاتورة الكاملة على `/invoices/{id}/`، فلا
    // تُبنى نصفُ فاتورةٍ هنا يظنّها من يقرأها كاملة.
    invoice: null,
  );

  /// معرّف فاتورة هذا المشترى، إن صدرت — للانتقال إليها.
  String? get invoiceId {
    final id = invoice?['id'];
    return id == null ? null : '$id';
  }
}

extension PurchasePageMapper on api.PaginatedPurchaseList {
  List<Purchase> toDomain() =>
      results.map((row) => row.toDomain()).toList(growable: false);
}

PurchaseState _purchaseStateOf(String state) => switch (state) {
  'awarded' => PurchaseState.awarded,
  'invoiced' => PurchaseState.invoiced,
  'paid' => PurchaseState.paid,
  'released' || 'handed_over' => PurchaseState.handedOver,
  'cancelled' => PurchaseState.cancelled,
  _ => PurchaseState.unknown,
};

extension InvoiceMapper on api.Invoice {
  Invoice toDomain() => Invoice(
    id: '$id',
    number: number,
    total: Money(amount: amount, currency: walletCurrency),
    paid: Money(amount: amountPaid, currency: walletCurrency),
    due: Money(amount: outstanding, currency: walletCurrency),
    state: _invoiceStateOf(state),
    stateLabel: stateLabel,
    issuedAt: issuedAt.toUtc(),
    // **لا قفل تأمين على الفاتورة في العقد.** القفل حالةٌ في المحفظة
    // (`locked_for_dues` ودلو `insurance_locked`) لا حقلٌ على الفاتورة —
    // والمحفظة هي التي تقوله بقيده. كان هنا لأن المخطط الوهميّ وعد به.
    insuranceLock: null,
  );
}

extension InvoicePageMapper on api.PaginatedInvoiceList {
  List<Invoice> toDomain() =>
      results.map((row) => row.toDomain()).toList(growable: false);
}

/// `draft` في العقد ولا مقابل له في النطاق: مسودّةُ فاتورةٍ لا تصل عميلاً.
/// وصولُها يوماً يعني `unknown` — تُعرض بنصّ الخادم ولا تُطوى على `open`،
/// فـ«مطلوبٌ سدادها» حكمٌ لم يقله أحد.
InvoiceState _invoiceStateOf(api.InvoiceStateEnum? state) => switch (state) {
  api.InvoiceStateEnum.open => InvoiceState.open,
  api.InvoiceStateEnum.partial => InvoiceState.partiallyPaid,
  api.InvoiceStateEnum.paid => InvoiceState.paid,
  api.InvoiceStateEnum.cancelled => InvoiceState.cancelled,
  _ => InvoiceState.unknown,
};
