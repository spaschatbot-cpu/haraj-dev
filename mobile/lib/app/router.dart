import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../presentation/auth/pending_sign_in.dart';
import '../presentation/auth/session_controller.dart';
import '../presentation/auth/sign_in_screen.dart';
import '../presentation/auth/verify_code_screen.dart';
import '../presentation/catalog/auction_vehicles_screen.dart';
import '../presentation/catalog/home_screen.dart';
import '../presentation/catalog/vehicle_screen.dart';
import '../presentation/profile/change_phone_screen.dart';
import '../presentation/profile/company_profile_screen.dart';
import '../presentation/profile/profile_screen.dart';
import 'routes.dart';

export 'routes.dart' show Routes;

/// التوجيه مُعلَن في مكان واحد (T701).
///
/// أسماء المسارات ومداخلها تعيش في `routes.dart` لأن لها قارئين — جدول التوجيه
/// هنا، ومترجم حمولة الإشعار (معيار H6). كل مسار جديد يُضاف هنا وحده — لا
/// `Navigator.push` بشاشة مبنية في مكان الاستدعاء، وإلا صار للشاشة الواحدة
/// مدخلان لا يعرف الإشعار أيّهما يفتح.
///
/// **إعادة التوجيه عند سقوط الجلسة تعيش هنا وحدها.** اعتراض المصادقة يرفع
/// إشارة بعد 401 لم ينفع معه التجديد، و`SessionController` يترجمها إلى حالة،
/// وهذا الشرط ينقل المستخدم إلى الدخول أياً كانت الشاشة المفتوحة. البديل —
/// أن تعالج كل شاشة 401 بنفسها — يُنسى في شاشة، فتبقى معلَّقة تعرض دوّامة على
/// طلب لن ينجح أبداً.
final routerProvider = Provider<GoRouter>((ref) {
  // `refreshListenable` يحتاج `Listenable`؛ هذا الجسر يحوّل تغيّر المزوّد
  // إليه، ولا يحمل حالة من عنده.
  final sessionChanged = ValueNotifier<SessionState>(
    ref.read(sessionControllerProvider),
  );
  ref
    ..listen<SessionState>(
      sessionControllerProvider,
      (_, next) => sessionChanged.value = next,
    )
    ..onDispose(sessionChanged.dispose);

  return GoRouter(
    initialLocation: Routes.homePath,
    refreshListenable: sessionChanged,
    redirect: (context, state) {
      final session = ref.read(sessionControllerProvider);
      final location = state.matchedLocation;
      final onSignInFlow = location.startsWith(Routes.signInPath);

      // لحظة الإقلاع: لم يُقرأ التخزين الآمن بعد. لا قرار قبل الجواب — قرارٌ
      // هنا يعني وميض شاشة دخول أمام مستخدم مسجَّل أصلاً.
      if (session == SessionState.unknown) return null;

      final signedIn = session == SessionState.signedIn;

      if (!signedIn && location.startsWith(Routes.profilePath)) {
        return Routes.signInPath;
      }

      // شاشة الرمز بلا رمز مُرسَل تعرض «أرسلنا رمزاً إلى» بلا رقم.
      if (location == Routes.verifyCodePath &&
          ref.read(pendingSignInProvider) == null) {
        return Routes.signInPath;
      }

      if (signedIn && onSignInFlow) return Routes.homePath;

      return null;
    },
    routes: <RouteBase>[
      GoRoute(
        path: Routes.homePath,
        name: Routes.home,
        builder: (context, state) => const HomeScreen(),
        routes: <RouteBase>[
          GoRoute(
            // العنوان هو `Routes.auctionPath` بعينه، وهو ما يبنيه
            // `PushLocations` لوجهة مزاد: مدخل واحد للشاشة لا مدخلان.
            path: 'auctions/:auctionId',
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
      GoRoute(
        path: Routes.signInPath,
        name: Routes.signIn,
        builder: (context, state) => const SignInScreen(),
        routes: <RouteBase>[
          GoRoute(
            path: 'code',
            name: Routes.verifyCode,
            builder: (context, state) => const VerifyCodeScreen(),
          ),
        ],
      ),
      GoRoute(
        path: Routes.profilePath,
        name: Routes.profile,
        builder: (context, state) => const ProfileScreen(),
        routes: <RouteBase>[
          GoRoute(
            path: 'company',
            name: Routes.companyProfile,
            builder: (context, state) => const CompanyProfileScreen(),
          ),
          GoRoute(
            path: 'phone',
            name: Routes.changePhone,
            builder: (context, state) => const ChangePhoneScreen(),
          ),
        ],
      ),
    ],
  );
});
