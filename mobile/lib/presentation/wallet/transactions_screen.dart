import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../app/router.dart';
import '../../app/theme.dart';
import '../../domain/common/failure.dart';
import '../../domain/wallet/entities/ledger_movement.dart';
import '../../domain/wallet/entities/wallet_balance.dart';
import '../../l10n/generated/app_localizations.dart';
import '../common/failure_message.dart';
import '../common/failure_view.dart';
import '../common/haraj_app_bar.dart';
import '../common/money_text.dart';
import '../common/saudi_time.dart';
import '../common/stale_data_banner.dart';
import 'transactions_controller.dart';

/// كشف الحركات (T712).
///
/// كل سطر هنا **قيد** في الدفتر، لا ملخّص بجانبه: الوصف عربيٌّ من الخادم،
/// والاتجاه من الخادم، والمبلغ نصّ يُعرض كما وصل. لا شيء في هذه الشاشة يجمع
/// ولا يطرح ولا يستنتج «دخل أم خرج» من إشارة المبلغ.
///
/// حين تُفتح بدلو، فهي النصف الثاني من المادة ١-٦: الرقم في المحفظة يُفتح على
/// القيود التي تفسّره. والترشيح يُرسَل إلى الخادم — لا ترشيح في الذاكرة هنا.
class TransactionsScreen extends ConsumerStatefulWidget {
  const TransactionsScreen({this.bucket, super.key});

  /// الدلو المطلوب، أو `null` للكشف كله.
  final WalletBucketKind? bucket;

  @override
  ConsumerState<TransactionsScreen> createState() => _TransactionsScreenState();
}

class _TransactionsScreenState extends ConsumerState<TransactionsScreen> {
  final ScrollController _scroll = ScrollController();

  @override
  void initState() {
    super.initState();
    _scroll.addListener(_onScroll);
  }

  @override
  void dispose() {
    _scroll
      ..removeListener(_onScroll)
      ..dispose();
    super.dispose();
  }

  /// الترقيم اللانهائي: الاقتراب من القاع يطلب الصفحة التالية. الزرّ في الذيل
  /// يبقى موجوداً لمن لا يصل إليه التمرير (قارئ شاشة، قائمة أقصر من الشاشة).
  void _onScroll() {
    if (!_scroll.hasClients) return;
    final position = _scroll.position;
    if (position.pixels >= position.maxScrollExtent - 240) {
      unawaited(_controller.loadMore());
    }
  }

  TransactionsController get _controller =>
      ref.read(transactionsControllerProvider(widget.bucket).notifier);

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final state = ref.watch(transactionsControllerProvider(widget.bucket));

    final palette = HarajPalette.of(context);

    // تصميمُ الزجاج الأبيض بطلب المالك (٣ أكتوبر ٢٠٢٦): شاشةٌ شفّافة فوق
    // `GlassBackdrop`، وكلُّ قيدٍ كرتٌ زجاجيٌّ منفصل بدل صفوفٍ يفصلها خطّ.
    return Scaffold(
      backgroundColor: Colors.transparent,
      appBar: HarajAppBar(title: l10n.transactionsTitle),
      body: switch (state) {
        AsyncData(value: final data) => Column(
          children: [
            StaleDataBanner(snapshot: data.snapshot),
            _Header(bucket: widget.bucket, total: data.total),
            Expanded(
              child: data.movements.isEmpty
                  ? Center(
                      child: Padding(
                        padding: const EdgeInsets.all(24),
                        child: Column(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Icon(
                              Icons.receipt_long_outlined,
                              size: 44,
                              color: palette.inkMuted.withValues(alpha: 0.35),
                            ),
                            const SizedBox(height: 12),
                            Text(
                              l10n.transactionsEmpty,
                              textAlign: TextAlign.center,
                              style: TextStyle(
                                fontFamily: HarajTheme.fontFamily,
                                fontSize: 13.5,
                                color: palette.inkMuted,
                              ),
                            ),
                          ],
                        ),
                      ),
                    )
                  : RefreshIndicator(
                      onRefresh: _controller.refresh,
                      child: ListView.separated(
                        controller: _scroll,
                        padding: EdgeInsets.fromLTRB(
                          16,
                          4,
                          16,
                          16 + MediaQuery.paddingOf(context).bottom,
                        ),
                        itemCount: data.movements.length + 1,
                        separatorBuilder: (context, index) =>
                            const SizedBox(height: 10),
                        itemBuilder: (context, index) =>
                            index == data.movements.length
                            ? _Footer(
                                state: data,
                                onLoadMore: _controller.loadMore,
                              )
                            : _MovementTile(movement: data.movements[index]),
                      ),
                    ),
            ),
          ],
        ),
        AsyncError(:final error) => Center(
          child: FailureView(
            failure: error is Failure ? error : UnexpectedFailure(error),
            onRetry: _controller.refresh,
          ),
        ),
        _ => const Center(child: CircularProgressIndicator()),
      },
    );
  }
}

