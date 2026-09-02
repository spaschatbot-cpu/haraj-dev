import '../../domain/common/money.dart';
import '../../domain/wallet/entities/wallet_balance.dart';
import '../api/generated/models/wallet.dart' as api;
import '../api/generated/models/wallet_bucket.dart' as api;
import '../api/generated/models/wallet_bucket_kind.dart' as api;
import '../api/generated/models/wallet_hold.dart' as api;

/// تحويل نماذج المخطط المولَّدة إلى كيانات النطاق.
///
/// طبقة التحويل مقصودة: لولاها لسافر نموذج مولَّد إلى الشاشات، فصار كل تغيير
/// في المخطط تغييراً في كل شاشة. وهنا أيضاً يُحفظ المبلغ **نصّاً** كما وصل —
/// لا `double.parse` ولا تنسيق (المادة ٣-٢).
extension WalletMapper on api.Wallet {
  WalletBalance toDomain() => WalletBalance(
    buckets: buckets.map((bucket) => bucket.toDomain()).toList(growable: false),
    asOf: asOf.toUtc(),
  );
}

extension WalletBucketMapper on api.WalletBucket {
  WalletBucket toDomain() => WalletBucket(
    kind: kind.toDomain(),
    label: label,
    money: Money(amount: amount, currency: currency),
    holds: (holds ?? const <api.WalletHold>[])
        .map((hold) => hold.toDomain())
        .toList(growable: false),
  );
}

extension WalletHoldMapper on api.WalletHold {
  WalletHold toDomain() => WalletHold(
    reference: reference,
    reason: reason,
    money: Money(amount: amount, currency: currency),
  );
}

extension WalletBucketKindMapper on api.WalletBucketKind {
  /// قيمة جديدة من الخادم تصير `unknown` ولا تُسقط الاستجابة (المادة ٢-٣).
  WalletBucketKind toDomain() => switch (this) {
    api.WalletBucketKind.wallet => WalletBucketKind.wallet,
    api.WalletBucketKind.insuranceFree => WalletBucketKind.insuranceFree,
    api.WalletBucketKind.insuranceHeld => WalletBucketKind.insuranceHeld,
    api.WalletBucketKind.insuranceLocked => WalletBucketKind.insuranceLocked,
    api.WalletBucketKind.$unknown => WalletBucketKind.unknown,
  };
}
