import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../app/router.dart';
import '../../domain/common/failure.dart';
import '../../domain/common/snapshot.dart';
import '../../domain/wallet/entities/wallet_balance.dart';
import '../../l10n/generated/app_localizations.dart';
import '../common/failure_view.dart';
import '../common/money_text.dart';
import '../common/saudi_time.dart';
import '../common/stale_data_banner.dart';
import 'wallet_controller.dart';

/// المحفظة (T711).
///
/// **الدلاء مفصَّلة، ولا رقم واحد يجمعها.** في v1 كان الرقم الواحد يشمل المحجوز
/// فيقرؤه العميل على أنه متاح، ثم يزايد على فلوس مربوطة بمزاد آخر. الشاشة هنا
/// لا تجمع ولا تطرح: ما تعرضه هو ما أرسله الخادم، مبلغاً مبلغاً.
///
/// وكل رقم قابل لفتحه على القيود التي تفسّره (المادة ١-٦): «الرقم ده جاي منين»
/// سؤال له إجابة بضغطة، لا مكالمة دعم.
class WalletScreen extends ConsumerWidget {
  const WalletScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = AppLocalizations.of(context);
    final state = ref.watch(walletBalanceProvider);

    return Scaffold(
      appBar: AppBar(title: Text(l10n.walletTitle)),
      body: switch (state) {
        AsyncData(value: final snapshot) => RefreshIndicator(
          onRefresh: () async => ref.refresh(walletBalanceProvider.future),
          child: _Balance(snapshot: snapshot),
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

class _Balance extends StatelessWidget {
  const _Balance({required this.snapshot});

  final Snapshot<WalletBalance> snapshot;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final theme = Theme.of(context);
    final balance = snapshot.value;
    final asOf = SaudiTime.forDisplay(balance.asOf);

    return ListView(
      padding: const EdgeInsets.only(bottom: 32),
      children: [
        StaleDataBanner(snapshot: snapshot),
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 16, 16, 8),
          child: Text(
            l10n.walletAsOf(asOf, asOf),
            style: theme.textTheme.bodySmall,
          ),
        ),
        if (balance.buckets.isEmpty)
          Padding(
            padding: const EdgeInsets.all(24),
            child: Text(l10n.walletEmpty, textAlign: TextAlign.center),
          )
        else
          // لا `total` هنا ولا في أي مكان: الفيز 008 يمنع جمع الدلاء، وأي
          // مجموع يحتاجه العرض يأتي حقلاً من الخادم بقيده الذي يثبته.
          for (final bucket in balance.buckets) _BucketCard(bucket: bucket),
        const _TopUpEntry(),
      ],
    );
  }
}

/// دلو واحد: اسمه من الخادم، ومبلغه كما وصل، وأسباب حجزه، ومدخله إلى قيوده.
class _BucketCard extends StatelessWidget {
  const _BucketCard({required this.bucket});

  final WalletBucket bucket;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final theme = Theme.of(context);

    return Card(
      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(bucket.label, style: theme.textTheme.titleMedium),
            const SizedBox(height: 8),
            MoneyText(bucket.money, style: theme.textTheme.headlineSmall),
            if (bucket.holds.isNotEmpty) ...[
              const SizedBox(height: 12),
              Text(l10n.walletHoldsTitle, style: theme.textTheme.labelLarge),
              // كل حجز بسببه ومرجعه: «الحجز مسمّى دائماً». رقم محجوز بلا سبب
              // هو ما جعل عملاء v1 يظنّون فلوسهم متاحة.
              for (final hold in bucket.holds) _HoldRow(hold: hold),
            ],
            const SizedBox(height: 8),
            Align(
              alignment: AlignmentDirectional.centerStart,
              child: _StatementLink(bucket: bucket),
            ),
          ],
        ),
      ),
    );
  }
}

class _HoldRow extends StatelessWidget {
  const _HoldRow({required this.hold});

  final WalletHold hold;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final theme = Theme.of(context);

    return Padding(
      padding: const EdgeInsets.only(top: 8),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // السبب عربيٌّ من الخادم ويُعرض حرفياً.
                Text(hold.reason, style: theme.textTheme.bodyMedium),
                Text(
                  l10n.movementReference(hold.reference),
                  style: theme.textTheme.bodySmall,
                ),
              ],
            ),
          ),
          MoneyText(hold.money, style: theme.textTheme.bodyMedium),
        ],
      ),
    );
  }
}

/// مدخل الرقم إلى القيود التي تفسّره (المادة ١-٦).
class _StatementLink extends StatelessWidget {
  const _StatementLink({required this.bucket});

  final WalletBucket bucket;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);

    // دلو لا يعرف هذا الإصدار اسمه لا يمكن أن يُسأل عنه الخادم، فلا يُعرض له
    // مدخل يفتح كشفاً غير مرشَّح ويبدو كأنه تفسير لهذا الرقم.
    if (bucket.kind == WalletBucketKind.unknown) return const SizedBox.shrink();

    return TextButton(
      onPressed: () => context.pushNamed(
        Routes.walletStatement,
        queryParameters: <String, String>{
          Routes.bucketParameter: bucket.kind.name,
        },
      ),
      child: Text(l10n.walletOpenStatement),
    );
  }
}

/// مدخل الشحن بالبطاقة (T713).
///
/// بلا خانة مبلغ هنا أيضاً: المبلغ يحدّده الخادم، والزرّ يفتح الشاشة التي
/// تكتب النيّة عنده قبل أن يصل العميل إلى أي بوابة.
class _TopUpEntry extends StatelessWidget {
  const _TopUpEntry();

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);

    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 8, 16, 0),
      child: Align(
        alignment: AlignmentDirectional.centerStart,
        child: FilledButton(
          onPressed: () => context.pushNamed(Routes.walletTopUp),
          child: Text(l10n.topUpTitle),
        ),
      ),
    );
  }
}
