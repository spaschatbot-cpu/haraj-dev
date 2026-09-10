import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../app/router.dart';
import '../../app/theme.dart';
import '../../domain/common/failure.dart';
import '../../domain/common/money.dart';
import '../../domain/common/snapshot.dart';
import '../../domain/wallet/entities/ledger_movement.dart';
import '../../domain/wallet/entities/refund_request.dart';
import '../../domain/wallet/entities/wallet_balance.dart';
import '../../l10n/generated/app_localizations.dart';
import '../common/failure_view.dart';
import '../common/haraj_app_bar.dart';
import '../common/money_text.dart';
import '../common/stale_data_banner.dart';
import 'wallet_controller.dart';
import 'wallet_subscribe_flow.dart';

/// المحفظة — على موكاب المالك: الاسترداد، ثم الحوالات، ثم التأمين.
///
/// **ثلاث بطاقات، وكلُّ رقمٍ فيها من الخادم.** الأصفار التي في الموكاب أعدادٌ
/// لا مبالغ: «كم طلبَ استردادٍ لك؟» جوابُه طولُ القائمة التي يردّ بها الخادم،
/// وصفرٌ صادقٌ حين لا طلب. والمبالغُ — التأمينُ والمستردّ — تأتي دلواً وصفّاً
/// كما أرسلهما، ولا يُجمع منها شيء هنا (المادة ١-٦).
///
/// **وما في الموكاب ولا عقدَ له لم يُخترَع**: «سجل الاشتراكات» يفتح كشفَ دلو
/// التأمين — وهو سجلُّ اشتراكاته بعينه — لا شاشةً ثانية بأرقامٍ من عندنا.
class WalletScreen extends ConsumerWidget {
  const WalletScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final state = ref.watch(walletBalanceProvider);

    return Scaffold(
      // **لا `appBar`**: شريطُ العنوان عنصرٌ في القائمة فينزلق معها، بطلب
      // المالك في ٩ سبتمبر ٢٠٢٦. الثابتُ فوقه هيدرُ العلامة في القشرة.
      body: switch (state) {
        AsyncData(value: final Snapshot<WalletBalance> snapshot) =>
          RefreshIndicator(
            onRefresh: () async {
              // الثلاثةُ تُبطَل معاً: بطاقةٌ تُحدَّث وأختاها لا تُحدَّثان
              // تعطي شاشةً نصفُها من لحظةٍ ونصفُها من أخرى.
              ref
                ..invalidate(refundRequestsProvider)
                ..invalidate(walletMovementsCountProvider)
                ..invalidate(walletBalanceProvider);
            },
            child: _Wallet(snapshot: snapshot),
          ),
        AsyncError(:final error) => Center(
          child: FailureView(
            failure: error is Failure ? error : UnexpectedFailure(error),
            onRetry: () => ref.invalidate(walletBalanceProvider),
          ),
        ),
        _ => const Center(child: CircularProgressIndicator()),
      },
    );
  }
}

class _Wallet extends StatelessWidget {
  const _Wallet({required this.snapshot});

  final Snapshot<WalletBalance> snapshot;

  @override
  Widget build(BuildContext context) => ListView(
    // **حاشيةُ الشريط السفليّ تُضاف إلى الحشوة**: `ListView` بحشوةٍ مكتوبة
    // لا يقرأ `MediaQuery` — والقشرةُ تضيف ارتفاعَ الشريط هناك، فيقع آخرُ
    // كرتٍ تحته ويُقرأ نصفه. قيس في لقطة المالك ٩ سبتمبر ٢٠٢٦.
    // **الحشوةُ الأفقيّة على البطاقات لا على القائمة**: شريطُ العنوان صار
    // عنصراً فيها ويمتدّ بعرض الشاشة كما كان.
    padding: EdgeInsets.only(bottom: 28 + MediaQuery.paddingOf(context).bottom),
    children: <Widget>[
      HarajAppBar(title: AppLocalizations.of(context).walletTitle),
      StaleDataBanner(snapshot: snapshot),
      Padding(
        padding: const EdgeInsets.fromLTRB(16, 14, 16, 0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: <Widget>[
            const _RefundsCard(),
            const SizedBox(height: 14),
            const _TransfersCard(),
            const SizedBox(height: 14),
            _InsuranceCard(balance: snapshot.value),
            const SizedBox(height: 22),
            const _SubscriptionsLog(),
            const SizedBox(height: 22),
            const _InsuranceLog(),
          ],
        ),
      ),
    ],
  );
}

