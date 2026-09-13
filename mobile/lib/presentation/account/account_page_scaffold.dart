import 'package:flutter/material.dart';

import '../../l10n/generated/app_localizations.dart';
import '../common/haraj_app_bar.dart';

/// قشرةٌ مشتركة لصفحات «حسابي» الجديدة (١٣ سبتمبر ٢٠٢٦).
///
/// كلُّ صفحةٍ في القائمة تُبنى فوق هذه القشرة: شريطُ عنوانٍ بزرِّ رجوع، وجسمٌ
/// يُملأ لاحقاً. الجسمُ الافتراضيُّ نصٌّ مؤقّت — يُستبدل بمحتوى الصفحة حين
/// يحدّده المالك، صفحةً صفحةً، بلا لمسِ القائمة ولا التوجيه.
///
/// **قشرةٌ واحدة لا عشرُ نُسخ** (المادة ٤-٥): الشريطُ وزرُّ الرجوع والحشوةُ
/// معرّفةٌ مرّةً، فلا تفترق صفحةٌ عن أختها في هيئتها حين يُملأ محتواها.
class AccountPageScaffold extends StatelessWidget {
  const AccountPageScaffold({required this.title, this.child, super.key});

  /// عنوانُ الصفحة في شريطها.
  final String title;

  /// محتوى الصفحة. حين يكون `null` يظهر النصُّ المؤقّت — الحالةُ الأولى لكل
  /// صفحةٍ قبل أن يُملأ محتواها.
  final Widget? child;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return Scaffold(
      appBar: HarajAppBar(title: title),
      body:
          child ??
          Center(
            child: Padding(
              padding: const EdgeInsets.all(24),
              child: Text(
                l10n.accountPageComingSoon,
                textAlign: TextAlign.center,
                style: Theme.of(context).textTheme.bodyLarge,
              ),
            ),
          ),
    );
  }
}
