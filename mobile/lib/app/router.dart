import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../domain/wallet/entities/wallet_balance.dart';
import '../presentation/seed/seed_screen.dart';
import '../presentation/wallet/transactions_screen.dart';

/// أسماء المسارات — تُستدعى بالاسم لا بالنصّ الحر.
///
/// السبب: الإشعار يفتح الشاشة الصحيحة (معيار H6) بمطابقة اسم مسار، ومسار مكتوب
/// نصّاً في مكانين يفترق فيهما عند أول تعديل (المادة ٤-٥).
abstract final class Routes {
  static const String seed = 'seed';
  static const String walletStatement = 'walletStatement';

  /// اسم معامل الترشيح في مسار الكشف.
  ///
  /// القيمة اسم عضو `WalletBucketKind` في التطبيق، لا قيمة السلك: التحويل إلى
  /// ما يفهمه الخادم يحدث في طبقة البيانات وحدها.
  static const String bucketParameter = 'bucket';
}

/// كل مسارات التطبيق في قائمة واحدة.
///
/// مفصولة عن `routerProvider` لتُبنى في الاختبارات بموقع ابتدائي مختلف بلا
/// نسخة ثانية من تعريف المسارات — نسخة الاختبار كانت ستفترق عن نسخة الإنتاج،
/// فيمرّ اختبار على شجرة لا تُشحن.
List<RouteBase> appRoutes() => <RouteBase>[
  GoRoute(
    path: '/',
    name: Routes.seed,
    builder: (context, state) => const SeedScreen(),
  ),
  GoRoute(
    path: '/wallet/transactions',
    name: Routes.walletStatement,
    builder: (context, state) => TransactionsScreen(
      bucket: _bucketOf(state.uri.queryParameters[Routes.bucketParameter]),
    ),
  ),
];

/// يبني الموجّه. `initialLocation` معامل ليبدأ اختبار الشاشة من مسارها.
GoRouter buildRouter({String initialLocation = '/'}) =>
    GoRouter(initialLocation: initialLocation, routes: appRoutes());

/// التوجيه مُعلَن في مكان واحد (T701).
final routerProvider = Provider<GoRouter>((ref) => buildRouter());

/// دلو مجهول الاسم يُقرأ كـ«بلا ترشيح» ولا يُسقط الشاشة: المسار قد يصل من
/// إشعار أو رابط أقدم من هذا الإصدار.
WalletBucketKind? _bucketOf(String? raw) {
  if (raw == null) return null;
  for (final kind in WalletBucketKind.values) {
    if (kind.name == raw && kind != WalletBucketKind.unknown) return kind;
  }
  return null;
}
