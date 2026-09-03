/// جذر التركيب (composition root).
///
/// **هذا الملف وحده** يعرف الطبقتين معاً: يستورد `data` ليبني التنفيذ، ويصدّر
/// أنواع `domain` فقط. طبقة `presentation` تقرأ من هنا فتحصل على `AuthRepository`
/// لا `AuthRepositoryImpl`، ولا تستورد `data` أبداً — القاعدة المعمارية في خطة
/// الفريق §5، ويفرضها `test/architecture/layering_test.dart` نصّياً.
library;

import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../core/environment.dart';
import '../data/activity/activity_repository_impl.dart';
import '../data/api/dio_factory.dart';
import '../data/api/generated/haraj_api_client.dart';
import '../data/api/interceptors/auth_interceptor.dart';
import '../data/auth/auth_repository_impl.dart';
import '../data/auth/session_refresher.dart';
import '../data/bidding/bidding_repository_impl.dart';
import '../data/bidding/sse_channel.dart';
import '../data/catalog/catalog_repository_impl.dart';
import '../data/local/cache/cache_database.dart';
import '../data/local/cache/drift_response_cache.dart';
import '../data/local/cache/response_cache.dart';
import '../data/local/secure/secure_token_store.dart';
import '../data/notifications/device_registry_impl.dart';
import '../data/notifications/unconfigured_push_service.dart';
import '../data/profile/profile_repository_impl.dart';
import '../data/wallet/url_checkout_launcher.dart';
import '../data/wallet/wallet_repository_impl.dart';
import '../domain/activity/repositories/activity_repository.dart';
import '../domain/activity/usecases/load_my_invoices.dart';
import '../domain/activity/usecases/load_my_participations.dart';
import '../domain/activity/usecases/load_my_purchases.dart';
import '../domain/auth/repositories/auth_repository.dart';
import '../domain/auth/session_signal.dart';
import '../domain/auth/usecases/change_phone_number.dart';
import '../domain/auth/usecases/sign_in_with_code.dart';
import '../domain/auth/usecases/sign_out.dart';
import '../domain/bidding/repositories/bidding_repository.dart';
import '../domain/bidding/usecases/load_my_bids.dart';
import '../domain/bidding/usecases/place_bid.dart';
import '../domain/bidding/usecases/watch_live_bids.dart';
import '../domain/bidding/usecases/withdraw_bid.dart';
import '../domain/catalog/entities/auction_summary.dart';
import '../domain/catalog/entities/vehicle_detail.dart';
import '../domain/catalog/repositories/catalog_repository.dart';
import '../domain/catalog/usecases/load_auction_vehicles.dart';
import '../domain/catalog/usecases/load_home_auctions.dart';
import '../domain/catalog/usecases/load_vehicle.dart';
import '../domain/common/snapshot.dart';
import '../domain/notifications/repositories/device_registry.dart';
import '../domain/notifications/repositories/push_service.dart';
import '../domain/notifications/usecases/forget_this_device.dart';
import '../domain/notifications/usecases/register_this_device.dart';
import '../domain/notifications/usecases/resolve_push_destination.dart';
import '../domain/profile/repositories/profile_repository.dart';
import '../domain/profile/usecases/manage_profile.dart';
import '../domain/wallet/gateways/checkout_launcher.dart';
import '../domain/wallet/repositories/wallet_repository.dart';
import '../domain/wallet/usecases/load_wallet_balance.dart';
import '../domain/wallet/usecases/load_wallet_transactions.dart';
import '../domain/wallet/usecases/read_top_up_status.dart';
import '../domain/wallet/usecases/start_card_top_up.dart';
import '../l10n/generated/app_localizations.dart';
import '../presentation/common/push_banner.dart';
import 'haraj_app.dart';
import 'push_coordinator.dart';
import 'router.dart';
import 'routes.dart';

final appConfigProvider = Provider<AppConfig>((ref) => AppConfig.fromBuild());

final secureTokenStoreProvider = Provider<SecureTokenStore>(
  (ref) => SecureTokenStore.platformDefault(),
);

