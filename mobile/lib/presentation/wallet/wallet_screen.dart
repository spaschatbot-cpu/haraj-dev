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
      // شفّافةٌ فوق `GlassBackdrop` — تصميمُ الزجاج الأبيض بطلب المالك
      // (٣ أكتوبر ٢٠٢٦)؛ أرضيّةٌ مصمتةٌ هنا تحجب التدرّجَ فيبطل الزجاج.
      backgroundColor: Colors.transparent,
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
            const SizedBox(height: 24),
            const _SubscriptionsLog(),
            const SizedBox(height: 20),
            const _InsuranceLog(),
          ],
        ),
      ),
    ],
  );
}

/// إطارُ البطاقات الثلاث — **زجاجٌ أبيضُ مصنفر، وحدٌّ رفيع**.
///
/// شكلٌ واحدٌ للثلاث لا ثلاثةُ أشكال: بطاقاتٌ متطابقةٌ إلا في محتواها تفترق
/// عند أول تعديلٍ يُنسى في إحداها (المادة ٤-٥).
///
/// تصميمُ الزجاج الأبيض بطلب المالك (٣ أكتوبر ٢٠٢٦): سقط الشريطُ الذهبيّ على
/// الحافّة والحدُّ الأزرق — على أرضيّةٍ متدرّجة يكفي الزجاجُ والظلُّ الناعم
/// ليُقرأ الكرتُ كرتاً، والشريطُ صار زخرفةً تزاحم الأرقام. و`tinted` يصبغه
/// بأزرقَ خفيف — لبطاقة الرصيد وحدها، فتُقرأ أوّلاً بلا كحليٍّ ثقيل.
class _Card extends StatelessWidget {
  const _Card({required this.child, this.tinted = false});

  final Widget child;
  final bool tinted;

  @override
  Widget build(BuildContext context) {
    final palette = HarajPalette.of(context);

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: tinted ? null : palette.cardSurface,
        gradient: tinted
            ? LinearGradient(
                begin: Alignment.topRight,
                end: Alignment.bottomLeft,
                colors: <Color>[
                  Color.alphaBlend(
                    palette.gold.withValues(alpha: 0.12),
                    palette.cardSurface,
                  ),
                  palette.cardSurface,
                ],
              )
            : null,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(
          color: tinted
              ? palette.gold.withValues(alpha: 0.22)
              : palette.navInactive.withValues(alpha: 0.7),
        ),
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

/// مربّعُ الأيقونة — أزرقُ على أزرقَ شفيف، كما في شاشة الدخول.
class _IconTile extends StatelessWidget {
  const _IconTile({required this.icon, this.size = 36});

  final IconData icon;
  final double size;

  @override
  Widget build(BuildContext context) {
    final palette = HarajPalette.of(context);
    return Container(
      width: size,
      height: size,
      decoration: BoxDecoration(
        color: palette.gold.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(10),
      ),
      child: Icon(icon, size: size * 0.5, color: palette.gold),
    );
  }
}

/// سطرُ عنوانٍ وعددٍ عريض في رأس البطاقة.
class _Headline extends StatelessWidget {
  const _Headline({
    required this.icon,
    required this.label,
    required this.value,
  });

  final IconData icon;
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
            _IconTile(icon: icon),
            const SizedBox(width: 12),
            Expanded(
              child: Text(
                label,
                style: TextStyle(
                  fontFamily: HarajTheme.fontFamily,
                  fontSize: 14,
                  fontWeight: FontWeight.w700,
                  color: palette.ink,
                ),
              ),
            ),
            Text(
              value,
              // **`ltr`**: الأعداد تُكتب من اليسار حتى داخل نصٍّ عربيّ.
              textDirection: TextDirection.ltr,
              style: TextStyle(
                fontFamily: HarajTheme.fontFamily,
                fontSize: 26,
                fontWeight: FontWeight.w700,
                color: palette.ink,
                height: 1.05,
              ),
            ),
          ],
        ),
        const SizedBox(height: 14),
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
            icon: Icons.assignment_return_outlined,
            label: l10n.walletRefundRequests,
            // شرطةٌ ريثما يردّ الخادم: صفرٌ قبل الجواب خبرٌ لم يُقَل بعد.
            value: requests.hasValue ? '${rows.length}' : '—',
          ),
          // حوضٌ أزرقُ شفيف لا `pageBackground` المصمت — تصميمُ الزجاج
          // (٣ أكتوبر ٢٠٢٦): رماديٌّ مصمتٌ داخل كرتٍ زجاجيّ يُقرأ رقعة.
          Container(
            width: double.infinity,
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
            decoration: BoxDecoration(
              color: palette.gold.withValues(alpha: 0.06),
              borderRadius: BorderRadius.circular(14),
              border: Border.all(color: palette.gold.withValues(alpha: 0.12)),
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
            icon: Icons.swap_horiz_rounded,
            label: l10n.walletTransfers,
            value: movements.hasValue ? '${movements.value}' : '—',
          ),
          SizedBox(
            width: double.infinity,
            child: FilledButton.icon(
              onPressed: () => context.pushNamed(Routes.walletStatement),
              icon: const Icon(Icons.arrow_back_rounded, size: 18),
              label: Text(l10n.walletOpenTransfers),
              // الزرُّ الأساسيّ في تصميم الزجاج (٣ أكتوبر ٢٠٢٦) — كزرّ الدخول.
              style: _primaryButtonStyle(palette),
            ),
          ),
        ],
      ),
    );
  }
}

