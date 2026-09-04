import 'package:haraj_mobile/data/local/cache/response_cache.dart';

/// كاش في الذاكرة للاختبارات.
///
/// يجعل اختبار سلوك «بلا اتصال» ممكناً بلا SQLite ولا محرّك أصلي — وهذا وحده
/// سبب وجود `ResponseCache` كواجهة.
///
/// يخزّن النصّ كما يخزّنه تنفيذ drift بالضبط، فما يمرّ هنا يمرّ هناك.
final class MemoryResponseCache implements ResponseCache {
  final Map<String, CachedDocument> _documents = <String, CachedDocument>{};

  int writeCount = 0;

  /// عدّاد التفريغ: «هل مُحي كاش العميل عند الخروج؟» سؤال أمني له جواب.
  int clearCount = 0;

  /// المفاتيح المكتوبة — «تحت أي مفتاح حُفظ هذا؟» سؤالٌ له جواب أيضاً، وهو ما
  /// يفرّق كاشاً لكل تبويب عن كاشٍ واحد يعرض تبويباً مكان آخر.
  Iterable<String> get keys => _documents.keys;

  @override
  Future<CachedDocument?> read(String key) async => _documents[key];

  @override
  Future<void> write(
    String key,
    String rawJson, {
    required DateTime fetchedAtUtc,
  }) async {
    writeCount++;
    _documents[key] = CachedDocument(
      rawJson: rawJson,
      fetchedAtUtc: fetchedAtUtc,
    );
  }

  @override
  Future<void> clear() async {
    clearCount++;
    _documents.clear();
  }
}
