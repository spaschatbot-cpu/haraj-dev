import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../l10n/generated/app_localizations.dart';
import '../common/failure_message.dart';
import 'bidding_controllers.dart';
import 'lower_bid_confirmation_dialog.dart';

/// صندوق المزايدة — نموذج، وجوابُ الخادم تحته.
///
/// **ما لا يفعله هذا الصندوق هو تعريفه:** لا يسأل إن كان العميل مؤهلاً، ولا
/// إن كان المزاد مفتوحاً، ولا يحسب حدّاً أدنى، ولا يقارن بمزايدة قائمة. لا
/// يوجد فيه فرعٌ يستطيع أن يرفض من كان الخادم ليقبله، أو أن يفتح الصندوق لمن
/// سيرفضه. المعيار J7 أن يكون الرفض الذي يراه العميل هو سبب **الخادم**
/// المُعدَّد نفسه في القناتين، والطريقة الوحيدة لضمانه ألّا يوجد هنا ما ينتج
/// سبباً آخر.
///
/// النتيجة الظاهرة أن غير المؤهل يرى الصندوق ثم يرى جملة. وهذا مقصود: صندوقٌ
/// مخفيّ لا يقول لصاحبه شيئاً، و«لا يوجد تأمين متاح» تقول له ما يفعله تالياً.
///
/// المبلغ نصّ من الحقل إلى الجسم بلا `double.parse` وبلا تنسيق (المادة ٣-٢).
class PlaceBidPanel extends ConsumerStatefulWidget {
  const PlaceBidPanel({required this.vehicleId, super.key});

  final String vehicleId;

  @override
  ConsumerState<PlaceBidPanel> createState() => _PlaceBidPanelState();
}

class _PlaceBidPanelState extends ConsumerState<PlaceBidPanel> {
  final TextEditingController _amount = TextEditingController();
  final GlobalKey<FormState> _form = GlobalKey<FormState>();

  @override
  void dispose() {
    _amount.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (!(_form.currentState?.validate() ?? false)) return;

    final amount = _amount.text.trim();
    final controller = ref.read(
      placeBidControllerProvider(widget.vehicleId).notifier,
    );

    await controller.submit(amount);
    if (!mounted) return;

    final state = ref.read(placeBidControllerProvider(widget.vehicleId));
    if (state is! PlaceBidNeedsConfirmation) return;

    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => LowerBidConfirmationDialog(request: state.request),
    );
    if (!mounted) return;

    if (confirmed ?? false) {
      // النداء الثاني وحده يحمل التأكيد، ولا يحمله إلا بعد أن طلبه الخادم
      // وأقرّه المستخدم. استنتاجه هنا يمشي خلال الحارس الذي وُجد F3 له.
      await controller.submit(amount, confirmLower: true);
    } else {
      controller.dismiss();
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final theme = Theme.of(context);
    final state = ref.watch(placeBidControllerProvider(widget.vehicleId));
    final busy = state is PlaceBidSubmitting;

    return Form(
      key: _form,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(l10n.bidPanelTitle, style: theme.textTheme.titleMedium),
          const SizedBox(height: 12),
          TextFormField(
            controller: _amount,
            enabled: !busy,
            // نصّ لا رقم: `TextInputType.number` على بعض الأجهزة يفرض فاصلاً
            // عشرياً محلياً، فيصل إلى الخادم مبلغ بشكل آخر (المادة ٣-٢).
            keyboardType: const TextInputType.numberWithOptions(decimal: true),
            textDirection: TextDirection.ltr,
            decoration: InputDecoration(
              labelText: l10n.bidAmountLabel,
              border: const OutlineInputBorder(),
            ),
            // الفحص الوحيد المسموح: أن الحقل ليس فارغاً. نقصٌ في النموذج، لا
            // قاعدة عمل — قيمةُ المبلغ نفسها يحكم عليها الخادم وحده.
            validator: (value) =>
                (value ?? '').trim().isEmpty ? l10n.bidAmountMissing : null,
          ),
          const SizedBox(height: 12),
          FilledButton(
            onPressed: busy ? null : _submit,
            child: busy
                ? const SizedBox.square(
                    dimension: 18,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                : Text(l10n.bidSubmit),
          ),
          const SizedBox(height: 12),
          _Answer(state: state),
          Text(l10n.bidServerDecides, style: theme.textTheme.bodySmall),
        ],
      ),
    );
  }
}

/// جواب الخادم على آخر محاولة.
class _Answer extends StatelessWidget {
  const _Answer({required this.state});

  final PlaceBidState state;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final theme = Theme.of(context);

    return switch (state) {
      PlaceBidIdle() ||
      PlaceBidSubmitting() ||
      // الحوار نفسه هو عرض هذه الحالة؛ تكرارها تحته يقول الشيء مرتين.
      PlaceBidNeedsConfirmation() => const SizedBox.shrink(),
      PlaceBidAccepted() => Padding(
        padding: const EdgeInsets.only(bottom: 12),
        child: Text(
          l10n.bidPlaced,
          style: theme.textTheme.bodyMedium?.copyWith(
            color: theme.colorScheme.primary,
          ),
        ),
      ),
      // رسالة الخادم حرفياً. لا خريطة رموز، ولا صياغة ثانية عندنا — من كتب
      // القاعدة كتب رفضها.
      PlaceBidRefused(:final failure) => Padding(
        padding: const EdgeInsets.only(bottom: 12),
        child: Text(
          failureMessage(context, failure),
          style: theme.textTheme.bodyMedium?.copyWith(
            color: theme.colorScheme.error,
          ),
        ),
      ),
    };
  }
}