/// الزرُّ الأزرقُ الممتلئ — **واحدٌ للشاشة كلِّها** لا نسخةٌ في كل بطاقة.
ButtonStyle _primaryButtonStyle(HarajPalette palette) => FilledButton.styleFrom(
  backgroundColor: palette.gold,
  foregroundColor: Colors.white,
  minimumSize: const Size.fromHeight(50),
  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
  textStyle: const TextStyle(
    fontFamily: HarajTheme.fontFamily,
    fontWeight: FontWeight.w700,
    fontSize: 15,
  ),
);

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

    // **والصفرُ ليس دائماً «لا تأمين». T945**
    //
    // العطل، مقيساً في المتصفّح (١٩ سبتمبر ٢٠٢٦): عميلٌ له `insurance_free = 0`
    // و`insurance_held = 10,000` — أي أن تأمينه **محجوزٌ كلُّه على مزادٍ قائم**
    // — قرأ «غير مفعّل: يجب شحن التأمين أولاً». وهي جملةٌ تقول له «ما عندك
    // شيء» وعنده عشرةُ آلاف، فيشحن ثانيةً أو يتصل غاضباً.
    //
    // والرقمُ المعروضُ يبقى المتاحَ وحدَه — هو الذي يفتح مزاداً جديداً، وجمعُه
    // بالمحجوز يعطي رقماً لا يستطيع صاحبُه أن يزايد به. **والذي يتغيّر هو
    // الجملةُ تحته**: تقول أين ذهب المال لا أنه ليس موجوداً.
    final committed = balance.buckets
        .where(
          (bucket) =>
              bucket.kind == WalletBucketKind.insuranceHeld ||
              bucket.kind == WalletBucketKind.insuranceLocked,
        )
        .where((bucket) => !_isZero(bucket.money))
        .toList();
    final held = committed
        .where((bucket) => bucket.kind == WalletBucketKind.insuranceHeld)
        .isNotEmpty;

    final String statusLine;
    if (active) {
      statusLine = l10n.walletInsuranceActive;
    } else if (committed.isEmpty) {
      statusLine = l10n.walletInsuranceInactive;
    } else {
      // المحجوزُ أوّلاً حين يجتمعان: هو المؤقّتُ الذي يعود بلا فعلٍ من العميل،
      // والمقفولُ يحتاج سداداً — والأولُ طمأنةٌ والثاني مطالبة.
      statusLine = held ? l10n.walletInsuranceHeld : l10n.walletInsuranceLocked;
    }

    // ولا «خطأ» أحمرُ لمالٍ قائم: المحجوزُ حالةٌ طبيعيّةٌ في مزادٍ جارٍ.
    final tint = active
        ? palette.goldDeep
        : (committed.isEmpty ? theme.colorScheme.error : palette.inkMuted);

    // بطاقةُ الرصيد مصبوغةٌ بأزرقَ خفيف — تُقرأ أوّلاً في الشاشة بلا لوحٍ
    // كحليّ، بتصميم الزجاج (٣ أكتوبر ٢٠٢٦).
    return _Card(
      tinted: true,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: <Widget>[
          const Center(child: _IconTile(icon: Icons.shield_outlined, size: 42)),
          const SizedBox(height: 10),
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
                      fontSize: 32,
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
                  active
                      ? Icons.check_circle_rounded
                      : (committed.isEmpty
                            ? Icons.cancel_rounded
                            : Icons.lock_clock_rounded),
                  size: 16,
                  color: tint,
                ),
                const SizedBox(width: 6),
                Flexible(
                  child: Text(
                    statusLine,
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
          const SizedBox(height: 14),
          // لوحُ حالة الاشتراك — أرضيّتُه بلون الحالة، فيُقرأ قبل أن يُقرأ
          // نصُّه.
          Container(
            decoration: BoxDecoration(
              color: tint.withValues(alpha: 0.07),
              borderRadius: BorderRadius.circular(14),
              border: Border.all(color: tint.withValues(alpha: 0.22)),
            ),
            padding: const EdgeInsets.fromLTRB(14, 12, 14, 12),
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
          const SizedBox(height: 14),
          // **زرٌّ أزرقُ شفيف لا ممتلئ**: الممتلئُ في هذه الشاشة لزرّ «اضغط
          // للعرض»، وزرّان ممتلئان في صفحةٍ واحدة يتنازعان على النظر. وكان
          // كحليّاً (`heroTop`) فسقط مع الكحليّ كلِّه في تصميم الزجاج الأبيض
          // (٣ أكتوبر ٢٠٢٦).
          SizedBox(
            width: double.infinity,
            child: FilledButton.icon(
              // **بياناتٌ ثم دفع**: الشرحُ عند `showSubscribeFlow`.
              onPressed: () => showSubscribeFlow(context),
              icon: const Icon(Icons.add_rounded, size: 18),
              label: Text(l10n.walletSubscribeAction),
              style: FilledButton.styleFrom(
                backgroundColor: palette.gold.withValues(alpha: 0.10),
                foregroundColor: palette.gold,
                iconColor: palette.gold,
                side: BorderSide(color: palette.gold.withValues(alpha: 0.30)),
                minimumSize: const Size.fromHeight(50),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(14),
                ),
                textStyle: const TextStyle(
                  fontFamily: HarajTheme.fontFamily,
                  fontWeight: FontWeight.w700,
                  fontSize: 15,
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

/// عنوانُ قسمٍ تحت البطاقات: مربّعُ أيقونةٍ واسمٌ.
///
/// كان تحته خيطٌ ذهبيٌّ متدرّج يعنون القسم؛ وفي تصميم الزجاج الأبيض (٣ أكتوبر
/// ٢٠٢٦) صار محتوى القسم في كرتٍ زجاجيّ تحته، والكرتُ يحدّه — فالخيطُ حدٌّ ثانٍ.
class _SectionTitle extends StatelessWidget {
  const _SectionTitle({required this.icon, required this.label});

  final IconData icon;
  final String label;

  @override
  Widget build(BuildContext context) {
    final palette = HarajPalette.of(context);

    return Padding(
      padding: const EdgeInsetsDirectional.only(start: 4, bottom: 10),
      // **من اليمين**: `end` كانت تضعه يساراً في العربية، فيقف عنوانُ القسم
      // في جهةٍ والنصُّ تحته في الأخرى.
      child: Row(
        children: <Widget>[
          _IconTile(icon: icon, size: 30),
          const SizedBox(width: 10),
          Text(
            label,
            style: TextStyle(
              fontFamily: HarajTheme.fontFamily,
              fontSize: 15,
              fontWeight: FontWeight.w700,
              color: palette.ink,
            ),
          ),
        ],
      ),
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
      padding: const EdgeInsets.symmetric(vertical: 14),
      child: Column(
        children: <Widget>[
          if (icon case final IconData glyph) ...<Widget>[
            Icon(
              glyph,
              size: 40,
              color: palette.inkMuted.withValues(alpha: 0.35),
            ),
            const SizedBox(height: 10),
          ],
          Text(
            message,
            textAlign: TextAlign.center,
            style: TextStyle(
              fontFamily: HarajTheme.fontFamily,
              fontSize: 13,
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
        // المحتوى في كرتٍ زجاجيّ — تصميمُ الزجاج (٣ أكتوبر ٢٠٢٦): جملةٌ
        // سائبةٌ على أرضيّةٍ متدرّجة تضيع، وفي كرتٍ تُقرأ حالةً لا فراغاً.
        _Card(
          child: _EmptyNote(
            message: l10n.walletNoSubscriptions,
            icon: Icons.assignment_outlined,
          ),
        ),
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
        _Card(
          child: switch (movements) {
            AsyncData(value: final List<LedgerMovement> rows)
                when rows.isEmpty =>
              _EmptyNote(
                message: l10n.walletNoOperations,
                icon: Icons.schedule_rounded,
              ),
            // خيطٌ رفيعٌ بين الحركات: صفوفٌ متلاصقةٌ في كرتٍ واحد تُقرأ فقرةً.
            AsyncData(value: final List<LedgerMovement> rows) => Column(
              children: <Widget>[
                for (final (index, movement) in rows.indexed) ...<Widget>[
                  if (index > 0)
                    Divider(
                      height: 20,
                      color: palette.navInactive.withValues(alpha: 0.7),
                    ),
                  _MovementRow(movement: movement),
                ],
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
              padding: const EdgeInsets.symmetric(vertical: 14),
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
        ),
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

    return Row(
      crossAxisAlignment: CrossAxisAlignment.center,
      children: <Widget>[
        const _IconTile(icon: Icons.receipt_long_outlined, size: 34),
        const SizedBox(width: 12),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Text(
                // الوصفُ عربيٌّ من الخادم ويُعرض حرفياً.
                movement.description,
                style: TextStyle(
                  fontFamily: HarajTheme.fontFamily,
                  fontSize: 13,
                  fontWeight: FontWeight.w600,
                  color: palette.ink,
                ),
              ),
              const SizedBox(height: 2),
              Text(
                movement.bucketLabel,
                style: TextStyle(
                  fontFamily: HarajTheme.fontFamily,
                  fontSize: 11.5,
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
            fontSize: 14,
            fontWeight: FontWeight.w700,
            color: palette.goldDeep,
          ),
        ),
      ],
    );
  }
}
