import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../app/router.dart';
import '../../app/theme.dart';
import '../../domain/activity/entities/purchase.dart';
import '../../domain/common/failure.dart';
import '../../domain/common/snapshot.dart';
import '../../l10n/generated/app_localizations.dart';
import '../activity/activity_providers.dart';
import '../common/failure_view.dart';
import '../common/haraj_app_bar.dart';
import '../common/riyal_text.dart';

/// صفحة «مشترياتي» — على تصميم المالك (١٣ سبتمبر ٢٠٢٦).
///
/// **من المزوّد الحقيقيّ** (`myPurchasesProvider`): القائمةُ ما رسا على العميل،
/// والفارغُ حالةٌ تُعرض لا رقمٌ يُختلَق. وشريطُ الدفع أسفلها يقرأ **مختاراته**،
/// ومبلغُه جمعُ أسعارِ ما اختاره — لا رقمٌ من عندنا.
///
/// **والدفعُ غيرُ مفعَّل بعد**: لا مدخلَ في العقد لدفع المشتريات من التطبيق،
/// فالزرّ يقول «لم يُفعَّل بعد» بدل نجاحٍ مزيَّف (شاشة مال).
class PurchasesScreen extends ConsumerStatefulWidget {
  const PurchasesScreen({super.key});

  @override
  ConsumerState<PurchasesScreen> createState() => _PurchasesScreenState();
}

class _PurchasesScreenState extends ConsumerState<PurchasesScreen> {
  final Set<String> _selected = <String>{};

  void _toggle(String id) => setState(() {
    if (!_selected.add(id)) _selected.remove(id);
  });

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final state = ref.watch(myPurchasesProvider);

    return Scaffold(
      appBar: HarajAppBar(title: l10n.accountMenuPurchases),
      body: switch (state) {
        AsyncData(value: final Snapshot<List<Purchase>> snapshot) =>
          _Body(
            purchases: snapshot.value,
            selected: _selected,
            onToggle: _toggle,
            onClear: () => setState(_selected.clear),
          ),
        AsyncError(:final error) => Center(
          child: FailureView(
            failure: error is Failure ? error : UnexpectedFailure(error),
            onRetry: () => ref.invalidate(myPurchasesProvider),
          ),
        ),
        _ => const Center(child: CircularProgressIndicator()),
      },
    );
  }
}

class _Body extends StatelessWidget {
  const _Body({
    required this.purchases,
    required this.selected,
    required this.onToggle,
    required this.onClear,
  });

  final List<Purchase> purchases;
  final Set<String> selected;
  final void Function(String id) onToggle;
  final VoidCallback onClear;

  @override
  Widget build(BuildContext context) {
    // **شريطُ الدفع عائمٌ في الأسفل، والمحتوى يمرّر خلفه** (بطلب المالك ١٣
    // سبتمبر ٢٠٢٦): `Stack` بدل `Column` — القائمةُ تملأ الشاشة بحاشيةٍ سفليّةٍ
    // تكفي الشريطَ فلا يُقصّ آخرُها، والشريطُ فوقها ملتصقٌ بالحافّة. يظهر دائماً
    // حتى مع لا مشتريات، بعددٍ وإجماليٍّ صفر وزرّين معطَّلين.
    const barSpace = 150.0;
    // ارتفاعُ الشريط السفليّ للقشرة بالضبط (`_GoldNavigationBar.barHeight` = ٧٠):
    // `MediaQuery.bottom` هنا أكبرُ منه فيترك فجوةً فوق الفوتر. ثابتٌ مطابقٌ له
    // يُجلس شريطَ الدفع فوق الفوتر تماماً (١٣ سبتمبر ٢٠٢٦).
    const footerHeight = 70.0;
    return Stack(
      children: <Widget>[
        Positioned.fill(
          child: purchases.isEmpty
              ? _EmptyState(bottomPadding: barSpace + footerHeight)
              : ListView.builder(
                  padding: const EdgeInsets.fromLTRB(16, 16, 16, barSpace + footerHeight),
                  itemCount: purchases.length,
                  itemBuilder: (context, i) => _PurchaseCard(
                    purchase: purchases[i],
                    selected: selected.contains(purchases[i].id),
                    onTap: () => onToggle(purchases[i].id),
                  ),
                ),
        ),
        // يُرفَع الشريطُ بمقدار ارتفاع الشريط السفليّ للقشرة (`bottomInset`)
        // فيجلس فوقه تماماً لا خلفه — القشرةُ تمدّ المحتوى خلف شريطها
        // (`extendBody`)، فالموضعُ ٠ يخفيه تحته. بطلب المالك (١٣ سبتمبر ٢٠٢٦).
        Positioned(
          left: 0,
          right: 0,
          bottom: footerHeight,
          child: _PayBar(
            purchases: purchases,
            selected: selected,
            onClear: onClear,
          ),
        ),
      ],
    );
  }
}

