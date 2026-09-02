import '../../common/snapshot.dart';
import '../entities/wallet_balance.dart';

/// عقد المحفظة.
///
/// يرجع `Snapshot` لا `WalletBalance` مجرَّدة: العرض يحتاج أن يعرف إن كانت هذه
/// آخر نسخة من الخادم أم نسخة محفوظة، ومتى جُلبت — وإلا تعذّر تنفيذ H5 بصدق.
abstract interface class WalletRepository {
  /// يقرأ الدلاء. عند تعذّر الوصول للخادم يرجع آخر نسخة محفوظة، وعند غيابها
  /// يرمي `TransportFailure` — لا يرجع فراغاً يُقرأ كـ«رصيدك صفر».
  Future<Snapshot<WalletBalance>> loadBalance();
}
