import 'package:flutter/material.dart';

import '../../../domain/activity/entities/participation.dart';
import '../../../domain/common/money.dart';
import '../../../l10n/generated/app_localizations.dart';
import '../../common/money_text.dart';
import '../../common/saudi_time.dart';

/// مزاد دخله العميل، وحالة تأمينه فيه.
///
/// حالة التأمين تُعرض **بنصّ الخادم** ومعها مبلغها. الإبراز البصري وحده يُشتقّ
/// من الحالة المسمّاة — لا نصّ عندنا لحالة يعرفها الخادم، ولا استنتاج للحالة
/// من المبلغ.
class ParticipationCard extends StatelessWidget {
  const ParticipationCard({required this.participation, super.key});

  final Participation participation;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final theme = Theme.of(context);
    final money = participation.insuranceMoney;

    return Card(
      margin: const EdgeInsets.symmetric(vertical: 6),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Text(
              participation.auctionTitle,
              style: theme.textTheme.titleMedium,
            ),
            const SizedBox(height: 4),
            Text(
              participation.auctionStatusLabel,
              style: theme.textTheme.bodySmall,
            ),
            Text(
              l10n.participationEndsAt(
                SaudiTime.forDisplay(participation.endsAt),
                SaudiTime.forDisplay(participation.endsAt),
              ),
              style: theme.textTheme.bodySmall,
            ),
            Text(
              l10n.participationBidsCount(participation.bidsCount),
              style: theme.textTheme.bodySmall,
            ),
            const SizedBox(height: 12),
            _InsuranceRow(
              state: participation.insuranceState,
              label: participation.insuranceStateLabel,
              money: money,
            ),
          ],
        ),
      ),
    );
  }
}

class _InsuranceRow extends StatelessWidget {
  const _InsuranceRow({
    required this.state,
    required this.label,
    required this.money,
  });

  final InsuranceState state;
  final String label;

  /// يغيب حين لا تأمين مرتبطاً بهذا المزاد — فلا يُعرض رقم بلا معنى.
  final Money? money;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final theme = Theme.of(context);
    final scheme = theme.colorScheme;
    final amount = money;
    final (background, foreground) = switch (state) {
      InsuranceState.locked => (scheme.errorContainer, scheme.onErrorContainer),
      InsuranceState.held => (
        scheme.secondaryContainer,
        scheme.onSecondaryContainer,
      ),
      InsuranceState.released ||
      InsuranceState.none ||
      InsuranceState.unknown => (
        scheme.surfaceContainerHighest,
        scheme.onSurfaceVariant,
      ),
    };

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: background,
        borderRadius: BorderRadius.circular(8),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(
            l10n.insuranceInThisAuction,
            style: theme.textTheme.labelMedium?.copyWith(color: foreground),
          ),
          const SizedBox(height: 4),
          Text(
            label,
            style: theme.textTheme.bodyMedium?.copyWith(color: foreground),
          ),
          if (amount != null) ...<Widget>[
            const SizedBox(height: 4),
            MoneyText(
              amount,
              style: theme.textTheme.titleSmall?.copyWith(color: foreground),
            ),
          ],
        ],
      ),
    );
  }
}
