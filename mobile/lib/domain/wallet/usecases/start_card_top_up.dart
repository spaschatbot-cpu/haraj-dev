import '../entities/top_up.dart';
import '../gateways/checkout_launcher.dart';
import '../repositories/wallet_repository.dart';

/// «اشحن تأميني بالبطاقة.»
///
/// خطوتان بترتيب لا يُعكس: **تُكتب النيّة عند الخادم أولاً**، ثم يُسلَّم العميل
/// إلى البوابة. النيّة هي ما يربط دفعةً عائدة بصاحبها — البوابة لا تحمل هوية
/// المستخدم عندنا، و v1 كان يستعيدها مما يعود في الرابط، وهو قابل للضياع
/// وللتزوير معاً.
///
/// ولا مبلغ في الطلب: الخادم يحدّده (`deposit_amount_for` في الخلفية)، وطلبٌ
/// يسمّي مبلغه يُرفض عند الحافة.
final class StartCardTopUp {
  const StartCardTopUp({
    required WalletRepository repository,
    required CheckoutLauncher launcher,
  }) : _repository = repository,
       _launcher = launcher;

  final WalletRepository _repository;
  final CheckoutLauncher _launcher;

  Future<TopUpHandoff> call() async {
    final intent = await _repository.startTopUp();
    final opened = await _launcher.open(intent.checkoutUrl);
    return TopUpHandoff(intent: intent, gatewayOpened: opened);
  }
}