/// الحالةُ الفارغة — عربةٌ بعلامة منعٍ، وعنوانٌ وشرحٌ وزرُّ تصفّح.
class _EmptyState extends StatelessWidget {
  const _EmptyState({required this.bottomPadding});

  /// حاشيةٌ سفليّةٌ تكفي شريطَ الدفع العائم فلا يحجب البطاقةَ الفارغة.
  final double bottomPadding;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final palette = HarajPalette.of(context);
    return SingleChildScrollView(
      padding: EdgeInsets.fromLTRB(24, 24, 24, bottomPadding),
      child: Center(
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 40),
          decoration: BoxDecoration(
            color: palette.cardSurface,
            borderRadius: BorderRadius.circular(20),
            border: Border.all(
              color: palette.ink.withValues(alpha: 0.10),
              // حدٌّ متقطّعٌ يُحاكى بحدٍّ رقيق: التقطيعُ يحتاج رسّاماً، والحدُّ
              // الرقيقُ يعطي إحساسَ «مكانٌ فارغٌ ينتظر» نفسَه بلا تكلفة.
            ),
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: <Widget>[
              Container(
                width: 96,
                height: 96,
                alignment: Alignment.center,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: palette.gold.withValues(alpha: 0.10),
                ),
                child: Icon(
                  Icons.remove_shopping_cart_outlined,
                  size: 44,
                  color: palette.gold,
                ),
              ),
              const SizedBox(height: 20),
              Text(
                l10n.purchasesEmptyTitle,
                textAlign: TextAlign.center,
                style: TextStyle(
                  color: palette.ink,
                  fontSize: 20,
                  fontWeight: FontWeight.w700,
                  fontFamily: HarajTheme.fontFamily,
                ),
              ),
              const SizedBox(height: 10),
              Text(
                l10n.purchasesEmptyBody,
                textAlign: TextAlign.center,
                style: TextStyle(
                  color: palette.inkMuted,
                  fontSize: 14,
                  height: 1.6,
                  fontFamily: HarajTheme.fontFamily,
                ),
              ),
              const SizedBox(height: 24),
              _DarkButton(
                label: l10n.purchasesBrowse,
                icon: Icons.arrow_back_rounded,
                palette: palette,
                onTap: () => context.go(Routes.homePath),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

/// كرتُ مركبةٍ مشتراة — اختيارُه يدخله في حساب الدفع.
class _PurchaseCard extends StatelessWidget {
  const _PurchaseCard({
    required this.purchase,
    required this.selected,
    required this.onTap,
  });

  final Purchase purchase;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final palette = HarajPalette.of(context);
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: DecoratedBox(
        decoration: BoxDecoration(
          color: palette.cardSurface,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(
            color: selected ? palette.gold : Colors.transparent,
            width: 1.5,
          ),
          boxShadow: <BoxShadow>[
            BoxShadow(
              color: palette.ink.withValues(alpha: 0.05),
              blurRadius: 10,
              offset: const Offset(0, 2),
            ),
          ],
        ),
        child: Material(
          color: Colors.transparent,
          borderRadius: BorderRadius.circular(16),
          clipBehavior: Clip.antiAlias,
          child: InkWell(
            onTap: onTap,
            hoverColor: Colors.transparent,
            splashColor: Colors.transparent,
            highlightColor: Colors.transparent,
            child: Padding(
              padding: const EdgeInsets.all(14),
              child: Row(
                children: <Widget>[
                  Icon(
                    selected
                        ? Icons.check_circle_rounded
                        : Icons.radio_button_unchecked_rounded,
                    color: selected ? palette.gold : palette.inkMuted,
                    size: 24,
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: <Widget>[
                        Text(
                          purchase.title,
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: TextStyle(
                            color: palette.ink,
                            fontSize: 15,
                            fontWeight: FontWeight.w700,
                            fontFamily: HarajTheme.fontFamily,
                          ),
                        ),
                        const SizedBox(height: 4),
                        Text(
                          l10n.purchasesLotNumber(purchase.lotNumber),
                          style: TextStyle(
                            color: palette.inkMuted,
                            fontSize: 12.5,
                            fontFamily: HarajTheme.fontFamily,
                          ),
                        ),
                        const SizedBox(height: 8),
                        RiyalText(
                          purchase.awardedPrice,
                          style: TextStyle(
                            color: palette.gold,
                            fontSize: 16,
                            fontWeight: FontWeight.w700,
                            fontFamily: HarajTheme.fontFamily,
                          ),
                        ),
                      ],
                    ),
                  ),
                  _StatePill(label: purchase.stateLabel, palette: palette),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _StatePill extends StatelessWidget {
  const _StatePill({required this.label, required this.palette});

  final String label;
  final HarajPalette palette;

  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
    decoration: BoxDecoration(
      color: palette.gold.withValues(alpha: 0.10),
      borderRadius: BorderRadius.circular(20),
    ),
    child: Text(
      label,
      style: TextStyle(
        color: palette.goldDeep,
        fontSize: 11.5,
        fontWeight: FontWeight.w700,
        fontFamily: HarajTheme.fontFamily,
      ),
    ),
  );
}

/// شريطُ الدفع السفليّ — عددُ المختار وإجماليُّه، وزرّا الدفع والمسح.
class _PayBar extends StatelessWidget {
  const _PayBar({
    required this.purchases,
    required this.selected,
    required this.onClear,
  });

  final List<Purchase> purchases;
  final Set<String> selected;
  final VoidCallback onClear;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final palette = HarajPalette.of(context);

    // العملةُ من أول مركبة (كلُّها بعملةٍ واحدة)، والمجموعُ نصٌّ لا نطرحه على
    // العميل رقماً مخترعاً: نجمعُ ما اختاره فقط.
    final chosen = purchases.where((p) => selected.contains(p.id)).toList();
    final rawCurrency = purchases.isEmpty
        ? 'SAR'
        : purchases.first.awardedPrice.currency;
    // «ر.س» بدل «SAR» بطلب المالك — والرقمُ جمعُ ما اختاره فقط.
    final currency = rawCurrency == 'SAR' ? 'ر.س' : rawCurrency;
    final total = chosen.fold<double>(
      0,
      (sum, p) => sum + (double.tryParse(p.awardedPrice.amount) ?? 0),
    );

    return Container(
      // **بلا حاشية `MediaQuery.bottom`**: الصفحة داخل قشرةٍ تدفع محتواها من
      // فوق الشريط السفليّ أصلاً، فإضافتُها تحسب ارتفاعَه مرّتين وتترك فجوةً
      // بين هذا الشريط والشريط السفليّ. حُذفت بطلب المالك (١٣ سبتمبر ٢٠٢٦).
      padding: const EdgeInsets.fromLTRB(16, 12, 16, 12),
      decoration: BoxDecoration(
        color: palette.cardSurface,
        boxShadow: <BoxShadow>[
          BoxShadow(
            color: palette.ink.withValues(alpha: 0.10),
            blurRadius: 16,
            offset: const Offset(0, -4),
          ),
        ],
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: <Widget>[
          Row(
            children: <Widget>[
              Expanded(
                child: _Stat(
                  label: l10n.purchasesSelectedCount,
                  value: '${selected.length}',
                  palette: palette,
                ),
              ),
              Container(
                width: 1,
                height: 32,
                color: palette.ink.withValues(alpha: 0.10),
              ),
              Expanded(
                child: _Stat(
                  label: l10n.purchasesTotalDue,
                  value: '${total.toStringAsFixed(2)} $currency',
                  palette: palette,
                  highlight: true,
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Row(
            children: <Widget>[
              // زرُّ الدفع أوسعُ (٣) من زرّ المسح (٢) ليتّسع اسمُه كاملاً بلا
              // قصّ، بطلب المالك (١٣ سبتمبر ٢٠٢٦).
              Expanded(
                flex: 3,
                child: _DarkButton(
                  label: l10n.purchasesPayAll,
                  icon: Icons.credit_card_rounded,
                  palette: palette,
                  onTap: selected.isEmpty
                      ? null
                      : () => ScaffoldMessenger.of(context)
                          ..hideCurrentSnackBar()
                          ..showSnackBar(
                            SnackBar(content: Text(l10n.purchasesPaySoon)),
                          ),
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                flex: 2,
                child: OutlinedButton.icon(
                  onPressed: selected.isEmpty ? null : onClear,
                  icon: const Icon(Icons.cancel_outlined, size: 18),
                  label: Text(l10n.purchasesClear),
                  style: OutlinedButton.styleFrom(
                    foregroundColor: palette.goldDeep,
                    side: BorderSide(
                      color: palette.gold.withValues(alpha: 0.6),
                    ),
                    padding: const EdgeInsets.symmetric(vertical: 14),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(12),
                    ),
                  ),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _Stat extends StatelessWidget {
  const _Stat({
    required this.label,
    required this.value,
    required this.palette,
    this.highlight = false,
  });

  final String label;
  final String value;
  final HarajPalette palette;
  final bool highlight;

  @override
  Widget build(BuildContext context) => Column(
    children: <Widget>[
      Text(
        label,
        style: TextStyle(
          color: palette.inkMuted,
          fontSize: 12.5,
          fontFamily: HarajTheme.fontFamily,
        ),
      ),
      const SizedBox(height: 4),
      Directionality(
        textDirection: TextDirection.ltr,
        child: Text(
          value,
          style: TextStyle(
            color: highlight ? palette.goldDeep : palette.ink,
            fontSize: 16,
            fontWeight: FontWeight.w700,
            fontFamily: HarajTheme.fontFamily,
          ),
        ),
      ),
    ],
  );
}

/// زرٌّ كحليٌّ ممتلئ — نظيرُ زرّ «تصفح المزادات» و«دفع».
class _DarkButton extends StatelessWidget {
  const _DarkButton({
    required this.label,
    required this.icon,
    required this.palette,
    required this.onTap,
  });

  final String label;
  final IconData icon;
  final HarajPalette palette;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final enabled = onTap != null;
    return Material(
      color: Colors.transparent,
      child: InkWell(
        borderRadius: BorderRadius.circular(14),
        onTap: onTap,
        child: Ink(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 14),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(14),
            gradient: LinearGradient(
              begin: Alignment.topRight,
              end: Alignment.bottomLeft,
              colors: <Color>[palette.heroTop, palette.heroBottom],
            ),
            color: enabled ? null : palette.inkMuted,
          ),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: <Widget>[
              // `Flexible` وقصٌّ: الاسمُ طويلٌ وزرٌّ ضيّق، فبلا حدٍّ يفيض أفقيّاً
              // ويظهر شريطُ الطفح الأحمر. حُلّ بطلب المالك (١٣ سبتمبر ٢٠٢٦).
              Flexible(
                child: Text(
                  label,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  textAlign: TextAlign.center,
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 14,
                    fontWeight: FontWeight.w700,
                    fontFamily: HarajTheme.fontFamily,
                  ),
                ),
              ),
              const SizedBox(width: 8),
              Icon(icon, color: Colors.white, size: 18),
            ],
          ),
        ),
      ),
    );
  }
}
