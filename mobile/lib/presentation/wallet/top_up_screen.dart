import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app/theme.dart';
import '../../domain/wallet/entities/top_up.dart';
import '../../l10n/generated/app_localizations.dart';
import '../common/failure_message.dart';
import '../common/haraj_app_bar.dart';
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

  /// يسأل ثمّ يُلغي — والسؤالُ لأن الإلغاء يُبطل رابطَ الدفع بلا رجعة.
  Future<void> _cancel(BuildContext context, WidgetRef ref) async {
    final l10n = AppLocalizations.of(context);
    final messenger = ScaffoldMessenger.of(context);
    final reference = ref.read(topUpControllerProvider).intent?.reference;
    if (reference == null) return;

    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(l10n.topUpCancelConfirmTitle),
        content: Text(l10n.topUpCancelConfirmBody(reference)),
        actions: <Widget>[
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: Text(l10n.cancel),
          ),
          FilledButton(
            onPressed: () => Navigator.of(context).pop(true),
            child: Text(l10n.topUpCancel),
          ),
        ],
      ),
    );
    if (!(confirmed ?? false) || !mounted) return;

    final done = await ref.read(topUpControllerProvider.notifier).cancel();
    if (!mounted || !done) return;
    messenger.showSnackBar(SnackBar(content: Text(l10n.topUpCancelled)));
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final state = ref.watch(topUpControllerProvider);
    final controller = ref.read(topUpControllerProvider.notifier);
    final intent = state.intent;

    final palette = HarajPalette.of(context);
    final muted = TextStyle(
      fontFamily: HarajTheme.fontFamily,
      fontSize: 12.5,
      color: palette.inkMuted,
      height: 1.5,
    );

    // تصميمُ الزجاج الأبيض بطلب المالك (٣ أكتوبر ٢٠٢٦): شاشةٌ شفّافة فوق
    // `GlassBackdrop`، والأزرارُ بالزرّ الأزرق الواحد، والنصوصُ السائبة كحليّةٌ
    // باهتة بدل أسلوب Material الافتراضيّ.
    return Scaffold(
      backgroundColor: Colors.transparent,
      appBar: HarajAppBar(title: l10n.topUpTitle),
      body: ListView(
        padding: EdgeInsets.fromLTRB(
          16,
          16,
          16,
          16 + MediaQuery.paddingOf(context).bottom,
        ),
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
            Text(l10n.topUpGatewayNotOpened, style: muted),
            const SizedBox(height: 10),
            FilledButton(
              onPressed: controller.openGatewayAgain,
              style: _primaryStyle(palette),
              child: Text(l10n.topUpOpenGateway),
            ),
          ],
          if (state.failure != null) ...[
            const SizedBox(height: 16),
            // رسالة الخادم كما جاءت، أو تصنيف الصمت حين لم يتكلّم.
            _FailureNote(text: failureMessage(context, state.failure!)),
          ],
          if (intent != null) ...[
            const SizedBox(height: 16),
            FilledButton(
              onPressed: state.isBusy ? null : controller.checkStatus,
              style: _primaryStyle(palette),
              child: Text(l10n.topUpCheckStatus),
            ),
            // **والإلغاءُ للمعلّقة وحدَها.** نيّةٌ نجحت أو أُلغيت لا تُلغى
            // ثانية، وزرٌّ عليها يطلب من الخادم ما يرفضه — فيقرأ العميلُ رفضاً
            // عن فعلٍ ما كان ينبغي أن يُعرض عليه.
            if (intent.isPending) ...[
              const SizedBox(height: 8),
              TextButton(
                onPressed: state.isBusy ? null : () => _cancel(context, ref),
                style: TextButton.styleFrom(
                  foregroundColor: palette.inkMuted,
                  minimumSize: const Size.fromHeight(44),
                  textStyle: const TextStyle(
                    fontFamily: HarajTheme.fontFamily,
                    fontWeight: FontWeight.w700,
                    fontSize: 14,
                  ),
                ),
                child: Text(l10n.topUpCancel),
              ),
            ],
            const SizedBox(height: 8),
            Text(
              l10n.topUpStatusFromServer,
              textAlign: TextAlign.center,
              style: muted.copyWith(fontSize: 11.5),
            ),
          ],
        ],
      ),
    );
  }
}

