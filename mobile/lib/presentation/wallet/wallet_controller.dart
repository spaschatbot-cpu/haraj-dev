import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app/providers.dart';
import '../../domain/common/snapshot.dart';
import '../../domain/wallet/entities/wallet_balance.dart';

/// حالة المحفظة كما جاءت من الخادم، بمصدرها ولحظتها.
///
/// `Snapshot` لا `WalletBalance` مجرَّدة: بلا المصدر واللحظة تعرض الشاشة رصيداً
/// محفوظاً على أنه الحالي، وهذا أخطر ما يمكن أن تفعله شاشة فلوس.
final walletBalanceProvider =
    FutureProvider.autoDispose<Snapshot<WalletBalance>>(
      (ref) => ref.watch(loadWalletBalanceProvider)(),
    );
