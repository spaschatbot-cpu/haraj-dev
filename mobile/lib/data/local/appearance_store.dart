import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

/// «المظهر» على هذا الجهاز: ما اختاره العميل، وآخرُ ما قالته الإدارة.
///
/// **اختيارُ العميل تفضيلُ جهازٍ لا تفضيلُ حساب** — حجّةُ لوحة الموظّفين نفسُها
/// (`theme.js`): يريد الداكنَ على هاتفه ليلاً ولا يريده على جهازٍ آخر. ويبقى بعد
/// الخروج من الحساب، كما يبقى في اللوحة.
///
/// **ومظهرُ الإدارة يُحفظ هنا أيضاً** (`GET /api/v1/appearance/`): التطبيقُ
/// يُفتح بلا شبكةٍ أحياناً، وبلا نسخةٍ محفوظةٍ كان سيُرسم كحليّاً ثمّ يقلب إلى
/// لون الإدارة حين يصل الجواب — أو يبقى كحليّاً حتى تعود الشبكة.
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
  static const String _serverKey = 'haraj.look.server';

  final FlutterSecureStorage _storage;

  /// اختيارُ العميل — كلُّ مفتاحٍ وحدَه: من غيّر اللونَ ولم يلمس الإضاءة تبقى
  /// إضاءتُه ما تقوله الإدارة.
  Future<({String? scheme, String? accent})> readChoice() async =>
      (scheme: await _read(_schemeKey), accent: await _read(_accentKey));

  Future<void> writeScheme(String scheme) => _write(_schemeKey, scheme);

  Future<void> writeAccent(String accent) => _write(_accentKey, accent);

  /// آخرُ مظهرٍ قالته الإدارة، سطراً واحداً: `accent|mode|1` أو `…|0`.
  Future<String?> readServer() => _read(_serverKey);

  Future<void> writeServer(String line) => _write(_serverKey, line);

  /// تخزينٌ لا يجيب يُقرأ «لا شيء محفوظ» — التطبيقُ بمظهره الافتراضيّ أهونُ من
  /// شاشة بدءٍ معلّقة.
  Future<String?> _read(String key) async {
    try {
      return await _storage.read(key: key);
    } on Object {
      return null;
    }
  }

  Future<void> _write(String key, String value) async {
    try {
      await _storage.write(key: key, value: value);
    } on Object {
      // فشلُ الحفظ لا يُلغي الاختيار: يبقى حتى يُغلق التطبيق.
    }
  }
}

final appearanceStoreProvider = Provider<AppearanceStore>(
  (ref) => AppearanceStore.platformDefault(),
);
