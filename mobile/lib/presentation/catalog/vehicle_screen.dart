import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app/providers.dart';
import '../../domain/catalog/entities/vehicle_detail.dart';
import '../../domain/catalog/entities/vehicle_summary.dart';
import '../../domain/common/failure.dart';
import '../../l10n/generated/app_localizations.dart';
import '../common/failure_message.dart';
import '../common/money_text.dart';
import '../common/snapshot_view.dart';
import 'favourites_controller.dart';
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

    final vehicle = state.value?.value;

    return Scaffold(
      appBar: AppBar(
        title: Text(
          vehicle?.title ?? AppLocalizations.of(context).vehiclesTitle,
        ),
        actions: <Widget>[
          // القلب لا يظهر قبل وصول الكرت: زرٌّ يعرض حالةً لا يعرفها بعد
          // يقول «غير محفوظة» عن محفوظة، والضغط عليه حينها يحذفها.
          if (vehicle != null)
            _FavouriteButton(vehicleId: vehicleId, card: vehicle.card),
        ],
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
                  // نفس مال الكرت حرفياً: الرسوم ومعها الضريبة. سعرٌ واحد
                  // للمركبة في كل شاشة، وإلا اختلفت الأرقام أمام العميل كما
                  // اختلفت في v1 (المادة ٤-٥).
                  Text(l10n.vehicleAdminFee, style: theme.textTheme.bodyMedium),
                  MoneyText(
                    vehicle.card.adminFee,
                    style: theme.textTheme.titleLarge,
                  ),
                  Text(
                    l10n.vehicleAdminFeeWithVat,
                    style: theme.textTheme.bodyMedium,
                  ),
                  MoneyText(
                    vehicle.card.adminFeeWithVat,
                    style: theme.textTheme.bodyLarge,
                  ),
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

/// زرّ المفضلة — حالتُه من الخادم، وفعلُه عليه.
///
/// **مقفولٌ أثناء الطلب** (`_busy`): ضغطتان سريعتان تُرسلان إضافةً وحذفاً معاً،
/// فيبقى الحال على عكس ما تُظهره الشاشة حتى تُعاد القراءة.
class _FavouriteButton extends ConsumerStatefulWidget {
  const _FavouriteButton({required this.vehicleId, required this.card});

  final String vehicleId;
  final VehicleSummary card;

  @override
  ConsumerState<_FavouriteButton> createState() => _FavouriteButtonState();
}

class _FavouriteButtonState extends ConsumerState<_FavouriteButton> {
  bool _busy = false;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final isFavourite = widget.card.isFavourite;

    return IconButton(
      onPressed: _busy ? null : () => _toggle(isFavourite),
      icon: Icon(isFavourite ? Icons.favorite : Icons.favorite_border),
      tooltip: isFavourite ? l10n.favouriteRemove : l10n.favouriteAdd,
    );
  }

  Future<void> _toggle(bool isFavourite) async {
    setState(() => _busy = true);
    try {
      await ref.read(toggleFavouriteProvider)(
        vehicleId: widget.vehicleId,
        isFavourite: isFavourite,
      );
      if (!mounted) return;
      final l10n = AppLocalizations.of(context);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            isFavourite ? l10n.favouriteRemoved : l10n.favouriteAdded,
          ),
        ),
      );
    } on Failure catch (failure) {
      // رسالة الخادم كما جاءت — لا نصٌّ عندنا مكانها (المادة ٤-٥).
      if (!mounted) return;
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text(failureMessage(context, failure))));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }
}