/// إشارة سقوط الجلسة: يرفعها اعتراض المصادقة، ويسمعها الموجّه.
///
/// تُبنى هنا لأن الطرفين لا يعرف أحدهما الآخر، وهذا الملف وحده يعرفهما معاً.
final sessionSignalProvider = Provider<SessionSignal>((ref) {
  final signal = SessionSignal();
  ref.onDispose(signal.dispose);
  return signal;
});

final cacheDatabaseProvider = Provider<CacheDatabase>((ref) {
  final database = CacheDatabase.onDevice();
  ref.onDispose(database.close);
  return database;
});

final responseCacheProvider = Provider<ResponseCache>(
  (ref) => DriftResponseCache(ref.watch(cacheDatabaseProvider)),
);

/// عميل HTTP بلا اعتراض المصادقة.
///
/// يخدم غرضين لا ثالث لهما: تجديد الرمز (لئلا يجدّد التجديدُ نفسَه في حلقة)،
/// وإعادة إرسال الطلب بعد تجديد ناجح.
final _plainDioProvider = Provider<Dio>(
  (ref) => DioFactory.build(baseUrl: ref.watch(appConfigProvider).apiBaseUrl),
);

final _sessionRefresherProvider = Provider<SessionRefresher>(
  (ref) => SessionRefresher(
    api: HarajApiClient(ref.watch(_plainDioProvider)).auth,
    tokens: ref.watch(secureTokenStoreProvider),
  ),
);

final _authenticatedDioProvider = Provider<Dio>((ref) {
  return DioFactory.build(
    baseUrl: ref.watch(appConfigProvider).apiBaseUrl,
    interceptors: [
      AuthInterceptor(
        tokens: ref.watch(secureTokenStoreProvider),
        refreshSession: ref.watch(_sessionRefresherProvider).refresh,
        retryClient: ref.watch(_plainDioProvider),
        onSessionLost: ref.watch(sessionSignalProvider).reportLost,
      ),
    ],
  );
});

/// العميل المولَّد من المخطط — لا يُنشأ عميل HTTP آخر في أي مكان.
final apiClientProvider = Provider<HarajApiClient>(
  (ref) => HarajApiClient(ref.watch(_authenticatedDioProvider)),
);

final authRepositoryProvider = Provider<AuthRepository>(
  (ref) => AuthRepositoryImpl(
    api: ref.watch(apiClientProvider).auth,
    tokens: ref.watch(secureTokenStoreProvider),
    cache: ref.watch(responseCacheProvider),
  ),
);

final profileRepositoryProvider = Provider<ProfileRepository>(
  (ref) => ProfileRepositoryImpl(
    api: ref.watch(apiClientProvider).profile,
    cache: ref.watch(responseCacheProvider),
  ),
);

final walletRepositoryProvider = Provider<WalletRepository>(
  (ref) => WalletRepositoryImpl(
    api: ref.watch(apiClientProvider).wallet,
    cache: ref.watch(responseCacheProvider),
  ),
);

final catalogRepositoryProvider = Provider<CatalogRepository>(
  (ref) => CatalogRepositoryImpl(
    auctions: ref.watch(apiClientProvider).auctions,
    vehicles: ref.watch(apiClientProvider).vehicles,
    cache: ref.watch(responseCacheProvider),
  ),
);

final activityRepositoryProvider = Provider<ActivityRepository>(
  (ref) => ActivityRepositoryImpl(
    auctions: ref.watch(apiClientProvider).auctions,
    invoices: ref.watch(apiClientProvider).invoices,
    cache: ref.watch(responseCacheProvider),
  ),
);

/// خدمة الإشعارات على الجهاز (T716).
///
/// القيمة الافتراضية «بلا إعداد» عمداً: `main.dart` يستبدلها بتنفيذ Firebase
/// بعد نجاح التهيئة. البناء الذي لا يجد إعداد المزوّد — وهو كل بناء محلي، لأن
/// المادة ٥-٣ تُبقي الإعداد خارج المستودع — يعمل بلا إشعارات ولا ينهار.
final pushServiceProvider = Provider<PushService>(
  (ref) => const UnconfiguredPushService(),
);

final deviceRegistryProvider = Provider<DeviceRegistry>(
  (ref) => DeviceRegistryImpl(api: ref.watch(apiClientProvider).devices),
);

