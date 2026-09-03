import '../../common/snapshot.dart';
import '../entities/ledger_movement.dart';
import '../entities/wallet_balance.dart';

/// عقد المحفظة.
///
/// يرجع `Snapshot` لا الكيان مجرَّداً: العرض يحتاج أن يعرف إن كانت هذه آخر نسخة
/// من الخادم أم نسخة محفوظة، ومتى جُلبت — وإلا تعذّر تنفيذ H5 بصدق.
abstract interface class WalletRepository {
  /// يقرأ الدلاء. عند تعذّر الوصول للخادم يرجع آخر نسخة محفوظة، وعند غيابها
  /// يرمي `TransportFailure` — لا يرجع فراغاً يُقرأ كـ«رصيدك صفر».
  Future<Snapshot<WalletBalance>> loadBalance();

  /// يقرأ صفحة من كشف الحركات، مرشَّحة على دلو واحد عند الطلب.
  ///
  /// الصفحة الأولى وحدها تُحفظ في الكاش: هي ما يفتحه المستخدم بلا اتصال، أما
  /// صفحة عاشرة محفوظة بلا ما قبلها فكشف بثقوب لا يعرف قارئه مكانها.
  Future<Snapshot<LedgerPage>> loadTransactions({
    int page,
    WalletBucketKind? bucket,
  });
}
