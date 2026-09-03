import 'dart:convert';

/// آخر استجابة معروفة لمفتاح، بلحظة جلبها.
final class CachedDocument {
  const CachedDocument({required this.rawJson, required this.fetchedAtUtc});

  /// جسم الاستجابة **نصّاً كما وصل**.
  ///
  /// نصّ لا `Map`: نماذج المخطط المولَّدة تُرجع من `toJson()` خريطة تحوي نماذج
  /// أخرى غير مفكوكة، فتنجح الكتابة وتفشل القراءة عند أول حقل متداخل. حفظ
  /// النصّ يجعل ما يُكتب هو بعينه ما يُقرأ، في كل تنفيذ للكاش بلا استثناء.
  final String rawJson;

  /// بتوقيت UTC دائماً (المادة ٣-١).
  final DateTime fetchedAtUtc;

  /// يفكّ الجسم إلى خريطة صالحة لـ`Model.fromJson`. يرمي إن كان النصّ تالفاً.
  Map<String, Object?> decode() => jsonDecode(rawJson) as Map<String, Object?>;
}

/// كاش «آخر استجابة معروفة» لكل شاشة (T704).
///
/// واجهة مجرَّدة لسببين: أن يبقى `data/*_repository_impl` قابلاً للاختبار بلا
/// SQLite أصلاً، وأن يبقى استبدال المحرّك قراراً في مكان واحد.
abstract interface class ResponseCache {
  Future<CachedDocument?> read(String key);

  Future<void> write(
    String key,
    String rawJson, {
    required DateTime fetchedAtUtc,
  });

  /// يُستدعى عند الخروج من الحساب: بيانات عميل لا تبقى لعميل بعده.
  Future<void> clear();
}

/// مفاتيح الكاش — معرَّفة في مكان واحد كي لا يكتب مفتاحين لنفس الشاشة اثنان
/// بصيغتين (المادة ٤-٥).
abstract final class CacheKeys {
  static const String wallet = 'wallet.balance';

  /// مزادات الرئيسية (T707) — الجارية والقادمة في مستندٍ واحد، لأن الشاشة
  /// تعرضهما معاً ونصفُ رئيسيةٍ محفوظ أسوأ من رئيسيةٍ محفوظة كاملة.
  static const String homeAuctions = 'catalog.home-auctions';

  /// الصفحة الأولى بلا ترشيح من مركبات مزاد (T708). لا يُحفظ غيرها: صفحةٌ من
  /// بحثٍ قديم ليست «آخر ما نعرف» عن المزاد.
  static String auctionVehicles(String auctionId) =>
      'catalog.auction.$auctionId.vehicles';

  /// آخر نسخة معروفة من صفحة مركبة (T709) — مفتاحٌ لكل مركبة، فالعميل الذي فتح
  /// مركبةً ثم فقد الاتصال يراها كما رآها.
  static String vehicle(String vehicleId) => 'catalog.vehicle.$vehicleId';
}
