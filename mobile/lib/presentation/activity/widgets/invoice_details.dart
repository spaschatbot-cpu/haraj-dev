import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../app/providers.dart';
import '../../../domain/activity/entities/invoice.dart';
import '../../../domain/common/failure.dart';
import '../../../domain/common/money.dart';
import '../../../l10n/generated/app_localizations.dart';
import '../../common/failure_message.dart';
import '../../common/money_text.dart';
import '../../common/saudi_time.dart';
import '../activity_providers.dart';

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
        if (_isPayable(invoice)) ...<Widget>[
          const SizedBox(height: 12),
          _PayFromBalanceButton(invoice: invoice),
        ],
      ],
    );
  }
}

/// أتقبل هذه الفاتورةُ سداداً الآن؟
///
/// **الحالةُ من الخادم لا من المبلغ.** كان يُغري أن يُقرأ «الباقي أكبر من صفر»
/// وحدَه، لكنّ فاتورةً ملغاةً قد تحمل باقياً غيرَ مصفَّر، وزرُّ سدادٍ عليها
/// وعدٌ يكسره الخادم بعد الضغطة. فالشرطان معاً: حالةٌ تقبل الدفع، ومبلغٌ
/// يستحقّ الدفع.
bool _isPayable(Invoice invoice) {
  final state = invoice.state;
  if (state != InvoiceState.open && state != InvoiceState.partiallyPaid) {
    return false;
  }
  return (double.tryParse(invoice.due.amount) ?? 0) > 0;
}

/// زرُّ السداد من رصيد التأمين.
///
/// **والخلفيةُ هي التي تقرّر**: تقيّد الدفعة وتنقل المركبةَ وتفكّ ما رُهن في
/// بابٍ واحد (`bidding.settlement`). فهذا الزرّ ينادي وينتظر ويعرض، ولا يحسب
/// مبلغاً ولا يفترض نتيجة — ولا يُحدِّث الشاشة من عنده بل يُبطل المزوّدات
/// فتُقرأ من الخادم من جديد.
class _PayFromBalanceButton extends ConsumerStatefulWidget {
  const _PayFromBalanceButton({required this.invoice});

  final Invoice invoice;

  @override
  ConsumerState<_PayFromBalanceButton> createState() =>
      _PayFromBalanceButtonState();
}

class _PayFromBalanceButtonState extends ConsumerState<_PayFromBalanceButton> {
  bool _sending = false;

  Future<void> _pay() async {
    final l10n = AppLocalizations.of(context);
    final messenger = ScaffoldMessenger.of(context);
    final invoice = widget.invoice;

    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(l10n.invoicePayConfirmTitle),
        content: Text(
          l10n.invoicePayConfirmBody(
            '${invoice.due.amount} ${invoice.due.currency}',
            invoice.number,
          ),
        ),
        actions: <Widget>[
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: Text(l10n.cancel),
          ),
          FilledButton(
            onPressed: () => Navigator.of(context).pop(true),
            child: Text(l10n.invoicePayAction),
          ),
        ],
      ),
    );
    if (!(confirmed ?? false) || !mounted) return;

    setState(() => _sending = true);
    try {
      await ref.read(payInvoiceFromBalanceProvider)(invoice.id);
      // الثلاثةُ معاً: الفاتورةُ صارت مسدَّدة، والمركبةُ صارت شراءً، والرصيدُ
      // نقص. وإبطالُ واحدٍ منها يترك الشاشتين الأخريين تكذبان.
      ref
        ..invalidate(myInvoicesProvider)
        ..invalidate(myPurchasesProvider);
      if (!mounted) return;
      messenger.showSnackBar(SnackBar(content: Text(l10n.invoicePaid)));
    } on Failure catch (failure) {
      // جوابُ الخادم كما جاء: «رصيدك لا يكفي»، «الفاتورة مسدَّدة»… وأيٌّ منها
      // أوضح من «تعذّر السداد» التي كنّا سنكتبها نحن.
      if (!mounted) return;
      messenger.showSnackBar(
        SnackBar(content: Text(failureMessage(context, failure))),
      );
    } finally {
      if (mounted) setState(() => _sending = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);

    return SizedBox(
      width: double.infinity,
      child: FilledButton(
        // **يُعطَّل أثناء الإرسال**: ضغطتان على زرِّ دفعٍ ضغطتان على المال،
        // ولا يُترك ذلك لحارس التكرار في الخلفية وحدَه.
        onPressed: _sending ? null : _pay,
        child: _sending
            ? const SizedBox(
                height: 16,
                width: 16,
                child: CircularProgressIndicator(strokeWidth: 2),
              )
            : Text(l10n.invoicePayAction),
      ),
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
