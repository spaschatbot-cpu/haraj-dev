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

  @override
  Future<void> write(
    String key,
    String rawJson, {
    required DateTime fetchedAtUtc,
  }) => _database
      .into(_database.cachedDocuments)
      .insertOnConflictUpdate(
        CachedDocumentRow(
          key: key,
          payload: rawJson,
          fetchedAtUtcMillis: fetchedAtUtc.toUtc().millisecondsSinceEpoch,
        ),
      );

  @override
  Future<void> clear() => _database.delete(_database.cachedDocuments).go();
}
