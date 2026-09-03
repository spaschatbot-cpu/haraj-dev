import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../presentation/bidding/bid_screen.dart';
import '../presentation/bidding/my_bids_screen.dart';
import '../presentation/seed/seed_screen.dart';

/// أسماء المسارات — تُستدعى بالاسم لا بالنصّ الحر.
///
/// السبب: الإشعار يفتح الشاشة الصحيحة (معيار H6) بمطابقة اسم مسار، ومسار مكتوب
/// نصّاً في مكانين يفترق فيهما عند أول تعديل (المادة ٤-٥).
abstract final class Routes {
  static const String seed = 'seed';

  /// المزايدة على مركبة بعينها.
  static const String bid = 'bid';

  /// مزايداتي.
  static const String myBids = 'my-bids';
}

/// التوجيه مُعلَن في مكان واحد (T701).
///
/// كل مسار جديد يُضاف هنا وحده — لا `Navigator.push` بشاشة مبنية في مكان
/// الاستدعاء، وإلا صار للشاشة الواحدة مدخلان لا يعرف أحدهما ما يعرفه الآخر
/// (وهو أصل «ستة مسارات لإرسال مزايدة» في v1).
final routerProvider = Provider<GoRouter>((ref) {
  return GoRouter(
    initialLocation: '/',
    routes: <RouteBase>[
      GoRoute(
        path: '/',
        name: Routes.seed,
        builder: (context, state) => const SeedScreen(),
      ),
      GoRoute(
        path: '/bids',
        name: Routes.myBids,
        builder: (context, state) => const MyBidsScreen(),
      ),
      GoRoute(
        // المزايدة تحت المركبة لا بجوارها: لا توجد مزايدة بلا مركبة، والمسار
        // يقول ذلك بدل أن يعتمد على مُعامل يمكن أن يغيب.
        path: '/vehicles/:vehicleId/bid',
        name: Routes.bid,
        builder: (context, state) =>
            BidScreen(vehicleId: state.pathParameters['vehicleId']!),
      ),
    ],
  );
});
