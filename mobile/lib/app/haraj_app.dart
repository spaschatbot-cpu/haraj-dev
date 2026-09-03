import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../l10n/generated/app_localizations.dart';
import '../presentation/common/environment_banner.dart';
import 'providers.dart';
import 'router.dart';
import 'theme.dart';

/// جذر واجهة التطبيق.
///
/// **العربية والاتجاه ليسا طبقة تُضاف لاحقاً** (T703): اللغة مثبَّتة على
/// العربية، ومنها يشتقّ Flutter اتجاه RTL لكل الشجرة عبر
/// `GlobalWidgetsLocalizations`. لا `Directionality` يدوية في أي شاشة — لو
/// احتاجت شاشة أن تفرض اتجاهها فذلك عيب فيها، لا استثناء يُضاف هنا.
class HarajApp extends ConsumerWidget {
  const HarajApp({this.locale = const Locale('ar'), super.key});

  /// العربية هي الأصل. المعامل موجود لاختبارات الـwidget التي تقارن الاتجاهين،
  /// ولا يُغيَّر من داخل التطبيق.
  final Locale locale;

  /// نافذة عرض الرسائل من خارج شجرة الويدجت.
  ///
  /// إشعارُ المقدمة يصل من مجرى لا من ضغطة زرّ، فلا `BuildContext` معه. المفتاح
  /// يعطي `PushCoordinator` مكاناً واحداً معروفاً يعرض فيه، بدل تمرير سياق
  /// عبر طبقات (T716).
  static final GlobalKey<ScaffoldMessengerState> messengerKey =
      GlobalKey<ScaffoldMessengerState>();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final config = ref.watch(appConfigProvider);

    return MaterialApp.router(
      scaffoldMessengerKey: messengerKey,
      onGenerateTitle: (context) => AppLocalizations.of(context).appTitle,
      locale: locale,
      localizationsDelegates: AppLocalizations.localizationsDelegates,
      supportedLocales: AppLocalizations.supportedLocales,
      theme: HarajTheme.light(),
      darkTheme: HarajTheme.dark(),
      routerConfig: ref.watch(routerProvider),
      debugShowCheckedModeBanner: false,
      builder: (context, child) => EnvironmentBanner(
        environment: config.environment,
        child: child ?? const SizedBox.shrink(),
      ),
    );
  }
}
