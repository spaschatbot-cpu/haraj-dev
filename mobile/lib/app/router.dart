import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../presentation/seed/seed_screen.dart';

/// أسماء المسارات — تُستدعى بالاسم لا بالنصّ الحر.
///
/// السبب: الإشعار يفتح الشاشة الصحيحة (معيار H6) بمطابقة اسم مسار، ومسار مكتوب
/// نصّاً في مكانين يفترق فيهما عند أول تعديل (المادة ٤-٥).
abstract final class Routes {
  static const String seed = 'seed';
}

/// التوجيه مُعلَن في مكان واحد (T701).
///
/// اليوم مسار واحد فقط: شاشات المنتج هي المجموعة ب ولا تبدأ قبل تثبيت المخطط
/// (T621). كل مسار جديد يُضاف هنا وحده — لا `Navigator.push` بشاشة مبنية في
/// مكان الاستدعاء.
final routerProvider = Provider<GoRouter>((ref) {
  return GoRouter(
    initialLocation: '/',
    routes: <RouteBase>[
      GoRoute(
        path: '/',
        name: Routes.seed,
        builder: (context, state) => const SeedScreen(),
      ),
    ],
  );
});
