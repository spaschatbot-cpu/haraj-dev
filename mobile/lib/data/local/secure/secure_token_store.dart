import 'package:flutter_secure_storage/flutter_secure_storage.dart';

/// مخزن رمزي الوصول والتحديث.
///
/// **الرموز في التخزين الآمن وحده** (Keystore على أندرويد، Keychain على iOS) —
/// لا في drift ولا في SharedPreferences ولا في أي ملف. نسخة احتياطية للجهاز أو
/// وصول جذر إلى مجلد التطبيق تكشف قاعدة SQLite كاملةً؛ ولا تكشف هذه.
///
/// اختبار `test/architecture/secrets_stay_in_secure_storage_test.dart` يفرض
/// القاعدة نصّياً، فلا تعتمد على التذكّر.
final class SecureTokenStore {
  SecureTokenStore(this._storage);

  /// `first_unlock` لا `always`: الرمز لا يُقرأ قبل أن يفتح صاحب الجهاز قفله
  /// مرة واحدة بعد الإقلاع — جهاز مسروق ومطفأ لا يسلّم جلسة.
  ///
  /// و`storageNamespace` يفصل مفاتيحنا عن أي حزمة أخرى داخل التطبيق.
  factory SecureTokenStore.platformDefault() => SecureTokenStore(
    const FlutterSecureStorage(
      aOptions: AndroidOptions(storageNamespace: 'haraj_tokens'),
      iOptions: IOSOptions(accessibility: KeychainAccessibility.first_unlock),
    ),
  );

  static const String _accessKey = 'haraj.access_token';
  static const String _refreshKey = 'haraj.refresh_token';

  final FlutterSecureStorage _storage;

  Future<String?> readAccessToken() => _storage.read(key: _accessKey);

  Future<String?> readRefreshToken() => _storage.read(key: _refreshKey);

  Future<void> save({required String access, required String refresh}) async {
    await _storage.write(key: _accessKey, value: access);
    await _storage.write(key: _refreshKey, value: refresh);
  }

  Future<void> clear() async {
    await _storage.delete(key: _accessKey);
    await _storage.delete(key: _refreshKey);
  }

  Future<bool> hasSession() async => await readRefreshToken() != null;
}
