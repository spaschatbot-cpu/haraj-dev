import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../app/router.dart';
import '../../domain/catalog/entities/vehicle_query.dart';
import '../../domain/common/failure.dart';
import '../../domain/common/snapshot.dart';
import '../../l10n/generated/app_localizations.dart';
import '../common/failure_view.dart';
import '../common/stale_data_banner.dart';
import 'favourites_controller.dart';
import 'widgets/vehicle_results.dart';

/// المفضلة: مركبات حفظها العميل ليعود إليها.
///
/// **نفس كرت التصفّح ونفس مصفوفته** (`VehicleResults`): مركبةٌ في المفضلة ليست
/// نوعاً آخر من المركبات، وكرتٌ ثانٍ لها يعني حقلاً يُضاف في أحدهما ويُنسى في
/// الآخر — وهو ما كان في v1 (المادة ٤-٥).
///
/// **ولا ترقيمَ لا نهائيّاً هنا:** القائمة قائمةُ العميل، وهي قصيرة بطبعها.
/// الصفحة الأولى تكفي، وسحبُ منطق الصفحات إلى هنا يخلط تاسكين.
class FavouritesScreen extends ConsumerWidget {
  const FavouritesScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = AppLocalizations.of(context);
    final state = ref.watch(favouritesProvider);

    return Scaffold(
      appBar: AppBar(title: Text(l10n.favouritesTitle)),
      body: switch (state) {
        AsyncData(value: final snapshot) => RefreshIndicator(
          onRefresh: () async => ref.refresh(favouritesProvider.future),
          child: _Favourites(snapshot: snapshot),
        ),
        AsyncError(:final error) => Center(
          child: FailureView(
            failure: error is Failure ? error : UnexpectedFailure(error),
            onRetry: () => ref.invalidate(favouritesProvider),
          ),
        ),
        _ => const Center(child: CircularProgressIndicator()),
      },
    );
  }
}

class _Favourites extends StatelessWidget {
  const _Favourites({required this.snapshot});

  final Snapshot<VehiclePage> snapshot;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final page = snapshot.value;

    return Column(
      children: <Widget>[
        StaleDataBanner(snapshot: snapshot),
        Expanded(
          child: VehicleResults(
            vehicles: page.vehicles,
            totalCount: page.totalCount,
            // الترقيم مُطفأ صراحةً لا مُهمَل: `hasMore` مِن الخادم قد يقول
            // «نعم» على قائمةٍ طويلة، وتمريرٌ يطلب صفحةً لا أحد يجلبها يعلّق
            // الشاشة على دوّامة لا تنتهي.
            hasMore: false,
            loadingMore: false,
            moreFailure: null,
            onLoadMore: _noPaging,
            onRetryMore: _noPaging,
            emptyMessage: l10n.favouritesEmpty,
            onOpenVehicle: (vehicle) =>
                context.go(Routes.vehicleLocation(vehicle.id)),
            layout: VehicleResultsLayout.grid,
          ),
        ),
      ],
    );
  }

  static void _noPaging() {}
}
