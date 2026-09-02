/// وصف البيئة التي بُني عليها هذا التطبيق.
///
/// كل القيم تأتي من `--dart-define` وقت البناء، ولا شيء منها مكتوب في الكود:
/// المادة ٥-٣ من الدستور تمنع الأسرار وعناوين البيئات داخل المستودع.
library;

/// اسم البيئة كما يعرفها التشغيل. المادة ٥-٦: كل بيئة تعرف نفسها.
enum AppEnvironment {
  development,
  staging,
  production;

  static AppEnvironment parse(String raw) => switch (raw.toLowerCase()) {
    'production' || 'prod' => AppEnvironment.production,
    'staging' => AppEnvironment.staging,
    _ => AppEnvironment.development,
  };

  /// اللافتة تظهر في كل بناء غير إنتاجي (T718 يبنى على هذا).
  bool get showsBanner => this != AppEnvironment.production;
}

/// إعدادات البناء — تُقرأ مرة واحدة، ولا تُقرأ `String.fromEnvironment` في أي
/// مكان آخر (المادة ٤-٥: نقطة قرار واحدة).
final class AppConfig {
  const AppConfig({required this.environment, required this.apiBaseUrl});

  /// القيم الافتراضية تشير إلى بيئة تطوير محلية، فبناء بلا `--dart-define`
  /// لا يمكن أن يصيب الإنتاج بالخطأ.
  factory AppConfig.fromBuild() => AppConfig(
    environment: AppEnvironment.parse(
      const String.fromEnvironment('HARAJ_ENV', defaultValue: 'development'),
    ),
    apiBaseUrl: const String.fromEnvironment(
      'HARAJ_API_BASE_URL',
      defaultValue: 'http://10.0.2.2:8000',
    ),
  );

  final AppEnvironment environment;
  final String apiBaseUrl;
}