/// سطر تعريفي فوق الكشف: هل هو مرشَّح، وكم حركة عُرضت.
class _Header extends StatelessWidget {
  const _Header({required this.bucket, required this.total});

  final WalletBucketKind? bucket;
  final int total;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final palette = HarajPalette.of(context);
    final small = TextStyle(
      fontFamily: HarajTheme.fontFamily,
      fontSize: 12,
      color: palette.inkMuted,
    );

    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 12, 16, 10),
      child: _GlassCard(
        padding: const EdgeInsets.fromLTRB(14, 12, 10, 12),
        child: Row(
          children: [
            const _IconTile(icon: Icons.filter_list_rounded),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    bucket == null
                        // اسم الدلو لا يُكتب هنا: أسماء الدلاء عربية من الخادم،
                        // وشاشةٌ تحفظ نسخة منها تفترق عنه (المادة ٤-٥).
                        ? l10n.transactionsAll
                        : l10n.transactionsFiltered,
                    style: TextStyle(
                      fontFamily: HarajTheme.fontFamily,
                      fontSize: 13.5,
                      fontWeight: FontWeight.w700,
                      color: palette.ink,
                    ),
                  ),
                  Text(l10n.transactionsTotal(total), style: small),
                ],
              ),
            ),
            if (bucket != null)
              TextButton(
                onPressed: () => context.goNamed(Routes.walletStatement),
                style: TextButton.styleFrom(
                  foregroundColor: palette.gold,
                  textStyle: const TextStyle(
                    fontFamily: HarajTheme.fontFamily,
                    fontWeight: FontWeight.w700,
                  ),
                ),
                child: Text(l10n.transactionsShowAll),
              ),
          ],
        ),
      ),
    );
  }
}

/// الكرتُ الزجاجيّ — أبيضُ شفّافٌ بحدٍّ رفيعٍ وظلٍّ ناعم (٣ أكتوبر ٢٠٢٦).
class _GlassCard extends StatelessWidget {
  const _GlassCard({
    required this.child,
    this.padding = const EdgeInsets.all(16),
  });

  final Widget child;
  final EdgeInsetsGeometry padding;

  @override
  Widget build(BuildContext context) {
    final palette = HarajPalette.of(context);
    return Container(
      padding: padding,
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

/// مربّعُ الأيقونة — أزرقُ على أزرقَ شفيف.
class _IconTile extends StatelessWidget {
  const _IconTile({required this.icon});

  final IconData icon;

  @override
  Widget build(BuildContext context) {
    final palette = HarajPalette.of(context);
    return Container(
      width: 38,
      height: 38,
      decoration: BoxDecoration(
        color: palette.gold.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(10),
      ),
      child: Icon(icon, size: 19, color: palette.gold),
    );
  }
}

/// حركة واحدة: ماذا حدث، ومتى، وبكم، ومن أي دلو.
class _MovementTile extends StatelessWidget {
  const _MovementTile({required this.movement});

  final LedgerMovement movement;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final palette = HarajPalette.of(context);
    final occurredAt = SaudiTime.forDisplay(movement.occurredAt);
    final small = TextStyle(
      fontFamily: HarajTheme.fontFamily,
      fontSize: 11.5,
      color: palette.inkMuted,
      height: 1.5,
    );

    // الأيقونةُ من `direction` الذي أرسله الخادم — كالإشارة تحت، لا من المبلغ.
    final icon = switch (movement.direction) {
      LedgerDirection.incoming => Icons.south_west_rounded,
      LedgerDirection.outgoing => Icons.north_east_rounded,
      LedgerDirection.unknown => Icons.swap_vert_rounded,
    };

    return _GlassCard(
      padding: const EdgeInsets.all(14),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _IconTile(icon: icon),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  movement.description,
                  style: TextStyle(
                    fontFamily: HarajTheme.fontFamily,
                    fontSize: 13.5,
                    fontWeight: FontWeight.w700,
                    color: palette.ink,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  '${movement.bucketLabel} · '
                  '${l10n.dateTimeAt(occurredAt, occurredAt)}',
                  style: small,
                ),
                if (movement.reference != null)
                  Text(
                    l10n.movementReference(movement.reference!),
                    style: small,
                  ),
              ],
            ),
          ),
          const SizedBox(width: 10),
          _SignedAmount(movement: movement),
        ],
      ),
    );
  }
}

