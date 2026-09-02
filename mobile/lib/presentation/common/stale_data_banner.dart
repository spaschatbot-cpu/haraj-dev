import 'package:flutter/material.dart';

import '../../domain/common/snapshot.dart';
import '../../l10n/generated/app_localizations.dart';
import 'saudi_time.dart';

/// علامة «آخر تحديث» فوق أي شاشة تعرض بيانات من الكاش (معيار القبول H5).
///
/// تظهر عند `isStale` فقط. قاعدة العرض 7 في الفيز 008: فقد الاتصال يعرض آخر
/// بيانات معروفة **مع علامة**، لا شاشة خطأ — لكن بلا العلامة يقرأ المستخدم
/// رصيداً قديماً على أنه الحالي، وهذا أسوأ من شاشة الخطأ.
class StaleDataBanner extends StatelessWidget {
  const StaleDataBanner({required this.snapshot, super.key});

  final Snapshot<Object?> snapshot;

  @override
  Widget build(BuildContext context) {
    if (!snapshot.isStale) return const SizedBox.shrink();

    final l10n = AppLocalizations.of(context);
    final shownAt = SaudiTime.forDisplay(snapshot.fetchedAt);
    final theme = Theme.of(context);

    return Container(
      width: double.infinity,
      color: theme.colorScheme.secondaryContainer,
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      child: Text(
        l10n.offlineDataNotice(shownAt, shownAt),
        style: theme.textTheme.bodySmall?.copyWith(
          color: theme.colorScheme.onSecondaryContainer,
        ),
      ),
    );
  }
}
