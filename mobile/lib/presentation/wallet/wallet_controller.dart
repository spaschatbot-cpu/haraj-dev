import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app/providers.dart';
import '../../domain/common/snapshot.dart';
import '../../domain/wallet/entities/ledger_movement.dart';
import '../../domain/wallet/entities/refund_request.dart';
import '../../domain/wallet/entities/wallet_balance.dart';

/// حالة المحفظة كما جاءت من الخادم، بمصدرها ولحظتها.
///
/// `Snapshot` لا `WalletBalance` مجرَّدة: بلا المصدر واللحظة تعرض الشاشة رصيداً
/// محفوظاً على أنه الحالي، وهذا أخطر ما يمكن أن تفعله شاشة فلوس.
final walletBalanceProvider =
    FutureProvider.autoDispose<Snapshot<WalletBalance>>(
      (ref) => ref.watch(loadWalletBalanceProvider)(),
    );

/// طلباتُ الاسترداد التي قدّمها العميل.
///
/// **مزوّدٌ مستقلٌّ عن الرصيد**: سقوطُ نقطةِ الاسترداد لا يجوز أن يُخفي
/// المحفظةَ كلَّها — البطاقةُ وحدها تعرض شرطةً، وما تحتها يبقى معروضاً.
final refundRequestsProvider =
    FutureProvider.autoDispose<Snapshot<List<RefundRequest>>>(
      (ref) => ref.watch(walletRepositoryProvider).loadRefundRequests(),
    );

/// عددُ حركات الحساب كما يقوله الخادم في `total` — لا طولُ الصفحة الأولى.
///
/// صفحةٌ من عشرين حركةً في حسابٍ فيه مئتان تقول «٢٠» وهي كذبة، والعقدُ يرسل
/// المجموع مع الصفحة فيُقرأ منه.
final walletMovementsCountProvider = FutureProvider.autoDispose<int>((
  ref,
) async {
  final page = await ref.watch(walletRepositoryProvider).loadTransactions();
  return page.value.total;
});

/// حركاتُ دلاء التأمين وحدها — «سجل عمليات التأمين».
///
/// **الترشيح هنا لا على السلك**: العقد لا يقبل `bucket` على نقطة الحركات، وكلُّ
/// سطرٍ يحمل دلوَه. وهذا يعني أن ما يُعرض هو حركاتُ التأمين **في الصفحة الأولى**
/// لا كلَّها — ولذلك لا عدّاد فوق القائمة: رقمٌ من صفحةٍ واحدة يقول «ثلاث
/// عمليات» في حسابٍ فيه ثلاثون.
final insuranceMovementsProvider =
    FutureProvider.autoDispose<List<LedgerMovement>>((ref) async {
      final page = await ref.watch(walletRepositoryProvider).loadTransactions();
      return page.value.movements
          .where(
            (movement) =>
                movement.bucket == WalletBucketKind.insuranceFree ||
                movement.bucket == WalletBucketKind.insuranceHeld ||
                movement.bucket == WalletBucketKind.insuranceLocked,
          )
          .toList(growable: false);
    });
