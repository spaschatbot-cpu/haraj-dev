import 'package:dio/dio.dart';
import 'package:haraj_mobile/data/api/generated/clients/wallet_api.dart';
import 'package:haraj_mobile/data/api/generated/models/paginated_ledger_entry_list.dart';
import 'package:haraj_mobile/data/api/generated/models/refund_request.dart';
import 'package:haraj_mobile/data/api/generated/models/refund_request_input.dart';
import 'package:haraj_mobile/data/api/generated/models/top_up_intent.dart';
import 'package:haraj_mobile/data/api/generated/models/top_up_intent_request.dart';
import 'package:haraj_mobile/data/api/generated/models/wallet.dart';
import 'package:haraj_mobile/data/api/generated/models/wallet_bucket_kind.dart';

/// عميل المحفظة المولَّد، مزيَّفاً.
///
/// واحد لكل اختبارات المحفظة عمداً: نسخة لكل ملف تعني ثلاث نسخ تفترق، وأول
/// تغيير في المخطط يُصلَح في واحدة وتمرّ الأخريان على عقد قديم.
///
/// يسجّل ما سُئل عنه (`askedPages`، `askedBuckets`) لأن بعض القواعد لا تُثبت
/// إلا بما **أُرسل**: أن الترشيح ذهب إلى الخادم، وأن حالة الشحن قُرئت من نقطة
/// الخادم لا من رابط العودة.
final class FakeWalletApi implements WalletApi {
  FakeWalletApi({
    this.wallet,
    this.pages = const <int, PaginatedLedgerEntryList>{},
    this.topUpIntent,
    this.topUpStatuses = const <TopUpIntent>[],
  });

  final Wallet? wallet;
  final Map<int, PaginatedLedgerEntryList> pages;

  /// ما يرجع عند إنشاء نيّة شحن.
  final TopUpIntent? topUpIntent;

  /// ما يرجع عند سؤال الخادم عن الحالة، مرة بعد مرة. الأخيرة تتكرّر.
  final List<TopUpIntent> topUpStatuses;

  /// عطب يُرمى بدل الاستجابة — يُضبط لمحاكاة انقطاع أو ردّ خطأ.
  DioException? failWith;

  final List<int> askedPages = <int>[];
  final List<WalletBucketKind?> askedBuckets = <WalletBucketKind?>[];
  final List<String> askedReferences = <String>[];
  int topUpCreateCount = 0;

  int _statusReads = 0;

  @override
  Future<Wallet> walletRetrieve() async {
    _throwIfFailing();
    return wallet!;
  }

  @override
  Future<PaginatedLedgerEntryList> walletTransactionsList({
    int? page,
    int? pageSize,
    WalletBucketKind? bucket,
  }) async {
    askedPages.add(page ?? 1);
    askedBuckets.add(bucket);
    _throwIfFailing();
    return pages[page ?? 1]!;
  }

  @override
  Future<TopUpIntent> walletTopUpIntentCreate({
    required TopUpIntentRequest body,
  }) async {
    topUpCreateCount++;
    _throwIfFailing();
    return topUpIntent!;
  }

  @override
  Future<TopUpIntent> walletTopUpIntentRetrieve({
    required String reference,
  }) async {
    askedReferences.add(reference);
    _throwIfFailing();
    final index = _statusReads < topUpStatuses.length
        ? _statusReads
        : topUpStatuses.length - 1;
    _statusReads++;
    return topUpStatuses[index];
  }

  @override
  Future<RefundRequest> walletRefundRequestCreate({
    required RefundRequestInput body,
  }) => throw UnimplementedError();

  void _throwIfFailing() {
    final failure = failWith;
    if (failure != null) throw failure;
  }
}
