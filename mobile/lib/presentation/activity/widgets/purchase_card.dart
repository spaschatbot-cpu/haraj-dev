import 'package:flutter/material.dart';

import '../../../domain/activity/entities/purchase.dart';
import '../../../l10n/generated/app_localizations.dart';
import '../../common/money_text.dart';
import '../../common/saudi_time.dart';
import 'invoice_details.dart';

/// مركبة رست على العميل، وحالتها، وفاتورتها إن صدرت.
///
/// الفاتورة تُعرض بنفس `InvoiceDetails` التي يعرضها تبويب «فواتيري» — فما يراه
/// العميل عن فاتورة واحدة واحدٌ أينما رآها، بما فيه أثرها على تأمينه.
class PurchaseCard extends StatelessWidget {
  const PurchaseCard({required this.purchase, super.key});

  final Purchase purchase;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final theme = Theme.of(context);
    final invoice = purchase.invoice;

    return Card(
      margin: const EdgeInsets.symmetric(vertical: 6),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Row(
              children: <Widget>[
                Expanded(
                  child: Text(
                    purchase.title,
                    style: theme.textTheme.titleMedium,
                  ),
                ),
                Text(
                  purchase.stateLabel,
                  style: theme.textTheme.labelMedium?.copyWith(
                    color: theme.colorScheme.onSurfaceVariant,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 4),
            Text(
              l10n.purchaseLotNumber(purchase.lotNumber),
              style: theme.textTheme.bodySmall,
            ),
            Text(purchase.auctionTitle, style: theme.textTheme.bodySmall),
            Text(
              l10n.purchaseAwardedAt(SaudiTime.forDisplay(purchase.awardedAt)),
              style: theme.textTheme.bodySmall,
            ),
            const SizedBox(height: 8),
            MoneyText(purchase.awardedPrice, style: theme.textTheme.titleSmall),
            const Divider(height: 24),
            if (invoice == null)
              Text(l10n.purchaseNoInvoiceYet, style: theme.textTheme.bodyMedium)
            else
              InvoiceDetails(invoice: invoice),
          ],
        ),
      ),
    );
  }
}
