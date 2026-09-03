import 'package:flutter/widgets.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../presentation/catalog/auction_vehicles_screen.dart';
import '../presentation/catalog/home_screen.dart';
import '../presentation/catalog/vehicle_screen.dart';

/// أسماء المسارات ومداخلها — تُستدعى بالاسم لا بالنصّ الحر.
///
/// السبب: الإشعار يفتح الشاشة الصحيحة (معيار H6) بمطابقة اسم مسار، ومسار مكتوب
/// نصّاً في مكانين يفترق فيهما عند أول تعديل (المادة ٤-٥). ولهذا يعيش بناء
/// العنوان هنا أيضاً، لا في كل شاشة تنقل إلى غيرها.
abstract final class Routes {
  static const String home = 'home';
  static const String auctionVehicles = 'auction-vehicles';
  static const String vehicle = 'vehicle';

  static void goToAuctionVehicles(BuildContext context, String auctionId) =>
      GoRouter.of(context).goNamed(
        auctionVehicles,
        pathParameters: <String, String>{'auctionId': auctionId},
      );

  static void goToVehicle(BuildContext context, String vehicleId) =>
      GoRouter.of(context).goNamed(
        vehicle,
        pathParameters: <String, String>{'vehicleId': vehicleId},
      );
}

/// التوجيه مُعلَن في مكان واحد (T701).
///
/// كل مسار جديد يُضاف هنا وحده — لا `Navigator.push` بشاشة مبنية في مكان
/// الاستدعاء، وإلا صار للشاشة الواحدة مدخلان لا يعرف الإشعار أيّهما يفتح.
final routerProvider = Provider<GoRouter>((ref) {
  return GoRouter(
    initialLocation: '/',
    routes: <RouteBase>[
      GoRoute(
        path: '/',
        name: Routes.home,
        builder: (context, state) => const HomeScreen(),
        routes: <RouteBase>[
          GoRoute(
            path: 'auctions/:auctionId/vehicles',
            name: Routes.auctionVehicles,
            builder: (context, state) => AuctionVehiclesScreen(
              auctionId: state.pathParameters['auctionId']!,
            ),
          ),
          GoRoute(
            path: 'vehicles/:vehicleId',
            name: Routes.vehicle,
            builder: (context, state) =>
                VehicleScreen(vehicleId: state.pathParameters['vehicleId']!),
          ),
        ],
      ),
    ],
  );
});
