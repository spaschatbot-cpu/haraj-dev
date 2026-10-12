import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

/// اختيارُ «المظهر» على هذا الجهاز: الإضاءةُ واللونُ الأساسيّ.
///
/// **تفضيلُ جهازٍ لا تفضيلُ حساب** — حجّةُ لوحة الموظّفين نفسُها (`theme.js`):
/// العميلُ يريد الداكنَ على هاتفه ليلاً ولا يريده على جهازٍ آخر، وحفظُه في
/// الخادم حقلٌ وهجرةٌ وطلبُ كتابةٍ عند كلّ نقرةٍ على عيّنة لون. ويبقى بعد
/// الخروج من الحساب، كما يبقى في اللوحة.
///
/// **في التخزين الآمن** لأنه التخزينُ الدائم الوحيد في التبعيّات — كعلم
/// الترحيب في [OnboardingStore]، وبالمساحة نفسِها.
final class AppearanceStore {
  AppearanceStore(this._storage);

  factory AppearanceStore.platformDefault() => AppearanceStore(
    const FlutterSecureStorage(
      aOptions: AndroidOptions(storageNamespace: 'haraj_prefs'),
    ),
  );

  static const String _schemeKey = 'haraj.look.scheme';
  static const String _accentKey = 'haraj.look.accent';

  final FlutterSecureStorage _storage;

  /// تخزينٌ لا يجيب يُقرأ «لم يُختَر شيء» — التطبيقُ بمظهره الافتراضيّ أهونُ
  /// من شاشة بدءٍ معلّقة.
  Future<({String? scheme, String? accent})> read() async {
    try {
      return (
        scheme: await _storage.read(key: _schemeKey),
        accent: await _storage.read(key: _accentKey),
      );
    } on Object {
      return (scheme: null, accent: null);
    }
  }

  Future<void> write({required String scheme, required String accent}) async {
    try {
      await _storage.write(key: _schemeKey, value: scheme);
      await _storage.write(key: _accentKey, value: accent);
    } on Object {
      // فشلُ الحفظ لا يُلغي الاختيار: يبقى حتى يُغلق التطبيق ويرجع بعدها.
    }
  }
}

final appearanceStoreProvider = Provider<AppearanceStore>(
  (ref) => AppearanceStore.platformDefault(),
);
