import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../l10n/generated/app_localizations.dart';
import '../presentation/common/glass.dart';
import 'appearance.dart';
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
    final appearance = ref.watch(appearanceProvider);
    return MaterialApp.router(
      scaffoldMessengerKey: messengerKey,
      onGenerateTitle: (context) => AppLocalizations.of(context).appTitle,
      locale: locale,
      localizationsDelegates: AppLocalizations.localizationsDelegates,
      supportedLocales: AppLocalizations.supportedLocales,
      // **من «المظهر» في حسابي** (طلبُ المالك، ١٢ أكتوبر ٢٠٢٦): الإضاءةُ
      // واللونُ كدرج المظهر في لوحة الموظّفين. والافتراضُ فاتحٌ كحليّ — كان
      // «فاتحاً دائماً» بأمره (٢٩ سبتمبر) لأن التطبيق كان يتبع الجهاز فيراه
      // صاحبُ هاتفٍ داكنٍ بلونٍ غير الذي صُمّم؛ فالداكنُ الآن لمن يختاره بيده.
      theme: HarajTheme.light(appearance.accent),
      darkTheme: HarajTheme.dark(appearance.accent),
      themeMode: appearance.mode,
      routerConfig: ref.watch(routerProvider),
      builder: (context, child) =>
          GlassBackdrop(child: child ?? const SizedBox.shrink()),
      debugShowCheckedModeBanner: false,
      // **لافتةُ البيئة مُطفأة بقرار المالك (٩ سبتمبر ٢٠٢٦).**
      //
      // كانت هنا `EnvironmentBanner` تلفّ الشجرة كلها، وهي الحدّ الأدنى الذي
      // تطلبه المادة ٥-٦: كل بيئةٍ تعرف نفسها، حتى لا يظنّ مختبِرٌ أنه على
      // التجريب وهو على الإنتاج. ورُفعت لأنها تقطع زاوية الهيدر في المعاينة.
      //
      // **والثمن مذكور:** بناءُ التجريب صار لا يُميَّز عن بناء الإنتاج بالنظر.
      // والمكوّن باقٍ في `presentation/common/environment_banner.dart` بلا
      // مستعمل — إعادتُه سطرٌ واحد يُردّ هنا، لا كتابةٌ من جديد. و`T718` ما
      // زال مفتوحاً على تعريف البيئة في مخرجات المتجرين.
    );
  }
}
