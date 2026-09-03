import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app/providers.dart';
import '../../domain/bidding/entities/live_bids_update.dart';
import '../../domain/bidding/entities/placed_bid.dart';
import '../../domain/common/failure.dart';
import '../../domain/common/snapshot.dart';
import '../../l10n/generated/app_localizations.dart';
import '../common/failure_message.dart';
import '../common/failure_view.dart';
import '../common/money_text.dart';
import '../common/saudi_time.dart';
import '../common/stale_data_banner.dart';
import 'bidding_controllers.dart';
import 'live_status_banner.dart';

/// مزايداتي.
///
/// ثلاث حالات لا اثنتان: تحميل، وفشل بجواب الخادم وزرّ إعادة، وحالة فارغة
/// مكتوبة. شاشةٌ تعرض دوّامةً إلى الأبد عند سقوط الشبكة عطلٌ لا تصميم — ولذلك
/// أيضاً تظهر البيانات المحفوظة بعلامة «آخر تحديث» بدل شاشة خطأ (H5).
class MyBidsScreen extends ConsumerWidget {
  const MyBidsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = AppLocalizations.of(context);
    final bids = ref.watch(myBidsProvider);
    final live = ref.watch(liveBidsProvider);

    return Scaffold(
      appBar: AppBar(title: Text(l10n.myBidsTitle)),
      body: Column(
        children: [
          LiveStatusBanner(
            connection: live.value?.connection ?? LiveConnection.connecting,
          ),
          Expanded(
            child: bids.when(
              loading: () => const Center(child: CircularProgressIndicator()),
              error: (error, stackTrace) => Center(
                child: FailureView(
                  failure: error is Failure
                      ? error
                      : UnexpectedFailure(error, stackTrace: stackTrace),
                  onRetry: () => ref.invalidate(myBidsProvider),
                ),
              ),
              data: (snapshot) => _Bids(snapshot: snapshot),
            ),
          ),
        ],
      ),
    );
  }
}

class _Bids extends ConsumerWidget {
  const _Bids({required this.snapshot});

  final Snapshot<List<PlacedBid>> snapshot;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = AppLocalizations.of(context);
    final bids = snapshot.value;

    return Column(
      children: [
        StaleDataBanner(snapshot: snapshot),
        Expanded(
          child: bids.isEmpty
              ? Center(
                  child: Padding(
                    padding: const EdgeInsets.all(24),
                    child: Text(
                      l10n.myBidsEmpty,
                      textAlign: TextAlign.center,
                      style: Theme.of(context).textTheme.bodyLarge,
                    ),
                  ),
                )
              : RefreshIndicator(
                  onRefresh: () async => ref.invalidate(myBidsProvider),
                  child: ListView.separated(
                    itemCount: bids.length,
                    separatorBuilder: (context, index) =>
                        const Divider(height: 1),
                    itemBuilder: (context, index) => _BidTile(bid: bids[index]),
                  ),
                ),
        ),
      ],
    );
  }
}

class _BidTile extends ConsumerWidget {
  const _BidTile({required this.bid});

  final PlacedBid bid;

  Future<void> _withdraw(BuildContext context, WidgetRef ref) async {
    final l10n = AppLocalizations.of(context);
    final messenger = ScaffoldMessenger.of(context);

    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(l10n.bidWithdrawConfirmTitle),
        content: Text(
          l10n.bidWithdrawConfirmBody(bid.vehicleTitle ?? bid.vehicleId),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: Text(l10n.cancel),
          ),
          FilledButton(
            onPressed: () => Navigator.of(context).pop(true),
            child: Text(l10n.bidWithdrawAction),
          ),
        ],
      ),
    );
    if (!(confirmed ?? false) || !context.mounted) return;

    try {
      await ref.read(withdrawBidProvider)(bid.id);
      ref.invalidate(myBidsProvider);
      messenger.showSnackBar(SnackBar(content: Text(l10n.bidWithdrawn)));
    } on Failure catch (failure) {
      // جواب الخادم كما جاء: «هذه المزايدة ليست مزايدتك»، «انتهى المزاد»… أي
      // منها أوضح من «تعذّر السحب» التي كنا سنكتبها نحن.
      if (!context.mounted) return;
      messenger.showSnackBar(
        SnackBar(content: Text(failureMessage(context, failure))),
      );
    }
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = AppLocalizations.of(context);
    final theme = Theme.of(context);
    final placedAt = SaudiTime.forDisplay(bid.placedAtUtc);

    return ListTile(
      title: Text(bid.vehicleTitle ?? bid.vehicleId),
      subtitle: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // وصف الحالة عربي من الخادم — لا خريطة حالات هنا.
          Text(bid.stateLabel, style: theme.textTheme.bodySmall),
          Text(
            l10n.bidPlacedAt(placedAt, placedAt),
            style: theme.textTheme.bodySmall,
          ),
          MoneyText(bid.money, style: theme.textTheme.titleMedium),
        ],
      ),
      trailing: bid.offersWithdraw
          ? TextButton(
              onPressed: () => _withdraw(context, ref),
              child: Text(l10n.bidWithdrawAction),
            )
          : null,
      isThreeLine: true,
    );
  }
}
