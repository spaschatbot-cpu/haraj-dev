import 'dart:convert';

import '../../domain/activity/entities/invoice.dart';
import '../../domain/activity/entities/participation.dart';
import '../../domain/activity/entities/purchase.dart';
import '../../domain/activity/repositories/activity_repository.dart';
import '../../domain/common/failure.dart';
import '../../domain/common/snapshot.dart';
import '../api/api_call.dart';
import '../api/generated/clients/auctions_api.dart';
import '../api/generated/clients/invoices_api.dart';
import '../api/generated/models/paginated_invoice_list.dart' as api;
import '../api/generated/models/paginated_participation_list.dart' as api;
import '../api/generated/models/paginated_purchase_list.dart' as api;
import '../local/cache/response_cache.dart';
import 'activity_mapper.dart';

/// مشاركاتي ومشترياتي وفواتيري: الخادم أولاً، والكاش شبكة أمان عند **صمت**
/// الخادم وحده — نفس قرار `WalletRepositoryImpl` حرفاً بحرف.
///
/// **قرار مسجَّل — الصفحة الأولى فقط.** النقاط الثلاث مرقَّمة في المخطط، وهذا
/// المستودع يقرأ الصفحة الافتراضية ولا يلاحق الصفحات. الترقيم اللانهائي تاسك
/// قائم بذاته (T712 لكشف الحركات)، وسحبه إلى هنا يخلط تاسكين ويكسر المادة ٦-٢.
/// حجم الصفحة يقرّره الخادم: مُعامل `page_size` موجود في العقد، وإرسال قيمة
/// من التطبيق يجعل لنا رأياً في شيء ليس لنا.
final class ActivityRepositoryImpl implements ActivityRepository {
  ActivityRepositoryImpl({
    required AuctionsApi auctions,
    required InvoicesApi invoices,
    required ResponseCache cache,
    DateTime Function()? clock,
  }) : _auctions = auctions,
       _invoices = invoices,
       _cache = cache,
       _clock = clock ?? DateTime.now;

  final AuctionsApi _auctions;
  final InvoicesApi _invoices;
  final ResponseCache _cache;
  final DateTime Function() _clock;

  @override
  Future<Snapshot<List<Participation>>> loadParticipations() => _load(
    cacheKey: CacheKeys.participations,
    fetch: () => _auctions.participationsList(),
    encode: (page) => page.toJson(),
    decode: api.PaginatedParticipationList.fromJson,
    toDomain: (page) =>
        page.results.map((item) => item.toDomain()).toList(growable: false),
  );

  @override
  Future<Snapshot<List<Purchase>>> loadPurchases() => _load(
    cacheKey: CacheKeys.purchases,
    fetch: () => _invoices.purchasesList(),
    encode: (page) => page.toJson(),
    decode: api.PaginatedPurchaseList.fromJson,
    toDomain: (page) =>
        page.results.map((item) => item.toDomain()).toList(growable: false),
  );

  @override
  Future<Snapshot<List<Invoice>>> loadInvoices() => _load(
    cacheKey: CacheKeys.invoices,
    fetch: () => _invoices.invoicesList(),
    encode: (page) => page.toJson(),
    decode: api.PaginatedInvoiceList.fromJson,
    toDomain: (page) =>
        page.results.map((item) => item.toDomain()).toList(growable: false),
  );

  /// مسار القراءة الواحد للقوائم الثلاث.
  ///
  /// دالة واحدة لا ثلاث نسخ: قرار «متى يُقرأ الكاش» هو القرار الحسّاس هنا،
  /// ونسخه ثلاث مرات يجعل تصحيحه في مرة واحدة ونسيانه في اثنتين.
  Future<Snapshot<List<D>>> _load<P, D>({
    required String cacheKey,
    required Future<P> Function() fetch,
    required Map<String, Object?> Function(P page) encode,
    required P Function(Map<String, Object?> json) decode,
    required List<D> Function(P page) toDomain,
  }) async {
    try {
      final page = await callApi(fetch);
      final fetchedAt = _clock().toUtc();
      await _cache.write(
        cacheKey,
        jsonEncode(encode(page)),
        fetchedAtUtc: fetchedAt,
      );
      return Snapshot.fresh(toDomain(page), at: fetchedAt);
    } on TransportFailure {
      // الخادم لم يتكلّم: نعرض آخر ما نعرف مع علامة «آخر تحديث» (H5).
      final cached = await _readCache(cacheKey, decode, toDomain);
      if (cached != null) return cached;
      // لا كاش: نرمي العطب. **لا نرجع قائمة فارغة** — «ما عندك فواتير» أسوأ
      // من «تعذّر التحديث»: قارئها يظنّ أن ما عليه سقط عنه.
      rethrow;
    }
    // `ApiFailure` تمرّ كما هي عمداً: الخادم **تكلّم** ورسالته العربية هي
    // الحقيقة. إخفاؤها خلف بيانات قديمة يكذب على المستخدم.
  }

  Future<Snapshot<List<D>>?> _readCache<P, D>(
    String cacheKey,
    P Function(Map<String, Object?> json) decode,
    List<D> Function(P page) toDomain,
  ) async {
    final document = await _cache.read(cacheKey);
    if (document == null) return null;
    try {
      return Snapshot.cached(
        toDomain(decode(document.decode())),
        storedAt: document.fetchedAtUtc,
      );
    } on Object {
      // كاش من نسخة مخطط أقدم لم يعد يُفكّ: يُعامل كغياب كاش، لا كعطب.
      return null;
    }
  }
}
