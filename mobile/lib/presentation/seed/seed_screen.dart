import 'package:flutter/material.dart';

import '../../l10n/generated/app_localizations.dart';

/// شاشة البذرة — **مؤقّتة بالكامل**.
///
/// وجودها لسبب واحد: أن يقلع التطبيق ويُثبت أن الأساس يعمل (العربية والاتجاه،
/// والثيم، والتوجيه). شاشات المنتج الحقيقية هي المجموعة ب من الفيز 008
/// (T706 وما بعده)، ولا تبدأ قبل تثبيت مخطط الـAPI في T621 — نقطة التزامن «ب»
/// في خطة الفريق.
///
/// أول شاشة حقيقية تُدمَج تحذف هذا الملف ومساره من `router.dart`.
class SeedScreen extends StatelessWidget {
  const SeedScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return Scaffold(
      appBar: AppBar(title: Text(l10n.seedTitle)),
      body: Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Text(
            l10n.seedBody,
            textAlign: TextAlign.center,
            style: Theme.of(context).textTheme.bodyLarge,
          ),
        ),
      ),
    );
  }
}
