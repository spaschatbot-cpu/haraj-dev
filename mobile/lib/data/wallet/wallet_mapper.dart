import '../../domain/common/money.dart';
import '../../domain/wallet/entities/ledger_movement.dart';
import '../../domain/wallet/entities/refund_request.dart';
import '../../domain/wallet/entities/top_up.dart';
import '../../domain/wallet/entities/wallet_balance.dart';
import '../api/generated/models/bucket.dart' as api;
import '../api/generated/models/hold.dart' as api;
import '../api/generated/models/ledger_entry.dart' as api;
import '../api/generated/models/paginated_ledger_entry_list.dart' as api;
import '../api/generated/models/payment_intent.dart' as api;
import '../api/generated/models/payment_intent_state_enum.dart' as api;
import '../api/generated/models/refund_request.dart' as api;
import '../api/generated/models/wallet.dart' as api;
/// تحويل نماذج المخطط المولَّدة إلى كيانات النطاق.
///
/// طبقة التحويل مقصودة: لولاها لسافر نموذج مولَّد إلى الشاشات، فصار كل تغيير
/// في المخطط تغييراً في كل شاشة. وهنا أيضاً يُحفظ المبلغ **نصّاً** كما وصل —
/// لا `double.parse` ولا تنسيق (المادة ٣-٢).
extension WalletMapper on api.Wallet {
  WalletBalance toDomain() => WalletBalance(
    buckets: buckets
        .map((bucket) => bucket.toDomain(currency))
        .toList(growable: false),
    holds: holds.map((hold) => hold.toDomain(currency)).toList(growable: false),
    // المجاميع الأربعة من الخادم لا من جمع الدلاء هنا: القيدُ الذي يثبتها
    // عنده، وجمعُها في التطبيق يصنع رقماً ثانياً لا سند له (المادة ١-٦).
    total: Money(amount: total, currency: currency),
    available: Money(amount: available, currency: currency),
    heldForAuctions: Money(amount: heldForAuctions, currency: currency),
    lockedForDues: Money(amount: lockedForDues, currency: currency),
    asOf: asOf.toUtc(),
  );
}

extension WalletBucketMapper on api.Bucket {
  /// العملة تأتي من المحفظة لا من الدلو: الخادم يعلنها مرّةً للمحفظة كلّها،
  /// وتكرارُها على كل دلو يوحي بأن دلواً قد يخالف.
  WalletBucket toDomain(String currency) => WalletBucket(
    kind: WalletBucketKind.fromSlug(kind),
    label: label,
    money: Money(amount: amount, currency: currency),
    entryCount: entryCount,
    statement: statement,
  );
}

extension WalletHoldMapper on api.Hold {
  WalletHold toDomain(String currency) => WalletHold(
    id: '$id',
    // نصُّ الخادم لا نصُّنا: `reason` رمزٌ برمجيّ و`reason_label` هو ما يُقرأ.
    reason: reasonLabel,
    money: Money(amount: amount, currency: currency),
    createdAt: createdAt.toUtc(),
  );
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
    id: '$id',
    description: description,
    bucketLabel: bucketLabel,
    bucket: WalletBucketKind.fromSlug(bucket),
    money: Money(amount: amount, currency: walletCurrency),
    direction: _directionOf(direction),
    occurredAt: occurredAt.toUtc(),
    // معرّف القيد المحاسبيّ — به يُطابَق سطرٌ على الشاشة بسطرٍ في الدفتر حين
    // يسأل عميلٌ عن حركة. كان `reference` في المخطط الوهميّ ولا وجود له؛
    // و`transaction` هو ما يقوله العقد.
    reference: transaction,
  );
}

/// اتجاه القيد **نصٌّ في العقد** لا تعداد.
///
/// وقيمةٌ لم نرها تصير `unknown` ولا تُسقط الحركة: المادتان ٢-٣ و٣-٥ — سطرٌ
/// باتجاهٍ مجهول يُعرض بمبلغه بلا سهم، ولا يختفي من كشف الحساب.
LedgerDirection _directionOf(String direction) => switch (direction) {
  'in' => LedgerDirection.incoming,
  'out' => LedgerDirection.outgoing,
  _ => LedgerDirection.unknown,
};

extension TopUpMapper on api.PaymentIntent {
  TopUp toDomain() => TopUp(
    reference: reference,
    money: Money(amount: amount, currency: currency ?? walletCurrency),
    checkoutUrl: checkoutUrl,
    status: _statusOf(state),
    statusLabel: stateLabel,
  );
}

/// حالة جديدة من الخادم تصير `unknown`، ويبقى `state_label` هو ما يُعرض —
/// فالمستخدم يقرأ كلام الخادم حتى لو لم يعرف هذا الإصدار الحالةَ برمجياً.
///
/// و`expired` و`disputed` في العقد بلا مقابلٍ في النطاق: كلتاهما **ليست
/// معلّقة ولا ناجحة**، والشاشة تفرّق بين الثلاث. طيُّهما على `failed` يقول
/// «فشل الدفع» لنزاعٍ قائم لم يُفصل فيه — فبقيتا `unknown` ونصُّهما من الخادم.
TopUpStatus _statusOf(api.PaymentIntentStateEnum? state) => switch (state) {
  api.PaymentIntentStateEnum.pending => TopUpStatus.pending,
  api.PaymentIntentStateEnum.succeeded => TopUpStatus.succeeded,
  api.PaymentIntentStateEnum.cancelled => TopUpStatus.cancelled,
  api.PaymentIntentStateEnum.failed => TopUpStatus.failed,
  _ => TopUpStatus.unknown,
};

/// عملة النظام حين لا يذكرها الحقل.
///
/// الخادم يعلنها على المحفظة، ويتركها على القيد وعلى نيّة الدفع — النظام
/// بعملةٍ واحدة. تُكتب مرّةً هنا لا في كل موضع.
const String walletCurrency = 'SAR';

/// صفُّ استردادٍ من العقد إلى النطاق.
///
/// **العملةُ تأتي مع المحفظة لا مع الصفّ**: العقد يرسل المبلغ نصّاً بلا عملة،
/// واختيارُ عملةٍ هنا اختراعُ معلومةٍ في شاشة مال. فتُمرَّر عملةُ الدلاء نفسها.
extension RefundRequestMapper on api.RefundRequest {
  RefundRequest toDomain({required String currency}) => RefundRequest(
    id: id.toString(),
    reference: reference,
    money: Money(amount: amount, currency: currency),
    stateLabel: stateLabel,
    createdAt: createdAt,
  );
}
