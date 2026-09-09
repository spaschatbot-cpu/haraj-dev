import '../../common/money.dart';

/// الدلو الذي تسكن فيه فلوس العميل — نفس دلاء الدفتر حرفياً.
///
/// القيمة `unknown` مقصودة: المادة ٢-٣ و٣-٥ — قيمة لم نرها من قبل تُسجَّل ولا
/// تُسقِط الاستجابة التي تحملها.
enum WalletBucketKind {
  wallet('wallet'),
  insuranceFree('insurance_free'),
  insuranceHeld('insurance_held'),
  insuranceLocked('insurance_locked'),
  unknown('');

  const WalletBucketKind(this.slug);

  /// الاسم على السلك. الخادم يرسل الدلو **نصّاً** لا تعداداً مغلقاً — والمادة
  /// ٣-٥ تُبقيه كذلك: دلوٌ جديد في الدفتر لا يجوز أن يُسقط شاشة المحفظة.
  final String slug;

  static WalletBucketKind fromSlug(String? slug) => values.firstWhere(
    (kind) => kind.slug == slug,
    orElse: () => WalletBucketKind.unknown,
  );
}

/// سبب حجز بعينه: أي مزاد، أي فاتورة.
///
/// **لماذا السبب إلزامي:** «الحجز مسمّى دائماً» (دليل النظام §4-2). ورقم بلا
/// سبب هو بالضبط ما جعل عملاء v1 يظنّون فلوسهم متاحة وهي محجوزة.
final class WalletHold {
  const WalletHold({
    required this.id,
    required this.reason,
    required this.money,
    required this.createdAt,
  });

  /// معرّف الحجز نفسه.
  ///
  /// كان `reference` — «معرّف المزاد أو الفاتورة». والعقد لا يرسل ذلك رقماً
  /// مفرداً: يرسل `auction` أو `invoice` كائناً، وأحدهما فارغ. فبقي المعرّف
  /// معرّفَ الحجز، والسبب المعروض هو `reason_label`.
  final String id;

  /// سبب عربي جاهز للعرض، من الخادم.
  final String reason;

  final Money money;

  /// لحظة الحجز، بتوقيت UTC.
  final DateTime createdAt;
}

/// دلو واحد بمبلغه.
///
/// **ولا حجوزات عليه.** الحجز في العقد على المحفظة لا على دلو، وهو الأصدق:
/// حجزٌ واحد قد يمسّ أكثر من دلو، وتوزيعُه على الدلاء هنا كان يخترع نسبةً لم
/// يقلها الدفتر. الحجوزات في `WalletBalance.holds`.
final class WalletBucket {
  const WalletBucket({
    required this.kind,
    required this.label,
    required this.money,
    required this.entryCount,
    required this.statement,
  });

  final WalletBucketKind kind;

  /// اسم الدلو بالعربية من الخادم — لا خريطة أسماء في التطبيق.
  final String label;

  final Money money;

  /// عدد القيود التي يتألّف منها المبلغ. رقمٌ يجعل الدلو **قابلاً للمراجعة**:
  /// «٣٠٠ ريال» وحدها لا تُسأل، و«٣٠٠ من ١٢ قيداً» تُسأل.
  final int entryCount;

  /// جملة الخادم التي تشرح ما يعنيه هذا الدلو — تُعرض كما هي.
  final String statement;
}

/// حالة فلوس العميل: الدلاء مفصَّلة، والحجوزات مسمّاة.
///
/// **لا يوجد هنا `total` محسوبٌ عندنا** عمداً. الفيز 008 يمنع جمع الدلاء في
/// رقم واحد؛ والمجاميع التي تُعرض تأتي من الخادم بقيدها الذي يثبتها
/// (المادة ١-٦) — ولذلك هي حقولٌ من العقد لا حسابٌ هنا.
final class WalletBalance {
  const WalletBalance({
    required this.buckets,
    required this.holds,
    required this.total,
    required this.available,
    required this.heldForAuctions,
    required this.lockedForDues,
    required this.asOf,
  });

  final List<WalletBucket> buckets;

  /// كل حجزٍ قائم، مسمّى بسببه.
  final List<WalletHold> holds;

  /// أربعة مجاميع **يحسبها الخادم** من الدفتر نفسه.
  final Money total;
  final Money available;
  final Money heldForAuctions;
  final Money lockedForDues;

  /// لحظة قراءة الدفتر، بتوقيت UTC.
  final DateTime asOf;
}