/// المبلغ بإشارته.
///
/// الإشارة من `direction` الذي أرسله الخادم، لا من قراءة المبلغ: المبالغ تصل
/// موجبة دائماً، واستنتاج «خرج» من شكل الرقم اجتهاد في اصطلاح الدفتر.
class _SignedAmount extends StatelessWidget {
  const _SignedAmount({required this.movement});

  final LedgerMovement movement;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final palette = HarajPalette.of(context);

    // ألوانُ اللوحة لا `colorScheme`: الأزرقُ للداخل والكحليُّ للخارج، كبقيّة
    // تصميم الزجاج (٣ أكتوبر ٢٠٢٦).
    final (label, sign, color) = switch (movement.direction) {
      LedgerDirection.incoming => (l10n.movementIncoming, '+', palette.gold),
      LedgerDirection.outgoing => (l10n.movementOutgoing, '−', palette.ink),
      // اتجاه لم نره: يُعرض المبلغ بلا إشارة بدل أن نخترع له واحدة.
      LedgerDirection.unknown => ('', '', palette.ink),
    };
    final style = TextStyle(
      fontFamily: HarajTheme.fontFamily,
      fontSize: 15,
      fontWeight: FontWeight.w700,
      color: color,
    );

    return Semantics(
      label: label,
      child: Directionality(
        textDirection: TextDirection.ltr,
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            if (sign.isNotEmpty) Text(sign, style: style),
            const SizedBox(width: 4),
            MoneyText(movement.money, style: style),
          ],
        ),
      ),
    );
  }
}

/// ذيل القائمة: تحميل، أو فشل صفحة تالية، أو زرّ «المزيد».
class _Footer extends StatelessWidget {
  const _Footer({required this.state, required this.onLoadMore});

  final TransactionsState state;
  final Future<void> Function() onLoadMore;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final palette = HarajPalette.of(context);

    if (state.isLoadingMore) {
      return const Padding(
        padding: EdgeInsets.all(16),
        child: Center(child: CircularProgressIndicator()),
      );
    }

    final failure = state.loadMoreFailure;
    if (failure != null) {
      return Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          children: [
            Text(
              failureMessage(context, failure),
              textAlign: TextAlign.center,
              style: TextStyle(
                fontFamily: HarajTheme.fontFamily,
                fontSize: 12.5,
                color: palette.inkMuted,
              ),
            ),
            const SizedBox(height: 10),
            FilledButton(
              onPressed: onLoadMore,
              style: FilledButton.styleFrom(
                backgroundColor: palette.gold,
                foregroundColor: Colors.white,
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
              child: Text(l10n.retry),
            ),
          ],
        ),
      );
    }

    if (!state.hasMore) return const SizedBox(height: 24);

    return Padding(
      padding: const EdgeInsets.all(16),
      child: Center(
        child: TextButton(
          onPressed: onLoadMore,
          style: TextButton.styleFrom(
            foregroundColor: palette.gold,
            textStyle: const TextStyle(
              fontFamily: HarajTheme.fontFamily,
              fontWeight: FontWeight.w700,
            ),
          ),
          child: Text(l10n.transactionsLoadMore),
        ),
      ),
    );
  }
}