final registerThisDeviceProvider = Provider<RegisterThisDevice>(
  (ref) => RegisterThisDevice(
    push: ref.watch(pushServiceProvider),
    registry: ref.watch(deviceRegistryProvider),
    auth: ref.watch(authRepositoryProvider),
  ),
);

final forgetThisDeviceProvider = Provider<ForgetThisDevice>(
  (ref) => ForgetThisDevice(
    push: ref.watch(pushServiceProvider),
    registry: ref.watch(deviceRegistryProvider),
  ),
);

final signInWithCodeProvider = Provider<SignInWithCode>(
  (ref) => SignInWithCode(ref.watch(authRepositoryProvider)),
);

final changePhoneNumberProvider = Provider<ChangePhoneNumber>(
  (ref) => ChangePhoneNumber(ref.watch(authRepositoryProvider)),
);

final manageProfileProvider = Provider<ManageProfile>(
  (ref) => ManageProfile(ref.watch(profileRepositoryProvider)),
);

/// الخروج يمرّ من هنا وحده.
///
/// `AuthRepository.signOut` وحده يمحو الجلسة ويترك الجهاز مسجَّلاً على من خرج.
/// الشاشات تستدعي هذا لا ذاك.
final signOutProvider = Provider<SignOut>(
  (ref) => SignOut(
    auth: ref.watch(authRepositoryProvider),
    forgetDevice: ref.watch(forgetThisDeviceProvider),
  ),
);

/// قناة البثّ الحي فوق عميل dio المصادَق نفسه.
///
/// نفس العميل عمداً: الرمز يُلحق باعتراض المصادقة القائم، فلا يعرف مكانٌ ثانٍ
/// في التطبيق كيف يُصادَق طلب (المادة ٤-٥).
final _liveChannelProvider = Provider<SseChannel>(
  (ref) => DioSseChannel(ref.watch(_authenticatedDioProvider)),
);

final biddingRepositoryProvider = Provider<BiddingRepository>(
  (ref) => BiddingRepositoryImpl(
    api: ref.watch(apiClientProvider).bids,
    cache: ref.watch(responseCacheProvider),
    live: ref.watch(_liveChannelProvider),
  ),
);

final loadWalletBalanceProvider = Provider<LoadWalletBalance>(
  (ref) => LoadWalletBalance(ref.watch(walletRepositoryProvider)),
);

/// وصل الإشعارات بالتنقّل (T716).
///
/// لا يبدأ من داخل شجرة الويدجت: `main.dart` يشغّله بعد `runApp`. لو بدأ في
/// `initState` لبدأ في كل اختبار widget يبني التطبيق، فقرأ التخزين الآمن
/// وتحدّث إلى الشبكة من داخل اختبار لا يعني الإشعارات في شيء.
final pushCoordinatorProvider = Provider<PushCoordinator>((ref) {
  final coordinator = PushCoordinator(
    push: ref.watch(pushServiceProvider),
    register: ref.watch(registerThisDeviceProvider),
    navigate: (location) => ref.read(routerProvider).go(location),
    onForeground: (notification) {
      final messenger = HarajApp.messengerKey.currentState;
      final context = HarajApp.messengerKey.currentContext;
      if (messenger == null || context == null) return;

      showPushBanner(
        messenger,
        notification: notification,
        l10n: AppLocalizations.of(context),
        environment: ref.read(appConfigProvider).environment,
        onOpen: () => ref
            .read(routerProvider)
            .go(PushLocations.of(ResolvePushDestination.call(notification))),
      );
    },
  );
  ref.onDispose(coordinator.dispose);
  return coordinator;
});

final loadHomeAuctionsProvider = Provider<LoadHomeAuctions>(
  (ref) => LoadHomeAuctions(ref.watch(catalogRepositoryProvider)),
);

final loadAuctionVehiclesProvider = Provider<LoadAuctionVehicles>(
  (ref) => LoadAuctionVehicles(ref.watch(catalogRepositoryProvider)),
);

final loadVehicleProvider = Provider<LoadVehicle>(
  (ref) => LoadVehicle(ref.watch(catalogRepositoryProvider)),
);

