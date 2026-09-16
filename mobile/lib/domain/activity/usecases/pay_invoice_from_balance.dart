import '../entities/invoice.dart';
import '../repositories/activity_repository.dart';

/// «سدّد الفاتورة من رصيدي».
///
/// الفعلُ الوحيد في هذه العائلة — والثلاثةُ الباقون قراءات. والخلفيةُ تُبقي
/// بابَ الدفع واحداً (`bidding.settlement`): هي التي تقيّد الدفعة وتنقل
/// المركبةَ إلى `paid` وتفكّ ما رُهن، فليس للتطبيق في ذلك رأيٌ ولا خطوة.
final class PayInvoiceFromBalance {
  const PayInvoiceFromBalance(this._repository);

  final ActivityRepository _repository;

  Future<Invoice> call(String invoiceId) =>
      _repository.payInvoiceFromBalance(invoiceId);
}
