import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app/providers.dart';
import '../../domain/catalog/entities/vehicle_detail.dart';
import '../../l10n/generated/app_localizations.dart';
import '../common/money_text.dart';
import '../common/snapshot_view.dart';
import 'widgets/vehicle_gallery.dart';

/// صفحة المركبة: الصور والمواصفات والسعر (T709).
///
/// **السعر `reservePrice` ولا شيء غيره** — نفس الحقل الذي يعرضه الكرت، فلا
/// يقرأ العميل رقمين لمركبة واحدة (المادة ٤-٥، ودليل النظام §8-3). ولا حساب
/// هنا: المبلغ يُعرض كما وصل نصّاً عبر `MoneyText`.
///
/// وحالة المزايدة تأتي جاهزة من الخادم (`biddingOpen`). الشاشة لا تقارن
/// وقت المزاد بساعة الجهاز لتستنتجها: ساعة الجهاز ليست ساعة الخادم، والقرار
/// نقطةٌ واحدة في `apps/bidding/eligibility.py`.
class VehicleScreen extends ConsumerWidget {
  const VehicleScreen({required this.vehicleId, super.key});

  final String vehicleId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final state = ref.watch(vehicleProvider(vehicleId));

    return Scaffold(
      appBar: AppBar(
        title: Text(
          state.value?.value.title ??
              AppLocalizations.of(context).vehiclesTitle,
        ),
      ),
      body: SnapshotView(
        state: state,
        onRetry: () => ref.invalidate(vehicleProvider(vehicleId)),
        builder: (context, snapshot) => _Vehicle(vehicle: snapshot.value),
      ),
    );
  }
}

class _Vehicle extends StatelessWidget {
  const _Vehicle({required this.vehicle});

  final VehicleDetail vehicle;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final theme = Theme.of(context);
    final price = vehicle.reservePrice;

    return ListView(
      padding: const EdgeInsets.only(bottom: 24),
      children: <Widget>[
        VehicleGallery(imageUrls: vehicle.imageUrls),
        Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Text(vehicle.title, style: theme.textTheme.headlineSmall),
              const SizedBox(height: 4),
              Text(
                l10n.vehicleLot(vehicle.lotNumber),
                style: theme.textTheme.bodySmall,
              ),
              const SizedBox(height: 12),
              Wrap(
                crossAxisAlignment: WrapCrossAlignment.center,
                spacing: 8,
                runSpacing: 4,
                children: <Widget>[
                  Text(
                    l10n.vehicleReservePrice,
                    style: theme.textTheme.bodyMedium,
                  ),
                  if (price == null)
                    Text(
                      l10n.vehicleReservePriceUnset,
                      style: theme.textTheme.bodyLarge,
                    )
                  else
                    MoneyText(price, style: theme.textTheme.titleLarge),
                ],
              ),
              const SizedBox(height: 8),
              Text(
                vehicle.biddingOpen
                    ? l10n.vehicleBiddingOpen
                    : l10n.vehicleBiddingClosed,
                style: theme.textTheme.bodyMedium,
              ),
              const SizedBox(height: 24),
              Text(
                l10n.vehicleSpecifications,
                style: theme.textTheme.titleMedium,
              ),
              const SizedBox(height: 8),
              if (vehicle.specifications.isEmpty)
                // مركبةٌ بمواصفات ناقصة تُعرض ناقصة: صفٌّ مخترع أسوأ من صفٍّ
                // غائب، ولا يملك التطبيق ما يملؤه به.
                Text(l10n.vehicleNoSpecifications)
              else
                ...vehicle.specifications.map(
                  (specification) => Padding(
                    padding: const EdgeInsets.symmetric(vertical: 4),
                    child: Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: <Widget>[
                        SizedBox(
                          width: 140,
                          // التسمية العربية من الخادم — لا خريطة أسماء هنا.
                          child: Text(
                            specification.label,
                            style: theme.textTheme.bodySmall,
                          ),
                        ),
                        Expanded(child: Text(specification.value)),
                      ],
                    ),
                  ),
                ),
            ],
          ),
        ),
      ],
    );
  }
}
