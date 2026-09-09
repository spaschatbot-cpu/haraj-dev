import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../domain/catalog/entities/auction_phase.dart';
import '../domain/wallet/entities/wallet_balance.dart';
import '../presentation/activity/my_activity_screen.dart';
import '../presentation/auth/pending_sign_in.dart';
import '../presentation/auth/session_controller.dart';
import '../presentation/auth/sign_in_screen.dart';
import '../presentation/auth/verify_code_screen.dart';
import '../presentation/bidding/bid_screen.dart';
import '../presentation/bidding/my_bids_screen.dart';
import '../presentation/catalog/auction_vehicles_screen.dart';
import '../presentation/catalog/favourites_screen.dart';
import '../presentation/catalog/home_screen.dart';
import '../presentation/profile/change_phone_screen.dart';
import '../presentation/profile/company_profile_screen.dart';
import '../presentation/profile/profile_screen.dart';
import '../presentation/shell/home_shell.dart';
import '../presentation/wallet/top_up_screen.dart';
import '../presentation/wallet/transactions_screen.dart';
import '../presentation/wallet/wallet_screen.dart';
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
/// شجرة المسارات — تُبنى مرة واحدة ويقرؤها الإنتاج والاختبار معاً.
///
/// مفصولة عن `routerProvider` لتُبنى في الاختبارات بموقع ابتدائي مختلف بلا
/// نسخة ثانية من تعريف المسارات — نسخة الاختبار كانت ستفترق عن نسخة الإنتاج،
/// فيمرّ اختبار على شجرة لا تُشحن.
List<RouteBase> appRoutes() => <RouteBase>[
  // الأقسام الخمسة تحت قشرةٍ واحدة تحمل الشريط السفليّ.
  //
  // **`StatefulShellRoute` لا `ShellRoute`:** لكل فرعٍ مكدّسه الخاص، فمن فتح
  // مركبةً من المفضلة ثم ذهب إلى المحفظة وعاد وجدها كما تركها. مع `ShellRoute`
  // كان المكدّس واحداً، فيعود إلى رأس القسم في كل تنقّل.
  //
  // وترتيب الفروع هو ترتيب `HomeSection.values` — الشريط يختار بالفهرس.
  StatefulShellRoute.indexedStack(
    builder: (context, state, navigationShell) =>
        HomeShell(navigationShell: navigationShell),
    branches: <StatefulShellBranch>[
      // ١ — الرئيسية، وتحتها المزاد والمركبة والمزايدة.
      //
      // المركبة **داخل** القسم لا فوق القشرة: الشريط يبقى ظاهراً، فمن فتح
      // مركبةً يستطيع الذهاب إلى محفظته ليشحن ثم يعود إليها. رفعُها فوق
      // القشرة كان يحبسه في الشاشة حتى يرجع.
      StatefulShellBranch(
        routes: <RouteBase>[
          GoRoute(
            path: Routes.homePath,
            name: Routes.home,
            // التبويب يُقرأ من العنوان في كل بناء، لا يُحفظ في حالة الشاشة:
            // عنوانٌ واحد يعطي شاشةً واحدة، سواء وصل من ضغطة تبويب أو من رابط
            // مشارَك أو من إشعار أو من إعادة فتح التطبيق.
            builder: (context, state) => HomeScreen(
              phase: AuctionPhase.fromSlug(
                state.uri.queryParameters[Routes.phaseQueryParameter],
              ),
            ),
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
                // **لا صفحةَ مركبة فوقها** — حُذفت بطلب المالك في ٩ سبتمبر
                // ٢٠٢٦، وحلّ محلَّها صندوقُ المزايدة الذي يفتحه الكرت.
                // والمسارُ بقي كما كان (`vehicles/:id/bid`): الإشعارُ
                // والرابطُ المشارَك يفتحانه به (معيار H6)، وتغييرُه يكسر ما
                // أُرسل قبل اليوم. فصار فرعاً مباشراً بنفس العنوان.
                path: 'vehicles/:vehicleId/bid',
                name: Routes.bid,
                builder: (context, state) =>
                    BidScreen(vehicleId: state.pathParameters['vehicleId']!),
              ),
            ],
          ),
        ],
      ),

      // ٢ — مشاركاتي: مشاركاتي ومشترياتي وفواتيري، ومزايداتي تحتها.
      //
      // وموضعُها الثاني: بُدِّلت بالمحفظة بطلب المالك في ٩ سبتمبر ٢٠٢٦،
      // وترتيبُ الفروع هنا يتبع ترتيبَ `HomeSection` دائماً — الشريطُ
      // يختار بالفهرس، فبديلٌ في أحدهما بلا الآخر يفتح المحفظة عند ضغط
      // «مشاركاتي».
      //
      // تبويب واحد في العنوان، لا ثلاثة مسارات: الشاشة واحدة بحق (الثلاث
      // قوائم إجابة واحدة)، والتبويب حالةُ عرض داخلها. لكنه في العنوان لأن
      // الإشعار يجب أن يفتح التبويب الصحيح مباشرةً (H6).
      StatefulShellBranch(
        routes: <RouteBase>[
          GoRoute(
            path: Routes.myActivityPath,
            name: Routes.myActivity,
            builder: (context, state) => MyActivityScreen(
              initialTab: MyActivityTab.fromSlug(
                state.uri.queryParameters[Routes.tabQueryParameter],
              ),
            ),
          ),
          GoRoute(
            path: Routes.bidsPath,
            name: Routes.myBids,
            builder: (context, state) => const MyBidsScreen(),
          ),
        ],
      ),

      // ٣ — المفضلة.
      StatefulShellBranch(
        routes: <RouteBase>[
          GoRoute(
            path: Routes.favouritesPath,
            name: Routes.favourites,
            builder: (context, state) => const FavouritesScreen(),
          ),
        ],
      ),

      // ٤ — محفظتي، وتحتها الشحن والكشف.
      StatefulShellBranch(
        routes: <RouteBase>[
          GoRoute(
            path: Routes.walletPath,
            name: Routes.wallet,
            builder: (context, state) => const WalletScreen(),
            routes: <RouteBase>[
              GoRoute(
                path: 'topup',
                name: Routes.walletTopUp,
                builder: (context, state) => const TopUpScreen(),
              ),
              GoRoute(
                path: 'transactions',
                name: Routes.walletStatement,
                builder: (context, state) => TransactionsScreen(
                  bucket: _bucketOf(
                    state.uri.queryParameters[Routes.bucketParameter],
                  ),
                ),
              ),
            ],
          ),
        ],
      ),

      // ٥ — حسابي، وتحته ملفّ الشركة وتغيير الجوال.
      StatefulShellBranch(
        routes: <RouteBase>[
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
      ),
    ],
  ),

  // الدخول **خارج القشرة**: شريطٌ سفليّ على شاشة تسجيل الدخول يعرض أربعة
  // أقسام لا يفتحها من ليس داخلاً، فيضغطها فيُعاد إلى حيث هو.
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
];