/// **لا إعادة محاولة صامتة.**
///
/// Riverpod يعيد المحاولة تلقائياً عند الفشل بتباعدٍ متزايد. هنا يضرّ: خطأٌ ردّ
/// به الخادم (403، 404) لن يتغيّر بإعادة السؤال، فتصير الشاشة تسأل عشر مرات عن
/// جوابٍ معروف؛ ورسالة الخطأ تومض وتختفي فلا يقرؤها العميل ولا يفهم لماذا.
/// إعادة المحاولة قرارُ من يقرأ الرسالة، وله زرّ في `FailureView`.
Duration? _noSilentRetry(int attempt, Object error) => null;

/// حالة الرئيسية (T707) — تُبطَل بـ`ref.invalidate` عند إعادة المحاولة.
final homeAuctionsProvider = FutureProvider<Snapshot<HomeAuctions>>(
  (ref) => ref.watch(loadHomeAuctionsProvider)(),
  retry: _noSilentRetry,
);

/// حالة صفحة مركبة (T709)، بمعرّفها.
final vehicleProvider = FutureProvider.family<Snapshot<VehicleDetail>, String>(
  (ref, vehicleId) => ref.watch(loadVehicleProvider)(vehicleId),
  retry: _noSilentRetry,
);

/// «الآن» كدالّة، لا كقراءة مباشرة لـ`DateTime.now()` في الشاشة.
///
/// عدّادٌ تنازلي يقرأ الساعة بنفسه لا يُختبَر: كل تشغيل يعطي نتيجة أخرى.
/// وباستبدال هذا المزوّد يصير «كم بقي؟» سؤالاً له جواب ثابت في الاختبار.
final nowProvider = Provider<DateTime Function()>((ref) => DateTime.now);

/// نبض العدّاد التنازلي — `null` يعني «لا نبض».
///
/// **لماذا مزوَّد لا ثابت:** مؤقّت دوري يجعل `pumpAndSettle` لا تستقرّ أبداً،
/// فيسقط كل اختبار شاشةٍ تحمل عدّاداً بمهلةٍ لا يفهم قارئها سببها. الاختبار
/// يستبدله بـ`null` مع وقتٍ ثابت من `nowProvider`.
final countdownTickProvider = Provider<Duration?>(
  (ref) => const Duration(seconds: 1),
);

final loadMyParticipationsProvider = Provider<LoadMyParticipations>(
  (ref) => LoadMyParticipations(ref.watch(activityRepositoryProvider)),
);

final loadMyPurchasesProvider = Provider<LoadMyPurchases>(
  (ref) => LoadMyPurchases(ref.watch(activityRepositoryProvider)),
);

final loadMyInvoicesProvider = Provider<LoadMyInvoices>(
  (ref) => LoadMyInvoices(ref.watch(activityRepositoryProvider)),
);

final loadWalletTransactionsProvider = Provider<LoadWalletTransactions>(
  (ref) => LoadWalletTransactions(ref.watch(walletRepositoryProvider)),
);

final checkoutLauncherProvider = Provider<CheckoutLauncher>(
  (ref) => const UrlCheckoutLauncher(),
);

final startCardTopUpProvider = Provider<StartCardTopUp>(
  (ref) => StartCardTopUp(
    repository: ref.watch(walletRepositoryProvider),
    launcher: ref.watch(checkoutLauncherProvider),
  ),
);

final readTopUpStatusProvider = Provider<ReadTopUpStatus>(
  (ref) => ReadTopUpStatus(ref.watch(walletRepositoryProvider)),
);

final placeBidProvider = Provider<PlaceBid>(
  (ref) => PlaceBid(ref.watch(biddingRepositoryProvider)),
);

final withdrawBidProvider = Provider<WithdrawBid>(
  (ref) => WithdrawBid(ref.watch(biddingRepositoryProvider)),
);

final loadMyBidsProvider = Provider<LoadMyBids>(
  (ref) => LoadMyBids(ref.watch(biddingRepositoryProvider)),
);

final watchLiveBidsProvider = Provider<WatchLiveBids>(
  (ref) => WatchLiveBids(ref.watch(biddingRepositoryProvider)),
);
