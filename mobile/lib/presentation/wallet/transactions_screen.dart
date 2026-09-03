import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../app/router.dart';
import '../../domain/common/failure.dart';
import '../../domain/wallet/entities/ledger_movement.dart';
import '../../domain/wallet/entities/wallet_balance.dart';
import '../../l10n/generated/app_localizations.dart';
import '../common/failure_message.dart';
import '../common/failure_view.dart';
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

    return Scaffold(
      appBar: AppBar(title: Text(l10n.transactionsTitle)),
      body: switch (state) {
        AsyncData(value: final data) => Column(
          children: [
            StaleDataBanner(snapshot: data.snapshot),
            _Header(bucket: widget.bucket, total: data.total),
            Expanded(
              child: data.movements.isEmpty
                  ? Center(child: Text(l10n.transactionsEmpty))
                  : RefreshIndicator(
                      onRefresh: _controller.refresh,
                      child: ListView.separated(
                        controller: _scroll,
                        itemCount: data.movements.length + 1,
                        separatorBuilder: (context, index) =>
                            const Divider(height: 1),
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
    final theme = Theme.of(context);

    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 12, 16, 8),
      child: Row(
        children: [
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
                  style: theme.textTheme.bodySmall,
                ),
                Text(
                  l10n.transactionsTotal(total),
                  style: theme.textTheme.bodySmall,
                ),
              ],
            ),
          ),
          if (bucket != null)
            TextButton(
              onPressed: () => context.goNamed(Routes.walletStatement),
              child: Text(l10n.transactionsShowAll),
            ),
        ],
      ),
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
    final theme = Theme.of(context);
    final occurredAt = SaudiTime.forDisplay(movement.occurredAt);

    return ListTile(
      title: Text(movement.description),
      subtitle: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            '${movement.bucketLabel} · '
            '${l10n.dateTimeAt(occurredAt, occurredAt)}',
            style: theme.textTheme.bodySmall,
          ),
          if (movement.reference != null)
            Text(
              l10n.movementReference(movement.reference!),
              style: theme.textTheme.bodySmall,
            ),
        ],
      ),
      trailing: _SignedAmount(movement: movement),
      isThreeLine: movement.reference != null,
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
    final theme = Theme.of(context);

    final (label, sign, color) = switch (movement.direction) {
      LedgerDirection.incoming => (
        l10n.movementIncoming,
        '+',
        theme.colorScheme.primary,
      ),
      LedgerDirection.outgoing => (
        l10n.movementOutgoing,
        '−',
        theme.colorScheme.onSurface,
      ),
      // اتجاه لم نره: يُعرض المبلغ بلا إشارة بدل أن نخترع له واحدة.
      LedgerDirection.unknown => ('', '', theme.colorScheme.onSurface),
    };

    return Semantics(
      label: label,
      child: Directionality(
        textDirection: TextDirection.ltr,
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            if (sign.isNotEmpty)
              Text(
                sign,
                style: theme.textTheme.titleMedium?.copyWith(color: color),
              ),
            const SizedBox(width: 4),
            MoneyText(
              movement.money,
              style: theme.textTheme.titleMedium?.copyWith(color: color),
            ),
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
            Text(failureMessage(context, failure), textAlign: TextAlign.center),
            const SizedBox(height: 8),
            FilledButton(onPressed: onLoadMore, child: Text(l10n.retry)),
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
          child: Text(l10n.transactionsLoadMore),
        ),
      ),
    );
  }
}
