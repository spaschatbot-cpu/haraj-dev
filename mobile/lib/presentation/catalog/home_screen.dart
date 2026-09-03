import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app/providers.dart';
import '../../app/router.dart';
import '../../domain/catalog/entities/auction_summary.dart';
import '../../l10n/generated/app_localizations.dart';
import '../common/snapshot_view.dart';
import 'widgets/auction_card.dart';
import 'widgets/countdown_text.dart';

/// الرئيسية: المزادات الجارية والقادمة (T707).
///
/// **القسمة من الخادم.** الشاشة لا تنظر في حالة مزادٍ لتقرّر أين تضعه؛
/// المستودع يسأل مرتين — مرة عن الجارية ومرة عن المجدولة — وتعرض كلَّ ردٍّ
/// تحت عنوانه. لو صنّفت الشاشة بنفسها لصار لـ«جارٍ» تعريفٌ ثانٍ يعيش هنا،
/// ويفترق عن `apps/auctions/states.py` عند أول حالة جديدة (المادة ٤-٥).
class HomeScreen extends ConsumerWidget {
  const HomeScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = AppLocalizations.of(context);

    return Scaffold(
      appBar: AppBar(title: Text(l10n.homeTitle)),
      body: SnapshotView(
        state: ref.watch(homeAuctionsProvider),
        onRetry: () => ref.invalidate(homeAuctionsProvider),
        builder: (context, snapshot) => _Auctions(auctions: snapshot.value),
      ),
    );
  }
}

class _Auctions extends StatelessWidget {
  const _Auctions({required this.auctions});

  final HomeAuctions auctions;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);

    if (auctions.isEmpty) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Text(l10n.homeEmpty, textAlign: TextAlign.center),
        ),
      );
    }

    return ListView(
      children: <Widget>[
        if (auctions.running.isNotEmpty)
          ..._section(
            context,
            title: l10n.homeRunningSection,
            auctions: auctions.running,
            // مزادٌ جارٍ: ما يهمّ المزايد هو كم بقي قبل أن يُقفل.
            target: CountdownTarget.end,
          ),
        if (auctions.upcoming.isNotEmpty)
          ..._section(
            context,
            title: l10n.homeUpcomingSection,
            auctions: auctions.upcoming,
            target: CountdownTarget.start,
          ),
      ],
    );
  }

  Iterable<Widget> _section(
    BuildContext context, {
    required String title,
    required List<AuctionSummary> auctions,
    required CountdownTarget target,
  }) sync* {
    yield Padding(
      padding: const EdgeInsets.fromLTRB(16, 16, 16, 4),
      child: Text(title, style: Theme.of(context).textTheme.titleLarge),
    );
    for (final auction in auctions) {
      yield AuctionCard(
        key: ValueKey<String>(auction.id),
        auction: auction,
        countdownTarget: target,
        onTap: () => Routes.goToAuctionVehicles(context, auction.id),
      );
    }
  }
}