/// إطارُ البطاقات الثلاث — **شريطٌ ذهبيٌّ على الحافّة، وحدٌّ رفيع**.
///
/// شكلٌ واحدٌ للثلاث لا ثلاثةُ أشكال: بطاقاتٌ متطابقةٌ إلا في محتواها تفترق
/// عند أول تعديلٍ يُنسى في إحداها (المادة ٤-٥). والشريطُ في الحافّة الأولى —
/// يمينُ الشاشة في العربية — هو ما يجعلها بطاقةً لا مستطيلاً.
class _Card extends StatelessWidget {
  const _Card({required this.child});

  final Widget child;

  @override
  Widget build(BuildContext context) {
    final palette = HarajPalette.of(context);

    return Container(
      decoration: BoxDecoration(
        color: palette.cardSurface,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: palette.gold.withValues(alpha: 0.26)),
        boxShadow: <BoxShadow>[
          BoxShadow(
            color: palette.ink.withValues(alpha: 0.07),
            blurRadius: 10,
            offset: const Offset(0, 3),
          ),
        ],
      ),
      clipBehavior: Clip.antiAlias,
      child: IntrinsicHeight(
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: <Widget>[
            Container(
              width: 6,
              decoration: BoxDecoration(
                gradient: LinearGradient(
                  begin: Alignment.topCenter,
                  end: Alignment.bottomCenter,
                  colors: <Color>[palette.gold, palette.goldDeep],
                ),
              ),
            ),
            Expanded(
              child: Padding(
                padding: const EdgeInsets.fromLTRB(18, 16, 18, 16),
                child: child,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// سطرُ عنوانٍ وعددٍ عريض في رأس البطاقة.
class _Headline extends StatelessWidget {
  const _Headline({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    final palette = HarajPalette.of(context);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: <Widget>[
        Row(
          crossAxisAlignment: CrossAxisAlignment.center,
          children: <Widget>[
            Expanded(
              child: Text(
                label,
                style: TextStyle(
                  fontFamily: HarajTheme.fontFamily,
                  fontSize: 12.5,
                  fontWeight: FontWeight.w600,
                  color: palette.inkMuted,
                  letterSpacing: 0.2,
                ),
              ),
            ),
            Text(
              value,
              // **`ltr`**: الأعداد تُكتب من اليسار حتى داخل نصٍّ عربيّ.
              textDirection: TextDirection.ltr,
              style: TextStyle(
                fontFamily: HarajTheme.fontFamily,
                fontSize: 28,
                fontWeight: FontWeight.w700,
                color: palette.ink,
                height: 1.05,
              ),
            ),
          ],
        ),
        const SizedBox(height: 12),
        // خطٌّ يفصل الرأسَ عمّا تحته: بدونه يُقرأ الرقمُ والحوضُ كتلةً واحدة.
        Divider(height: 1, color: palette.gold.withValues(alpha: 0.22)),
        const SizedBox(height: 12),
      ],
    );
  }
}

/// بطاقةُ طلبات الاسترداد: عددُها، وآخرُ طلبٍ بمبلغه وحالته.
///
/// **ولا مجموعَ للمبالغ**: `Money` بلا عمليات، وجمعُ الطلبات هنا رقمٌ بلا قيدٍ
/// يقابله. فيُعرض آخرُ طلبٍ كما أرسله الخادم، وبقيّتُها في كشف الحساب.
class _RefundsCard extends ConsumerWidget {
  const _RefundsCard();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = AppLocalizations.of(context);
    final palette = HarajPalette.of(context);
    final requests = ref.watch(refundRequestsProvider);
    final rows = requests.value?.value ?? const <RefundRequest>[];

    return _Card(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          _Headline(
            label: l10n.walletRefundRequests,
            // شرطةٌ ريثما يردّ الخادم: صفرٌ قبل الجواب خبرٌ لم يُقَل بعد.
            value: requests.hasValue ? '${rows.length}' : '—',
          ),
          Container(
            width: double.infinity,
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
            decoration: BoxDecoration(
              color: palette.pageBackground,
              borderRadius: BorderRadius.circular(12),
            ),
            child: Row(
              children: <Widget>[
                Text(
                  l10n.walletRefundedAmount,
                  style: TextStyle(
                    fontFamily: HarajTheme.fontFamily,
                    fontSize: 11.5,
                    fontWeight: FontWeight.w600,
                    color: palette.inkMuted,
                  ),
                ),
                const Spacer(),
                if (rows.isEmpty)
                  Text(
                    '—',
                    style: TextStyle(
                      fontFamily: HarajTheme.fontFamily,
                      fontSize: 14,
                      fontWeight: FontWeight.w700,
                      color: palette.inkMuted,
                    ),
                  )
                else ...<Widget>[
                  Text(
                    rows.first.stateLabel,
                    style: TextStyle(
                      fontFamily: HarajTheme.fontFamily,
                      fontSize: 11,
                      fontWeight: FontWeight.w600,
                      color: palette.inkMuted,
                    ),
                  ),
                  const SizedBox(width: 8),
                  MoneyText(
                    rows.first.money,
                    style: TextStyle(
                      fontFamily: HarajTheme.fontFamily,
                      fontSize: 14,
                      fontWeight: FontWeight.w700,
                      color: palette.goldDeep,
                    ),
                  ),
                ],
              ],
            ),
          ),
        ],
      ),
    );
  }
}

/// بطاقةُ الحوالات: عددُها، وزرٌّ ذهبيٌّ يفتح كشفَ الحساب.
///
/// **العددُ من كشف الحركات لا من نقطةٍ للحوالات**: لا نقطةَ «حوالاتي» في
/// العقد، وحركاتُ الحساب هي ما يسرد ما دخل وما خرج. والزرُّ يفتحها كاملةً —
/// فلا رقمٌ هنا يقول شيئاً لا تؤكّده الشاشةُ التي يفتحها.
class _TransfersCard extends ConsumerWidget {
  const _TransfersCard();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = AppLocalizations.of(context);
    final palette = HarajPalette.of(context);
    final movements = ref.watch(walletMovementsCountProvider);

    return _Card(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          _Headline(
            label: l10n.walletTransfers,
            value: movements.hasValue ? '${movements.value}' : '—',
          ),
          SizedBox(
            width: double.infinity,
            child: FilledButton.icon(
              onPressed: () => context.pushNamed(Routes.walletStatement),
              icon: const Icon(Icons.arrow_back_rounded, size: 18),
              label: Text(l10n.walletOpenTransfers),
              style: FilledButton.styleFrom(
                backgroundColor: palette.goldDeep,
                foregroundColor: Colors.white,
                padding: const EdgeInsets.symmetric(vertical: 14),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(12),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

/// بطاقةُ التأمين: مبلغُه، وحالتُه، وحالةُ الاشتراك، وزرُّ الاشتراك.
///
/// **ولا رابطَ سجلٍّ فيها** — نزل قسماً تحتها بطلب المالك في ٩ سبتمبر ٢٠٢٦:
/// البطاقةُ تقول «أين أنت الآن»، والسجلُّ يقول «ماذا جرى»، وحشرُهما في صندوقٍ
/// واحد يجعل زرّاً صغيراً يحمل قائمةً كاملة.
///
/// **المبلغُ دلوُ التأمين كما أرسله الخادم**، وحالتُه تُقرأ منه لا تُخترع:
/// دلوٌ فارغ يعني «غير مفعّل»، وغيرُ الفارغ يعني «مفعّل». ولا رقمَ ثابتاً
/// («١٠٬٠٠٠») مكتوباً في التطبيق: مبلغُ الاشتراك قاعدةُ عملٍ يملكها الخادم،
/// وكتابتُها هنا نسخةٌ ثانية تفترق عنه في أوّل يومٍ تتغيّر فيه (المادة ٤-٥).
class _InsuranceCard extends StatelessWidget {
  const _InsuranceCard({required this.balance});

  final WalletBalance balance;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final palette = HarajPalette.of(context);
    final theme = Theme.of(context);

    // دلوُ التأمين المتاح هو ما يقول «اشتراكُك قائم»: المحجوزُ مربوطٌ بمزادٍ
    // والمقفلُ بمستحقّ، وكلاهما لا يفتح مزاداً جديداً.
    final deposit = balance.buckets
        .where((bucket) => bucket.kind == WalletBucketKind.insuranceFree)
        .map((bucket) => bucket.money)
        .firstOrNull;
    final active = deposit != null && !_isZero(deposit);
    final tint = active ? palette.goldDeep : theme.colorScheme.error;

    return _Card(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: <Widget>[
          Center(
            child: Text(
              l10n.walletInsuranceStatus,
              style: TextStyle(
                fontFamily: HarajTheme.fontFamily,
                fontSize: 12.5,
                fontWeight: FontWeight.w600,
                color: palette.inkMuted,
                letterSpacing: 0.2,
              ),
            ),
          ),
          const SizedBox(height: 8),
          Center(
            child: deposit == null
                ? Text(
                    '—',
                    style: TextStyle(
                      fontFamily: HarajTheme.fontFamily,
                      fontSize: 30,
                      fontWeight: FontWeight.w700,
                      color: palette.inkMuted,
                    ),
                  )
                : MoneyText(
                    deposit,
                    style: TextStyle(
                      fontFamily: HarajTheme.fontFamily,
                      fontSize: 30,
                      fontWeight: FontWeight.w700,
                      color: palette.goldDeep,
                      height: 1.15,
                    ),
                  ),
          ),
          const SizedBox(height: 8),
          Center(
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: <Widget>[
                Icon(
                  active ? Icons.check_circle_rounded : Icons.cancel_rounded,
                  size: 16,
                  color: tint,
                ),
                const SizedBox(width: 6),
                Flexible(
                  child: Text(
                    active
                        ? l10n.walletInsuranceActive
                        : l10n.walletInsuranceInactive,
                    textAlign: TextAlign.center,
                    style: TextStyle(
                      fontFamily: HarajTheme.fontFamily,
                      fontSize: 11.5,
                      fontWeight: FontWeight.w700,
                      color: tint,
                    ),
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 12),
          // لوحُ حالة الاشتراك — أرضيّتُه بلون الحالة، فيُقرأ قبل أن يُقرأ
          // نصُّه.
          Container(
            decoration: BoxDecoration(
              color: tint.withValues(alpha: 0.08),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: tint.withValues(alpha: 0.30)),
            ),
            padding: const EdgeInsets.fromLTRB(12, 10, 12, 12),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: <Widget>[
                Row(
                  children: <Widget>[
                    Icon(Icons.verified_user_outlined, size: 15, color: tint),
                    const SizedBox(width: 6),
                    Text(
                      l10n.walletSubscriptionStatus,
                      style: TextStyle(
                        fontFamily: HarajTheme.fontFamily,
                        fontSize: 12,
                        fontWeight: FontWeight.w700,
                        color: palette.ink,
                      ),
                    ),
                    const Spacer(),
                    Text(
                      active
                          ? l10n.walletSubscriptionActive
                          : l10n.walletSubscriptionInactive,
                      style: TextStyle(
                        fontFamily: HarajTheme.fontFamily,
                        fontSize: 12,
                        fontWeight: FontWeight.w700,
                        color: tint,
                      ),
                    ),
                    const SizedBox(width: 4),
                    Icon(
                      active ? Icons.check_rounded : Icons.close_rounded,
                      size: 15,
                      color: tint,
                    ),
                  ],
                ),
                const SizedBox(height: 8),
                Text(
                  l10n.walletSubscriptionNote,
                  textAlign: TextAlign.center,
                  style: TextStyle(
                    fontFamily: HarajTheme.fontFamily,
                    fontSize: 11,
                    color: palette.ink.withValues(alpha: 0.85),
                    height: 1.6,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 12),
          // **زرٌّ داكن لا ذهبيّ**: الذهبيُّ في هذه الشاشة لزرّ «اضغط للعرض»،
          // وزرّان ذهبيّان في صفحةٍ واحدة يتنازعان على النظر.
          SizedBox(
            width: double.infinity,
            child: FilledButton.icon(
              // **بياناتٌ ثم دفع**: الشرحُ عند `showSubscribeFlow`.
              onPressed: () => showSubscribeFlow(context),
              icon: const Icon(Icons.add_rounded, size: 18),
              label: Text(l10n.walletSubscribeAction),
              style: FilledButton.styleFrom(
                backgroundColor: palette.heroTop,
                foregroundColor: Colors.white,
                padding: const EdgeInsets.symmetric(vertical: 14),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(12),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  /// هل المبلغ صفر — **بفحص النصّ لا بتحويله إلى عدد**: المادة ٣-٢ تمنع
  /// `double` في أي مسار ماليّ. و«0.00» و«0» و«0.000» كلُّها صفر، وأيُّ رقمٍ
  /// من ١ إلى ٩ في النصّ يعني أنه ليس صفراً.
  static bool _isZero(Money money) =>
      !money.amount.split('').any((digit) => '123456789'.contains(digit));
}

/// عنوانُ قسمٍ تحت البطاقات: أيقونةٌ واسمٌ وخيطٌ ذهبيٌّ تحته.
class _SectionTitle extends StatelessWidget {
  const _SectionTitle({required this.icon, required this.label});

  final IconData icon;
  final String label;

  @override
  Widget build(BuildContext context) {
    final palette = HarajPalette.of(context);

    return Column(
      // **من اليمين**: `end` كانت تضعه يساراً في العربية، فيقف عنوانُ القسم
      // في جهةٍ والنصُّ تحته في الأخرى.
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        Row(
          mainAxisSize: MainAxisSize.min,
          children: <Widget>[
            Icon(icon, size: 17, color: palette.goldDeep),
            const SizedBox(width: 7),
            Text(
              label,
              style: TextStyle(
                fontFamily: HarajTheme.fontFamily,
                fontSize: 14,
                fontWeight: FontWeight.w700,
                color: palette.ink,
              ),
            ),
          ],
        ),
        const SizedBox(height: 7),
        // **خيطٌ تحت العنوان لا حول القسم**: القسمُ قد يكون فارغاً، وإطارٌ
        // حول فراغٍ يُقرأ صندوقاً معطَّلاً؛ والخيطُ يعنون ولا يحبس.
        Container(
          height: 2,
          decoration: BoxDecoration(
            gradient: LinearGradient(
              begin: Alignment.centerRight,
              end: Alignment.centerLeft,
              colors: <Color>[
                palette.goldDeep,
                palette.gold.withValues(alpha: 0),
              ],
            ),
            borderRadius: BorderRadius.circular(1),
          ),
        ),
      ],
    );
  }
}

/// حالةٌ فارغة داخل قسم: أيقونةٌ باهتة وجملةٌ واحدة.
class _EmptyNote extends StatelessWidget {
  const _EmptyNote({required this.message, this.icon});

  final String message;
  final IconData? icon;

  @override
  Widget build(BuildContext context) {
    final palette = HarajPalette.of(context);

    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 26),
      child: Column(
        children: <Widget>[
          if (icon case final IconData glyph) ...<Widget>[
            Icon(
              glyph,
              size: 44,
              color: palette.inkMuted.withValues(alpha: 0.35),
            ),
            const SizedBox(height: 12),
          ],
          Text(
            message,
            textAlign: TextAlign.center,
            style: TextStyle(
              fontFamily: HarajTheme.fontFamily,
              fontSize: 12.5,
              fontWeight: FontWeight.w500,
              color: palette.inkMuted,
            ),
          ),
        ],
      ),
    );
  }
}

/// سجلُّ الاشتراكات.
///
/// **فارغٌ دائماً في هذا الإصدار، وذلك صدقُه**: لا اشتراكَ في عقد الخادم بعد —
/// لا نقطةَ تُنشئه ولا صفَّ يسرده. فالجملةُ «لم تقم بأي اشتراك بعد» صحيحةٌ
/// لكل عميل، وقائمةٌ مخترَعةٌ مكانها كانت ستقول ما لم يقله الدفتر.
class _SubscriptionsLog extends StatelessWidget {
  const _SubscriptionsLog();

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: <Widget>[
        _SectionTitle(
          icon: Icons.assignment_outlined,
          label: l10n.walletSubscriptionsLog,
        ),
        _EmptyNote(message: l10n.walletNoSubscriptions),
      ],
    );
  }
}

/// سجلُّ عمليات التأمين — حركاتُ دلاء التأمين كما وصلت.
class _InsuranceLog extends ConsumerWidget {
  const _InsuranceLog();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = AppLocalizations.of(context);
    final palette = HarajPalette.of(context);
    final movements = ref.watch(insuranceMovementsProvider);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: <Widget>[
        _SectionTitle(
          icon: Icons.verified_user_outlined,
          label: l10n.walletInsuranceLog,
        ),
        switch (movements) {
          AsyncData(value: final List<LedgerMovement> rows) when rows.isEmpty =>
            _EmptyNote(
              message: l10n.walletNoOperations,
              icon: Icons.schedule_rounded,
            ),
          AsyncData(value: final List<LedgerMovement> rows) => Column(
            children: <Widget>[
              for (final movement in rows) _MovementRow(movement: movement),
            ],
          ),
          // **فشلُ القسم لا يُسقط الشاشة**: المحفظةُ فوقه وصلت، وسطرٌ يشرح
          // خيرٌ من شاشة خطأ تُخفي رصيداً قُرئ.
          AsyncError(:final error) => _EmptyNote(
            message: error is Failure
                ? error.toString()
                : l10n.walletNoOperations,
          ),
          _ => Padding(
            padding: const EdgeInsets.symmetric(vertical: 26),
            child: Center(
              child: SizedBox.square(
                dimension: 22,
                child: CircularProgressIndicator(
                  strokeWidth: 2,
                  color: palette.gold,
                ),
              ),
            ),
          ),
        },
      ],
    );
  }
}

/// حركةٌ واحدة في سجلّ التأمين: وصفُها ودلوُها ومبلغُها.
class _MovementRow extends StatelessWidget {
  const _MovementRow({required this.movement});

  final LedgerMovement movement;

  @override
  Widget build(BuildContext context) {
    final palette = HarajPalette.of(context);

    return Padding(
      padding: const EdgeInsets.only(top: 10),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text(
                  // الوصفُ عربيٌّ من الخادم ويُعرض حرفياً.
                  movement.description,
                  style: TextStyle(
                    fontFamily: HarajTheme.fontFamily,
                    fontSize: 12.5,
                    fontWeight: FontWeight.w600,
                    color: palette.ink,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  movement.bucketLabel,
                  style: TextStyle(
                    fontFamily: HarajTheme.fontFamily,
                    fontSize: 10.5,
                    color: palette.inkMuted,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(width: 10),
          MoneyText(
            movement.money,
            style: TextStyle(
              fontFamily: HarajTheme.fontFamily,
              fontSize: 13,
              fontWeight: FontWeight.w700,
              color: palette.goldDeep,
            ),
          ),
        ],
      ),
    );
  }
}
