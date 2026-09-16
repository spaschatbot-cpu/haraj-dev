import '../entities/refund_request.dart';
import '../repositories/wallet_repository.dart';

/// «أعيدوا لي تأميني المتاح».
///
/// والمبلغُ **لا يُتحقَّق منه هنا**: ما يجوز خروجُه يقرّره الدلو الحرّ في
/// `money.services.request_refund`، ونسخةٌ ثانيةٌ من القاعدة في التطبيق
/// تُصبح نسخةً تتفارق — فترفض الشاشةُ مبلغاً يقبله الخادم أو العكس.
final class RequestInsuranceRefund {
  const RequestInsuranceRefund(this._repository);

  final WalletRepository _repository;

  Future<RefundRequest> call({required String amount, String note = ''}) =>
      _repository.requestRefund(amount: amount, note: note);
}
