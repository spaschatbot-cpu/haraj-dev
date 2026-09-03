import 'package:flutter/material.dart';

import '../../../domain/catalog/entities/auction_summary.dart';
import '../../../l10n/generated/app_localizations.dart';
import '../../common/saudi_time.dart';
import 'countdown_text.dart';

/// كرت المزاد — مكوّن واحد، وللسبب نفسه الذي لكرت المركبة.
///
/// قائمة واحدة تحمل هذا الشكل اليوم، وقائمتان غداً. تعريفٌ واحد يعني أن حقلاً
/// يُضاف يظهر في الاثنتين، لا في التي تذكّرها أحدهم.
///
/// التاريخ يُحوَّل إلى التوقيت السعودي في `SaudiTime` وحدها، والعدّاد يعمل على
/// الفرق بين لحظتين UTC — فلا يوجد في هذا الملف `add(Duration(hours: 3))`.
class AuctionCard extends StatelessWidget {
  const AuctionCard({
    required this.auction,
    required this.countdownTarget,
    this.onTap,
    super.key,
  });

  final AuctionSummary auction;

  /// إلى أين يعدّ العدّاد — يقرّره القسم الذي جاء منه المزاد، لا الكرت.
  final CountdownTarget countdownTarget;

  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final theme = Theme.of(context);
    final startsAt = SaudiTime.forDisplay(auction.startsAt);
    final endsAt = SaudiTime.forDisplay(auction.endsAt);

    return Card(
      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
      child: InkWell(
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Text(auction.title, style: theme.textTheme.titleMedium),
              const SizedBox(height: 8),
              Text(
                l10n.auctionStartsAt(startsAt, startsAt),
                style: theme.textTheme.bodySmall,
              ),
              Text(
                l10n.auctionEndsAt(endsAt, endsAt),
                style: theme.textTheme.bodySmall,
              ),
              const SizedBox(height: 8),
              CountdownText(
                at: countdownTarget == CountdownTarget.start
                    ? auction.startsAt
                    : auction.endsAt,
                target: countdownTarget,
              ),
              const SizedBox(height: 8),
              Text(
                l10n.auctionVehiclesCount(auction.vehiclesCount),
                style: theme.textTheme.bodySmall,
              ),
            ],
          ),
        ),
      ),
    );
  }
}