/// المسارات التي لا معنى لها بلا جلسة — **قائمة واحدة بجوار الجدول**.
///
/// أنماطٌ لا عناوين: `/vehicles/:vehicleId/bid` محمي و`/vehicles/:vehicleId`
/// مفتوح للجميع، وبادئةٌ نصّية على العنوان تحرسهما معاً أو تترك أحدهما.
/// و«بجوار الجدول» ليست ترتيباً جمالياً: شرطٌ يذكر مساراً واحداً بالاسم ينسى
/// كل مسار يُضاف بعده، وهو ما حدث — كانت الحراسة على `/profile` وحده بينما
/// المحفظة والمزايدات وحسابي مفتوحة، فيبقى صاحب الجلسة الساقطة على شاشته
/// يشاهد فشل شبكة بلا سبب ولا مخرج.
const Set<String> authenticatedRoutes = <String>{
  Routes.profilePath,
  Routes.walletPath,
  Routes.bidsPath,
  Routes.bidPath,
  Routes.myActivityPath,
  Routes.favouritesPath,
};

/// هل هذا النمط — لا العنوان — تحت الحراسة؟
///
/// المقارنة ببادئة النمط لا بمساواته: `/profile/company` و`/wallet/topup`
/// أبناءُ محميّين، وسردهما واحداً واحداً يعني نسيان الثالث.
bool requiresSession(String? matchedRoutePath) =>
    matchedRoutePath != null &&
    authenticatedRoutes.any(matchedRoutePath.startsWith);

/// يبني موجّهاً بلا إعادة توجيه — لاختبار شاشةٍ من مسارها مباشرةً.
///
/// إعادة التوجيه تحتاج `ref`، وهي في `routerProvider` وحده: اختبار شاشة واحدة
/// لا جلسة له ولا يعني سقوطَها في شيء.
GoRouter buildRouter({String initialLocation = '/'}) =>
    GoRouter(initialLocation: initialLocation, routes: appRoutes());

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

      // `fullPath` هو النمط الذي طابق (`/vehicles/:vehicleId/bid`) لا العنوان
      // المطابِق (`/vehicles/340/bid`)، فالحراسة تُسأل بلغة جدول المسارات.
      if (!signedIn && requiresSession(state.fullPath)) {
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
    routes: appRoutes(),
  );
});

/// دلو مجهول الاسم يُقرأ كـ«بلا ترشيح» ولا يُسقط الشاشة: المسار قد يصل من
/// إشعار أو رابط أقدم من هذا الإصدار.
WalletBucketKind? _bucketOf(String? raw) {
  if (raw == null) return null;
  for (final kind in WalletBucketKind.values) {
    if (kind.name == raw && kind != WalletBucketKind.unknown) return kind;
  }
  return null;
}
