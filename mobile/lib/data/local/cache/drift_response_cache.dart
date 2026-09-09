import 'cache_database.dart';
import 'response_cache.dart';

/// تنفيذ `ResponseCache` فوق drift.
final class DriftResponseCache implements ResponseCache {
  const DriftResponseCache(this._database);

  final CacheDatabase _database;

  @override
  Future<CachedDocument?> read(String key) async {
    final row = await (_database.select(
      _database.cachedDocuments,
    )..where((table) => table.key.equals(key))).getSingleOrNull();
    if (row == null) return null;

    return CachedDocument(
      rawJson: row.payload,
      fetchedAtUtc: DateTime.fromMillisecondsSinceEpoch(
        row.fetchedAtUtcMillis,
        isUtc: true,
      ),
    );
  }

  /// **الكتابة لا تفشل إلى الأعلى.**
  ///
  /// الكاش شبكةُ أمانٍ لما وصل، لا شرطٌ لوصوله. وكان فشلُ الحفظ يُلقى إلى
  /// المستودع، فيخرج من `try` الذي لا يلتقط إلا `TransportFailure`، فتسقط
  /// الشاشة بـ«حدث خطأ غير متوقع» **على استجابةٍ ناجحة وصلت كاملةً**
  /// — عطلٌ ظهر حرفياً: الخادم يردّ 200 بـ٢٨٦٨ بايت والشاشة تقول خطأ.
  ///
  /// فمن عجز عن حفظ نسخةٍ يبقى عنده الأصل. والعجز يُكتب في سجلّ التطوير ولا
  /// يُبتلع صامتاً (المادة ٢-٢): تخزينُ متصفّحٍ ممتلئ أو وضعٌ متدهور يجب أن
  /// يُقرأ اسمُه، لا أن يُخمَّن.
  @override
  Future<void> write(
    String key,
    String rawJson, {
    required DateTime fetchedAtUtc,
  }) async {
    try {
      await _database
          .into(_database.cachedDocuments)
          .insertOnConflictUpdate(
            CachedDocumentRow(
              key: key,
              payload: rawJson,
              fetchedAtUtcMillis: fetchedAtUtc.toUtc().millisecondsSinceEpoch,
            ),
          );
    } on Object catch (error) {
      assert(() {
        // ignore: avoid_print
        print('تعذّر حفظ الكاش «$key»: $error');
        return true;
      }());
    }
  }

  /// والمحو كذلك: تنظيفٌ فاشل لا يمنع خروجاً من الحساب.
  @override
  Future<void> clear() async {
    try {
      await _database.delete(_database.cachedDocuments).go();
    } on Object catch (error) {
      assert(() {
        // ignore: avoid_print
        print('تعذّر محو الكاش: $error');
        return true;
      }());
    }
  }
}
