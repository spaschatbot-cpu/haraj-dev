import 'package:flutter/material.dart';

import '../../core/environment.dart';
import '../../l10n/generated/app_localizations.dart';
import 'environment_label.dart';

/// لافتة تعرّف البيئة في كل بناء غير إنتاجي.
///
/// المادة ٥-٦: كل بيئة تعرف نفسها، حتى لا يظنّ مختبِر أنه على التجريب وهو على
/// الإنتاج. اللافتة هنا هي **الحد الأدنى الدستوري**؛ تاسك T718 يبقى مفتوحاً
/// لأنه يشمل بناء الإصدار والتوقيع وإظهارها في مخرجات المتجرين.
class EnvironmentBanner extends StatelessWidget {
  const EnvironmentBanner({
    required this.environment,
    required this.child,
    super.key,
  });

  final AppEnvironment environment;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    if (!environment.showsBanner) return child;

    final l10n = AppLocalizations.of(context);

    return Banner(
      message: l10n.environmentBanner(environmentLabel(l10n, environment)),
      location: BannerLocation.topStart,
      child: child,
    );
  }
}
