import 'package:flutter/material.dart';

import '../../domain/bidding/entities/bid_outcome.dart';
import '../../l10n/generated/app_localizations.dart';
import '../common/money_text.dart';

/// حوار «أكّد الخفض» — خطوة مقصودة، لا زرّ في مكان الزرّ الأول.
///
/// الخفض ميزة حقيقية في المزاد المغلق، وهو أيضاً ما تفعله إصبعٌ زائغة. لذلك
/// يرفض الخادم المحاولة الأولى ويقبل الثانية بتأكيد (F3)، ولذلك:
///
/// * **الحوار يذكر المبلغين** كما وصلا في حمولة الرفض نفسه، لا بقراءة جديدة —
///   الرقم الذي يوقّع عليه العميل يجب أن يكون الرقم الذي كان الرفض عنه.
/// * **مربّع الاختيار يبدأ فارغاً**، والزرّ معطَّل حتى يُؤشَّر. مربّعٌ مؤشَّر
///   سلفاً ليس تأكيداً، بل المحاولة الأولى ومعها حقل زائد.
/// * **الزرّ ليس في موضع «زايد»** ولا بنصّه: حوارٌ يظهر فوق الشاشة يقطع إيقاع
///   النقر المتتابع الذي تمرّ منه الأخطاء.
class LowerBidConfirmationDialog extends StatefulWidget {
  const LowerBidConfirmationDialog({required this.request, super.key});

  final BidNeedsLowerConfirmation request;

  @override
  State<LowerBidConfirmationDialog> createState() =>
      _LowerBidConfirmationDialogState();
}

class _LowerBidConfirmationDialogState
    extends State<LowerBidConfirmationDialog> {
  bool _confirmed = false;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final theme = Theme.of(context);

    return AlertDialog(
      title: Text(l10n.bidLowerConfirmTitle),
      // قابل للتمرير: خطّ نظام كبير على جوال صغير يجعل المحتوى أطول من الحوار،
      // وحوارٌ يقتطع سطر التأكيد يطلب موافقة على ما لا يُقرأ.
      scrollable: true,
      content: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // جملة الخادم كما جاءت. القاعدة التي رفضت هي التي تصوغ رفضها.
          Text(widget.request.message, style: theme.textTheme.bodyMedium),
          const SizedBox(height: 16),
          _AmountRow(
            label: l10n.bidLowerStandingLabel,
            amount: widget.request.standingAmount,
          ),
          const SizedBox(height: 4),
          _AmountRow(
            label: l10n.bidLowerRequestedLabel,
            amount: widget.request.requestedAmount,
          ),
          const SizedBox(height: 12),
          CheckboxListTile(
            value: _confirmed,
            onChanged: (value) => setState(() => _confirmed = value ?? false),
            title: Text(l10n.bidLowerConfirmCheckbox),
            contentPadding: EdgeInsets.zero,
            controlAffinity: ListTileControlAffinity.leading,
          ),
        ],
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(context).pop(false),
          child: Text(l10n.cancel),
        ),
        FilledButton(
          onPressed: _confirmed ? () => Navigator.of(context).pop(true) : null,
          child: Text(l10n.bidLowerConfirmAction),
        ),
      ],
    );
  }
}

class _AmountRow extends StatelessWidget {
  const _AmountRow({required this.label, required this.amount});

  final String label;
  final String amount;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    // التسمية فوق الرقم لا بجواره: الرقمان يجب أن يُقرآ كاملين على أضيق جوال،
    // وصفٌّ واحد يدفع أحدهما خارج الحوار عند أول خطّ نظام أكبر.
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label, style: theme.textTheme.bodySmall),
        MoneyText.bare(amount, style: theme.textTheme.titleMedium),
      ],
    );
  }
}