/// الزرُّ الأزرقُ الممتلئ — كزرّ الدخول، تصميمُ الزجاج (٣ أكتوبر ٢٠٢٦).
ButtonStyle _primaryStyle(HarajPalette palette) => FilledButton.styleFrom(
  backgroundColor: palette.gold,
  foregroundColor: Colors.white,
  disabledBackgroundColor: palette.gold.withValues(alpha: 0.35),
  disabledForegroundColor: Colors.white,
  minimumSize: const Size.fromHeight(50),
  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
  textStyle: const TextStyle(
    fontFamily: HarajTheme.fontFamily,
    fontWeight: FontWeight.w700,
    fontSize: 15,
  ),
);

/// الكرتُ الزجاجيّ — أبيضُ شفّافٌ بحدٍّ رفيعٍ وظلٍّ ناعم.
class _GlassCard extends StatelessWidget {
  const _GlassCard({required this.child});

  final Widget child;

  @override
  Widget build(BuildContext context) {
    final palette = HarajPalette.of(context);
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: palette.cardSurface,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: palette.navInactive.withValues(alpha: 0.7)),
        boxShadow: <BoxShadow>[
          BoxShadow(
            color: palette.ink.withValues(alpha: 0.05),
            blurRadius: 16,
            offset: const Offset(0, 6),
          ),
        ],
      ),
      child: child,
    );
  }
}

/// مربّعُ الأيقونة الأزرق مع عنوان الكرت.
class _CardTitle extends StatelessWidget {
  const _CardTitle({required this.icon, required this.text});

  final IconData icon;
  final String text;

  @override
  Widget build(BuildContext context) {
    final palette = HarajPalette.of(context);
    return Row(
      children: <Widget>[
        Container(
          width: 36,
          height: 36,
          decoration: BoxDecoration(
            color: palette.gold.withValues(alpha: 0.08),
            borderRadius: BorderRadius.circular(10),
          ),
          child: Icon(icon, size: 18, color: palette.gold),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: Text(
            text,
            style: TextStyle(
              fontFamily: HarajTheme.fontFamily,
              fontSize: 15,
              fontWeight: FontWeight.w700,
              color: palette.ink,
            ),
          ),
        ),
      ],
    );
  }
}

/// سطرُ الفشل — لوحٌ أحمرُ شفيف لا نصٌّ سائب يضيع على الأرضيّة.
class _FailureNote extends StatelessWidget {
  const _FailureNote({required this.text});

  final String text;

  @override
  Widget build(BuildContext context) {
    final error = Theme.of(context).colorScheme.error;
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: error.withValues(alpha: 0.07),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: error.withValues(alpha: 0.25)),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Icon(Icons.error_outline_rounded, size: 18, color: error),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              text,
              style: TextStyle(
                fontFamily: HarajTheme.fontFamily,
                fontSize: 12.5,
                fontWeight: FontWeight.w600,
                color: error,
                height: 1.5,
              ),
            ),
          ),
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
    final palette = HarajPalette.of(context);

    return _GlassCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          _CardTitle(icon: Icons.credit_card_rounded, text: l10n.topUpTitle),
          const SizedBox(height: 12),
          Text(
            l10n.topUpAmountFromServer,
            style: TextStyle(
              fontFamily: HarajTheme.fontFamily,
              fontSize: 13,
              color: palette.inkMuted,
              height: 1.6,
            ),
          ),
          const SizedBox(height: 16),
          if (isBusy)
            const Center(child: CircularProgressIndicator())
          else
            FilledButton(
              onPressed: onStart,
              style: _primaryStyle(palette),
              child: Text(l10n.topUpStart),
            ),
        ],
      ),
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
    final palette = HarajPalette.of(context);
    final small = TextStyle(
      fontFamily: HarajTheme.fontFamily,
      fontSize: 12.5,
      color: palette.inkMuted,
      height: 1.5,
    );

    return _GlassCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // وصف الحالة من الخادم — لا خريطة حالات في التطبيق (المادة ٤-٥).
          _CardTitle(
            icon: Icons.receipt_long_outlined,
            text: intent.statusLabel,
          ),
          const SizedBox(height: 14),
          MoneyText(
            intent.money,
            style: TextStyle(
              fontFamily: HarajTheme.fontFamily,
              fontSize: 28,
              fontWeight: FontWeight.w700,
              color: palette.goldDeep,
              height: 1.15,
            ),
          ),
          const SizedBox(height: 8),
          Text(l10n.movementReference(intent.reference), style: small),
          if (intent.isPending) ...[
            const SizedBox(height: 12),
            Text(l10n.topUpWaiting, style: small.copyWith(color: palette.ink)),
          ],
          if (isBusy) ...[
            const SizedBox(height: 12),
            const Center(child: CircularProgressIndicator()),
          ],
        ],
      ),
    );
  }
}
