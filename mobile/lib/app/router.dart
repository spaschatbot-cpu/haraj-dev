import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../presentation/activity/my_activity_screen.dart';
import '../presentation/seed/seed_screen.dart';

/// أسماء المسارات — تُستدعى بالاسم لا بالنصّ الحر.
///
/// السبب: الإشعار يفتح الشاشة الصحيحة (معيار H6) بمطابقة اسم مسار، ومسار مكتوب
/// نصّاً في مكانين يفترق فيهما عند أول تعديل (المادة ٤-٥).
abstract final class Routes {
  static const String seed = 'seed';

  /// حسابي: مشاركاتي ومشترياتي وفواتيري. التبويب في `?tab=`.
  static const String myActivity = 'my-activity';

  /// اسم مُعامل التبويب — مكتوب مرة واحدة لأن الإشعار يبنيه والشاشة تقرؤه.
  static const String tabQueryParameter = 'tab';
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
      // تبويب واحد في العنوان، لا ثلاثة مسارات: الشاشة واحدة بحق (الثلاث
      // قوائم إجابة واحدة)، والتبويب حالةُ عرض داخلها. لكنه في العنوان لأن
      // الإشعار يجب أن يفتح التبويب الصحيح مباشرةً (H6).
      GoRoute(
        path: '/my-activity',
        name: Routes.myActivity,
        builder: (context, state) => MyActivityScreen(
          initialTab: MyActivityTab.fromSlug(
            state.uri.queryParameters[Routes.tabQueryParameter],
          ),
        ),
      ),
    ],
  );
});
