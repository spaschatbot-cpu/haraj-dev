import 'package:flutter/material.dart';

import '../../../domain/activity/entities/invoice.dart';
import '../../../domain/common/money.dart';
import '../../../l10n/generated/app_localizations.dart';
import '../../common/money_text.dart';
import '../../common/saudi_time.dart';

/// عرض فاتورة واحدة: رقمها وحالتها ومبالغها وأثرها على التأمين.
///
/// **مكان واحد لعرض الفاتورة** تستعمله «فواتيري» و«مشترياتي» معاً. الفاتورة
/// تظهر في شاشتين، وشكلان لها هما بداية اختلافهما (المادة ٤-٥).
///
/// ثلاثة أشياء لا تُفعل هنا بالتحديد:
/// * **الحالة لا تُشتق** من `total` و`paid`. تصل من الخادم مسمّاة وتُعرض كما
///   وصلت. في v1 كان عمود الحالة مجمّداً منذ الإدراج، فقرأت كل شاشة تفرّعت
///   عليه قيمة ميتة — والعلاج نقطة اشتقاق واحدة، لا اشتقاق في كل شاشة.
/// * **المتبقّي لا يُطرح** — يصل محسوباً (`due_amount`).
/// * **شرح أثر الفاتورة على التأمين لا يُكتب هنا.** نصّه من الخادم: من كتب
///   القاعدة كتب شرحها، وصياغة ثانية عندنا تنحرف عنها فيسمع العميل جوابين.
class InvoiceDetails extends StatelessWidget {
  const InvoiceDetails({required this.invoice, super.key});

  final Invoice invoice;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final theme = Theme.of(context);
    final lock = invoice.insuranceLock;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        Row(
          children: <Widget>[
            Expanded(
              child: Text(
                l10n.invoiceNumber(invoice.number),
                style: theme.textTheme.titleSmall,
              ),
            ),
            _StateChip(label: invoice.stateLabel, state: invoice.state),
          ],
        ),
        const SizedBox(height: 4),
        Text(
          l10n.invoiceIssuedAt(SaudiTime.forDisplay(invoice.issuedAt)),
          style: theme.textTheme.bodySmall,
        ),
        const SizedBox(height: 8),
        _AmountRow(label: l10n.invoiceTotal, money: invoice.total),
        _AmountRow(label: l10n.invoicePaid, money: invoice.paid),
        _AmountRow(
          label: l10n.invoiceDue,
          money: invoice.due,
          emphasised: true,
        ),
        if (lock != null) ...<Widget>[
          const SizedBox(height: 8),
          _InsuranceLockNote(lock: lock),
        ],
      ],
    );
  }
}

/// شرح ما تعنيه الفاتورة لتأمين صاحبها — بنصّ الخادم وبمبلغه.
///
/// يظهر حين يرسله الخادم فقط. غيابه لا يُملأ بنصّ عندنا: أكثر ما أربك عملاء v1
/// رصيد يرونه ولا يستطيعون سحبه بلا سبب معروض، وسببٌ مخترع في الشاشة يعيد
/// المشكلة بصياغة ألطف.
class _InsuranceLockNote extends StatelessWidget {
  const _InsuranceLockNote({required this.lock});

  final InsuranceLock lock;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final theme = Theme.of(context);

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: theme.colorScheme.secondaryContainer,
        borderRadius: BorderRadius.circular(8),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(
            l10n.invoiceInsuranceEffect,
            style: theme.textTheme.labelLarge?.copyWith(
              color: theme.colorScheme.onSecondaryContainer,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            lock.note,
            style: theme.textTheme.bodyMedium?.copyWith(
              color: theme.colorScheme.onSecondaryContainer,
            ),
          ),
          const SizedBox(height: 4),
          MoneyText(
            lock.money,
            style: theme.textTheme.titleSmall?.copyWith(
              color: theme.colorScheme.onSecondaryContainer,
            ),
          ),
        ],
      ),
    );
  }
}

class _AmountRow extends StatelessWidget {
  const _AmountRow({
    required this.label,
    required this.money,
    this.emphasised = false,
  });

  final String label;
  final Money money;
  final bool emphasised;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final style = emphasised
        ? theme.textTheme.titleSmall
        : theme.textTheme.bodyMedium;

    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 2),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: <Widget>[
          Text(label, style: theme.textTheme.bodyMedium),
          MoneyText(money, style: style),
        ],
      ),
    );
  }
}

/// إبراز بصري مشتقّ من الحالة **المسمّاة من الخادم** — لا من مقارنة مبالغ.
class _StateChip extends StatelessWidget {
  const _StateChip({required this.label, required this.state});

  final String label;
  final InvoiceState state;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final (background, foreground) = switch (state) {
      InvoiceState.paid => (
        scheme.tertiaryContainer,
        scheme.onTertiaryContainer,
      ),
      InvoiceState.open || InvoiceState.partiallyPaid => (
        scheme.errorContainer,
        scheme.onErrorContainer,
      ),
      InvoiceState.cancelled || InvoiceState.unknown => (
        scheme.surfaceContainerHighest,
        scheme.onSurfaceVariant,
      ),
    };

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: background,
        borderRadius: BorderRadius.circular(12),
      ),
      child: Text(
        label,
        style: Theme.of(
          context,
        ).textTheme.labelMedium?.copyWith(color: foreground),
      ),
    );
  }
}
