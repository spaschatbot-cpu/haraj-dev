import '../entities/top_up.dart';
import '../repositories/wallet_repository.dart';

/// «الشحن ده تمّ ولا لأ؟» — والجواب من الخادم وحده.
///
/// هذه هي النقطة التي يُسنَد منها كل ما يُعرض بعد العودة من البوابة. لا معامل
/// من رابط العودة يدخل هنا، ولا شيء في التطبيق يستنتج نجاحاً من مجرّد أن
/// العميل عاد: الرصيد يتحرّك حين تؤكّد البوابة الدفع **للخادم**، وما دون ذلك
/// انتظار.
final class ReadTopUpStatus {
  const ReadTopUpStatus(this._repository);

  final WalletRepository _repository;

  Future<TopUp> call(String reference) => _repository.readTopUp(reference);
}
