import '../../domain/common/money.dart';
import '../../domain/wallet/entities/ledger_movement.dart';
import '../../domain/wallet/entities/top_up.dart';
import '../../domain/wallet/entities/wallet_balance.dart';
import '../api/generated/models/ledger_entry.dart' as api;
import '../api/generated/models/ledger_entry_direction.dart' as api;
import '../api/generated/models/paginated_ledger_entry_list.dart' as api;
import '../api/generated/models/top_up_intent.dart' as api;
import '../api/generated/models/top_up_intent_status.dart' as api;
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

extension WalletBucketKindWire on WalletBucketKind {
  /// الاتجاه المعاكس: من كيان النطاق إلى قيمة يفهمها الخادم عند الترشيح.
  ///
  /// `unknown` ترجع `null` عمداً — دلو لا نعرف اسمه على السلك لا يمكن أن
  /// نسأل عنه، وإرسال كلمة مخترعة يجعل الخادم يرفض بسبب صنعناه نحن.
  api.WalletBucketKind? toWire() => switch (this) {
    WalletBucketKind.wallet => api.WalletBucketKind.wallet,
    WalletBucketKind.insuranceFree => api.WalletBucketKind.insuranceFree,
    WalletBucketKind.insuranceHeld => api.WalletBucketKind.insuranceHeld,
    WalletBucketKind.insuranceLocked => api.WalletBucketKind.insuranceLocked,
    WalletBucketKind.unknown => null,
  };
}

extension LedgerPageMapper on api.PaginatedLedgerEntryList {
  /// `page` ليس في الاستجابة: الخادم يرجع `next`/`previous` كعناوين، والتطبيق
  /// لا يفكّ عنواناً ليستخرج منه رقماً — يمرّر الرقم الذي طلب به.
  LedgerPage toDomain({required int page}) => LedgerPage(
    movements: results.map((entry) => entry.toDomain()).toList(growable: false),
    hasMore: next != null,
    page: page,
    total: count,
  );
}

extension LedgerMovementMapper on api.LedgerEntry {
  LedgerMovement toDomain() => LedgerMovement(
    id: id,
    description: description,
    bucketLabel: bucketLabel,
    bucket: bucket?.toDomain(),
    money: Money(amount: amount, currency: currency),
    direction: direction.toDomain(),
    occurredAt: occurredAt.toUtc(),
    reference: reference,
  );
}

extension LedgerDirectionMapper on api.LedgerEntryDirection {
  LedgerDirection toDomain() => switch (this) {
    api.LedgerEntryDirection.valueIn => LedgerDirection.incoming,
    api.LedgerEntryDirection.out => LedgerDirection.outgoing,
    api.LedgerEntryDirection.$unknown => LedgerDirection.unknown,
  };
}

extension TopUpMapper on api.TopUpIntent {
  TopUp toDomain() => TopUp(
    reference: reference,
    money: Money(amount: amount, currency: currency),
    checkoutUrl: redirectUrl,
    status: status.toDomain(),
    statusLabel: statusLabel,
  );
}

extension TopUpStatusMapper on api.TopUpIntentStatus {
  /// حالة جديدة من الخادم تصير `unknown`، ويبقى `status_label` هو ما يُعرض —
  /// فالمستخدم يقرأ كلام الخادم حتى لو لم يعرف هذا الإصدار الحالةَ برمجياً.
  TopUpStatus toDomain() => switch (this) {
    api.TopUpIntentStatus.pending => TopUpStatus.pending,
    api.TopUpIntentStatus.succeeded => TopUpStatus.succeeded,
    api.TopUpIntentStatus.cancelled => TopUpStatus.cancelled,
    api.TopUpIntentStatus.failed => TopUpStatus.failed,
    api.TopUpIntentStatus.$unknown => TopUpStatus.unknown,
  };
}
