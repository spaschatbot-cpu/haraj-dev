import '../../domain/activity/entities/invoice.dart';
import '../../domain/activity/entities/participation.dart';
import '../../domain/activity/entities/purchase.dart';
import '../../domain/common/money.dart';
import '../api/generated/models/insurance_lock.dart' as api;
import '../api/generated/models/insurance_state.dart' as api;
import '../api/generated/models/invoice.dart' as api;
import '../api/generated/models/invoice_status.dart' as api;
import '../api/generated/models/participation.dart' as api;
import '../api/generated/models/purchase.dart' as api;
import '../api/generated/models/purchase_state.dart' as api;

/// تحويل نماذج المخطط المولَّدة إلى كيانات النطاق.
///
/// طبقة التحويل مقصودة: لولاها لسافر نموذج مولَّد إلى الشاشات، فصار كل تغيير
/// في المخطط تغييراً في كل شاشة. وهنا يُحفظ المبلغ **نصّاً** كما وصل — لا
/// `double.parse` ولا تنسيق ولا طرح (المادة ٣-٢ والمادة ١-٦).
extension ParticipationMapper on api.Participation {
  Participation toDomain() {
    final amount = insuranceAmount;
    final code = currency;
    return Participation(
      auctionId: auctionId,
      auctionTitle: auctionTitle,
      auctionStatusLabel: auctionStatusLabel,
      endsAt: endsAt.toUtc(),
      bidsCount: bidsCount,
      insuranceState: insuranceState.toDomain(),
      insuranceStateLabel: insuranceStateLabel,
      // مبلغ بلا عملة (أو عملة بلا مبلغ) ليس مبلغاً يُعرض. الغياب هنا يعني
      // «لا تأمين مرتبط»، وهي حالة تعرضها الشاشة بنصّ الخادم لا برقم ناقص.
      insuranceMoney: (amount == null || code == null)
          ? null
          : Money(amount: amount, currency: code),
    );
  }
}

extension InsuranceStateMapper on api.InsuranceState {
  /// قيمة جديدة من الخادم تصير `unknown` ولا تُسقط الاستجابة (المادة ٢-٣).
  InsuranceState toDomain() => switch (this) {
    api.InsuranceState.none => InsuranceState.none,
    api.InsuranceState.held => InsuranceState.held,
    api.InsuranceState.locked => InsuranceState.locked,
    api.InsuranceState.released => InsuranceState.released,
    api.InsuranceState.$unknown => InsuranceState.unknown,
  };
}

extension PurchaseMapper on api.Purchase {
  Purchase toDomain() => Purchase(
    id: id,
    vehicleId: vehicleId,
    lotNumber: lotNumber,
    title: title,
    auctionTitle: auctionTitle,
    awardedPrice: Money(amount: awardedAmount, currency: currency),
    awardedAt: awardedAt.toUtc(),
    state: state.toDomain(),
    stateLabel: stateLabel,
    invoice: invoice?.toDomain(),
  );
}

extension PurchaseStateMapper on api.PurchaseState {
  PurchaseState toDomain() => switch (this) {
    api.PurchaseState.awarded => PurchaseState.awarded,
    api.PurchaseState.invoiced => PurchaseState.invoiced,
    api.PurchaseState.paid => PurchaseState.paid,
    api.PurchaseState.handedOver => PurchaseState.handedOver,
    api.PurchaseState.cancelled => PurchaseState.cancelled,
    api.PurchaseState.$unknown => PurchaseState.unknown,
  };
}

extension InvoiceMapper on api.Invoice {
  Invoice toDomain() => Invoice(
    id: id,
    number: number,
    total: Money(amount: totalAmount, currency: currency),
    paid: Money(amount: paidAmount, currency: currency),
    // `due_amount` يأتي من الخادم ولا يُشتق هنا من الاثنين قبله.
    due: Money(amount: dueAmount, currency: currency),
    state: status.toDomain(),
    stateLabel: statusLabel,
    issuedAt: issuedAt.toUtc(),
    insuranceLock: insuranceLock?.toDomain(),
  );
}

extension InvoiceStateMapper on api.InvoiceStatus {
  InvoiceState toDomain() => switch (this) {
    api.InvoiceStatus.open => InvoiceState.open,
    api.InvoiceStatus.partiallyPaid => InvoiceState.partiallyPaid,
    api.InvoiceStatus.paid => InvoiceState.paid,
    api.InvoiceStatus.cancelled => InvoiceState.cancelled,
    api.InvoiceStatus.$unknown => InvoiceState.unknown,
  };
}

extension InsuranceLockMapper on api.InsuranceLock {
  InsuranceLock toDomain() => InsuranceLock(
    money: Money(amount: amount, currency: currency),
    note: note,
  );
}
