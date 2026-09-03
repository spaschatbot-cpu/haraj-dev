import '../../core/environment.dart';
import '../../l10n/generated/app_localizations.dart';

/// اسم البيئة بالعربية — تعريف واحد يقرأ منه كل ما يعرّف بالبيئة.
///
/// له قارئان: لافتة `EnvironmentBanner`، وختم البيئة على كل رسالة تظهر للمستخدم
/// في بناء غير إنتاجي. اسمان مكتوبان في مكانين يفترقان، فيقرأ المختبِر «تجريب»
/// على اللافتة و«staging» في الرسالة ويظنّهما بيئتين (المادة ٤-٥).
String environmentLabel(AppLocalizations l10n, AppEnvironment environment) =>
    switch (environment) {
      AppEnvironment.development => l10n.environmentDevelopment,
      AppEnvironment.staging => l10n.environmentStaging,
      AppEnvironment.production => l10n.environmentProduction,
    };
