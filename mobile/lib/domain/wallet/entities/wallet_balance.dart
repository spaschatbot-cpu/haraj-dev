import '../../common/money.dart';

/// الدلو الذي تسكن فيه فلوس العميل — نفس دلاء الدفتر حرفياً.
///
/// القيمة `unknown` مقصودة: المادة ٢-٣ و٣-٥ — قيمة لم نرها من قبل تُسجَّل ولا
/// تُسقِط الاستجابة التي تحملها.
enum WalletBucketKind {
  wallet,
  insuranceFree,
  insuranceHeld,
  insuranceLocked,
  unknown,
}

/// سبب حجز بعينه: أي مزاد، أي فاتورة.
///
/// **لماذا السبب إلزامي:** «الحجز مسمّى دائماً» (دليل النظام §4-2). ورقم بلا
/// سبب هو بالضبط ما جعل عملاء v1 يظنّون فلوسهم متاحة وهي محجوزة.
final class WalletHold {
  const WalletHold({
    required this.reference,
    required this.reason,
    required this.money,
  });

  /// معرّف المزاد أو الفاتورة التي يقابلها الحجز.
  final String reference;

  /// سبب عربي جاهز للعرض، من الخادم.
  final String reason;

  final Money money;
}

/// دلو واحد بمبلغه وأسباب حجزه.
final class WalletBucket {
  const WalletBucket({
    required this.kind,
    required this.label,
    required this.money,
    required this.holds,
  });

  final WalletBucketKind kind;

  /// اسم الدلو بالعربية من الخادم — لا خريطة أسماء في التطبيق.
  final String label;

  final Money money;
  final List<WalletHold> holds;
}

/// حالة فلوس العميل: الدلاء مفصَّلة، ولا مجموع.
///
/// **لا يوجد هنا `total`** عمداً. الفيز 008 يمنع جمع الدلاء في رقم واحد، وأي
/// مجموع يحتاجه العرض يأتي من الخادم بقيده الذي يثبته (المادة ١-٦).
final class WalletBalance {
  const WalletBalance({required this.buckets, required this.asOf});

  final List<WalletBucket> buckets;

  /// لحظة قراءة الدفتر، بتوقيت UTC.
  final DateTime asOf;
}
