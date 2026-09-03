import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../domain/wallet/entities/top_up.dart';
import '../../l10n/generated/app_localizations.dart';
import '../common/failure_message.dart';
import '../common/money_text.dart';
import 'top_up_controller.dart';

/// الشحن بالبطاقة (T713).
///
/// **الشاشة لا تقرأ رابط العودة.** تفتح صفحة الدفع، وحين يعود العميل تسأل
/// الخادم عن حالة النيّة بمرجعها. لا معامل من الرابط يصل إلى هنا أصلاً، فليس
/// في الشيفرة موضع يمكن التلاعب به: في v1 كان `?status=paid` كافياً ليعتقد
/// التطبيق أن الدفع تمّ، ورصيدٌ تحرّك على هذا الأساس.
///
/// العودة تُلتقط من دورة حياة التطبيق (`resumed`) لا من رابط: أياً كان طريق
/// العميل إلينا — أنهى الدفع، أو ألغى، أو بدّل التطبيقات — السؤال واحد
/// والمصدر واحد.
class TopUpScreen extends ConsumerStatefulWidget {
  const TopUpScreen({super.key});

  @override
  ConsumerState<TopUpScreen> createState() => _TopUpScreenState();
}

class _TopUpScreenState extends ConsumerState<TopUpScreen>
    with WidgetsBindingObserver {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState lifecycle) {
    if (lifecycle != AppLifecycleState.resumed) return;
    final intent = ref.read(topUpControllerProvider).intent;
    if (intent == null || !intent.isPending) return;
    unawaited(ref.read(topUpControllerProvider.notifier).checkStatus());
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final state = ref.watch(topUpControllerProvider);
    final controller = ref.read(topUpControllerProvider.notifier);
    final intent = state.intent;

    return Scaffold(
      appBar: AppBar(title: Text(l10n.topUpTitle)),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          if (intent == null)
            _StartCard(
              isBusy: state.isBusy,
              onStart: state.isBusy ? null : controller.start,
            )
          else
            _IntentCard(intent: intent, isBusy: state.isBusy),
          if (intent != null && !state.gatewayOpened) ...[
            const SizedBox(height: 16),
            Text(l10n.topUpGatewayNotOpened),
            const SizedBox(height: 8),
            FilledButton(
              onPressed: controller.openGatewayAgain,
              child: Text(l10n.topUpOpenGateway),
            ),
          ],
          if (state.failure != null) ...[
            const SizedBox(height: 16),
            // رسالة الخادم كما جاءت، أو تصنيف الصمت حين لم يتكلّم.
            Text(failureMessage(context, state.failure!)),
          ],
          if (intent != null) ...[
            const SizedBox(height: 16),
            FilledButton(
              onPressed: state.isBusy ? null : controller.checkStatus,
              child: Text(l10n.topUpCheckStatus),
            ),
            const SizedBox(height: 8),
            Text(
              l10n.topUpStatusFromServer,
              style: Theme.of(context).textTheme.bodySmall,
            ),
          ],
        ],
      ),
    );
  }
}

/// ما قبل البدء: زرّ واحد، وبلا خانة مبلغ.
///
/// خانة المبلغ كانت ستكون كذبة: الخادم يحدّد المبلغ ويرفض طلباً يسمّي مبلغه،
/// فحقلٌ تُهمَل قيمته أسوأ من غيابه لأنه يبدو خياراً.
class _StartCard extends StatelessWidget {
  const _StartCard({required this.isBusy, required this.onStart});

  final bool isBusy;
  final Future<void> Function()? onStart;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(l10n.topUpAmountFromServer),
        const SizedBox(height: 16),
        if (isBusy)
          const Center(child: CircularProgressIndicator())
        else
          FilledButton(onPressed: onStart, child: Text(l10n.topUpStart)),
      ],
    );
  }
}

/// النيّة كما يعرفها الخادم: حالتها بكلامه، ومبلغها كما وصل، ومرجعها.
class _IntentCard extends StatelessWidget {
  const _IntentCard({required this.intent, required this.isBusy});

  final TopUp intent;
  final bool isBusy;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final theme = Theme.of(context);

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // وصف الحالة من الخادم — لا خريطة حالات في التطبيق (المادة ٤-٥).
            Text(intent.statusLabel, style: theme.textTheme.titleMedium),
            const SizedBox(height: 8),
            MoneyText(intent.money, style: theme.textTheme.headlineSmall),
            const SizedBox(height: 8),
            Text(
              l10n.movementReference(intent.reference),
              style: theme.textTheme.bodySmall,
            ),
            if (intent.isPending) ...[
              const SizedBox(height: 12),
              Text(l10n.topUpWaiting),
            ],
            if (isBusy) ...[
              const SizedBox(height: 12),
              const Center(child: CircularProgressIndicator()),
            ],
          ],
        ),
      ),
    );
  }
}
