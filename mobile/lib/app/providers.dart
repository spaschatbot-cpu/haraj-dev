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
import '../data/api/dio_factory.dart';
import '../data/api/generated/haraj_api_client.dart';
import '../data/api/interceptors/auth_interceptor.dart';
import '../data/auth/auth_repository_impl.dart';
import '../data/auth/session_refresher.dart';
import '../data/catalog/catalog_repository_impl.dart';
import '../data/local/cache/cache_database.dart';
import '../data/local/cache/drift_response_cache.dart';
import '../data/local/cache/response_cache.dart';
import '../data/local/secure/secure_token_store.dart';
import '../data/wallet/wallet_repository_impl.dart';
import '../domain/auth/repositories/auth_repository.dart';
import '../domain/auth/usecases/sign_in_with_otp.dart';
import '../domain/catalog/entities/auction_summary.dart';
import '../domain/catalog/entities/vehicle_detail.dart';
import '../domain/catalog/repositories/catalog_repository.dart';
import '../domain/catalog/usecases/load_auction_vehicles.dart';
import '../domain/catalog/usecases/load_home_auctions.dart';
import '../domain/catalog/usecases/load_vehicle.dart';
import '../domain/common/snapshot.dart';
import '../domain/wallet/repositories/wallet_repository.dart';
import '../domain/wallet/usecases/load_wallet_balance.dart';

final appConfigProvider = Provider<AppConfig>((ref) => AppConfig.fromBuild());

final secureTokenStoreProvider = Provider<SecureTokenStore>(
  (ref) => SecureTokenStore.platformDefault(),
);

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

final signInWithOtpProvider = Provider<SignInWithOtp>(
  (ref) => SignInWithOtp(ref.watch(authRepositoryProvider)),
);

final loadWalletBalanceProvider = Provider<LoadWalletBalance>(
  (ref) => LoadWalletBalance(ref.watch(walletRepositoryProvider)),
);

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
