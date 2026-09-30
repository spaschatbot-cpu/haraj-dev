import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

/// هل رأى هذا الجهازُ صفحاتِ الترحيب؟ — **مرّةً واحدةً في عمر التثبيت.**
///
/// بأمر المالك (٣٠ سبتمبر ٢٠٢٦): «الأونبوردنج سكرينز ما تظهرش كلّ مرّة…
/// تظهر في المرّة الأولى بس». كانت شاشةُ البدء تفتح الترحيبَ في كلّ إقلاع،
/// فيمرّ العميلُ العائدُ بصفحتين يعرفهما قبل أن يصل إلى المزاد.
///
/// **في التخزين الآمن لا في كاش drift**: الكاشُ يُمسح حين يُفرَّغ أو تتغيّر
/// بنيتُه، ومسحُه كان سيعيد الترحيبَ لمن رآه. والعلمُ ليس سرّاً، لكن التخزين
/// الآمن هو التخزينُ الدائم الوحيد في التبعيّات (لا `shared_preferences`).
/// ويُمسح مع حذف التطبيق — وذلك «أوّلُ مرّة» من جديد، كما يُنتظر.
final class OnboardingStore {
  OnboardingStore(this._storage);

  factory OnboardingStore.platformDefault() => OnboardingStore(
    const FlutterSecureStorage(
      aOptions: AndroidOptions(storageNamespace: 'haraj_prefs'),
    ),
  );

  static const String _seenKey = 'haraj.onboarding_seen';

  final FlutterSecureStorage _storage;

  /// تخزينٌ لا يجيب (عطبٌ في Keystore على بعض الأجهزة) يُقرأ «لم يُرَ» —
  /// ترحيبٌ زائدٌ مرّةً أهونُ من شاشة بدءٍ معلّقة.
  Future<bool> seen() async {
    try {
      return await _storage.read(key: _seenKey) == '1';
    } on Object {
      return false;
    }
  }

  Future<void> markSeen() async {
    try {
      await _storage.write(key: _seenKey, value: '1');
    } on Object {
      // لا يُوقف الترحيبَ فشلُ حفظ علمه: أسوأُ ما يحدث أن يظهر مرّةً أخرى.
    }
  }
}

final onboardingStoreProvider = Provider<OnboardingStore>(
  (ref) => OnboardingStore.platformDefault(),
);
