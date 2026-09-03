import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../presentation/seed/seed_screen.dart';
import 'routes.dart';

export 'routes.dart' show Routes;

/// التوجيه مُعلَن في مكان واحد (T701).
///
/// اليوم مسار واحد فقط: شاشات المنتج هي المجموعة ب ولا تبدأ قبل تثبيت المخطط
/// (T621). كل مسار جديد يُضاف هنا وحده — لا `Navigator.push` بشاشة مبنية في
/// مكان الاستدعاء — وبمسارٍ من `Routes` لا بنصّ حر، فما يفتحه الإشعار وما يفتحه
/// الزرّ عنوان واحد (معيار H6، انظر `routes.dart`).
final routerProvider = Provider<GoRouter>((ref) {
  return GoRouter(
    initialLocation: Routes.homePath,
    routes: <RouteBase>[
      GoRoute(
        path: Routes.homePath,
        name: Routes.seed,
        builder: (context, state) => const SeedScreen(),
      ),
    ],
  );
});
