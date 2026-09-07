import 'package:flutter_test/flutter_test.dart';
import 'package:haraj_mobile/data/api/generated/models/bid.dart';
import 'package:haraj_mobile/data/api/generated/models/bid_status.dart';
import 'package:haraj_mobile/data/api/generated/models/paginated_bid_list.dart';
import 'package:haraj_mobile/data/bidding/bidding_repository_impl.dart';
import 'package:haraj_mobile/data/local/cache/response_cache.dart';
import 'package:haraj_mobile/domain/bidding/entities/bid_outcome.dart';
import 'package:haraj_mobile/domain/bidding/entities/placed_bid.dart';
import 'package:haraj_mobile/domain/common/failure.dart';
import 'package:haraj_mobile/domain/common/snapshot.dart';

import '../support/fake_bids_api.dart';
import '../support/fake_sse_channel.dart';
import '../support/memory_response_cache.dart';
import '../support/server_refusal_reasons.dart';

/// T710 — المزايدة في طبقة البيانات.
///
/// المحور: **التطبيق لا يقرّر**. كل اختبار هنا يثبت إمّا أن ما خرج من التطبيق
/// هو ما كتبه المستخدم بلا تعديل، أو أن ما دخل عليه من الخادم يصل الشاشة كما
/// هو — بلا رسالة بديلة وبلا رقم مخترَع.
void main() {
  final fetchedAt = DateTime.utc(2026, 9, 1, 8);

  BiddingRepositoryImpl build(FakeBidsApi api, {ResponseCache? cache}) =>
      BiddingRepositoryImpl(
        api: api,
        cache: cache ?? MemoryResponseCache(),
        live: FakeSseChannel(const <Stream<String>>[]),
        clock: () => fetchedAt,
      );

  group('وضع مزايدة', () {
    test('المبلغ يصل الخادم نصّاً كما كُتب — بلا تطبيع ولا تقريب', () async {
      final api = FakeBidsApi(bid: serverBid(amount: '12500.10'));
      final repository = build(api);

      final outcome = await repository.placeBid(
        vehicleId: 'V-1',
        amount: '12500.10',
      );

      expect(api.submissions.single.amount, '12500.10');
      expect((outcome as BidAccepted).bid.money.amount, '12500.10');
    });

    test('المحاولة الأولى لا تحمل تأكيد الخفض أبداً', () async {
      // لو استنتج التطبيق «هذا يبدو أقل، أضف العلم» لمرّ الخفض من المحاولة
      // الأولى، وسقط الحارس الذي وُجد F3 من أجله بلا أن يسقط اختبار واحد.
      final api = FakeBidsApi(bid: serverBid());
      final repository = build(api);

      await repository.placeBid(vehicleId: 'V-1', amount: '1.00');

      expect(api.submissions.single.confirmLower, isFalse);
    });

    test('الخفض يرجع طلب تأكيد بالمبلغين كما أرسلهما الخادم', () async {
      final api = FakeBidsApi(bid: serverBid())
        ..failWith = refusal(
          code: 'lower_needs_confirm',
          message: 'المبلغ أقل من مزايدتك الحالية. أكّد الخفض إن كنت متأكداً.',
          detail: const <String, Object?>{
            'standing': '12600.00',
            'requested': '9000.00',
            'bid': 41,
          },
        );
      final repository = build(api);

      final outcome = await repository.placeBid(
        vehicleId: 'V-1',
        amount: '9000.00',
      );

      expect(outcome, isA<BidNeedsLowerConfirmation>());
      final request = outcome as BidNeedsLowerConfirmation;
      expect(request.standingAmount, '12600.00');
      expect(request.requestedAmount, '9000.00');
      expect(
        request.message,
        'المبلغ أقل من مزايدتك الحالية. أكّد الخفض إن كنت متأكداً.',
      );
    });

    test('التأكيد يُرسَل في النداء الثاني وحده', () async {
      final api = FakeBidsApi(bid: serverBid());
      final repository = build(api);

      await repository.placeBid(
        vehicleId: 'V-1',
        amount: '9000.00',
        confirmLower: true,
      );

      expect(api.submissions.single.confirmLower, isTrue);
    });

    test('طلب تأكيد بلا مبلغيه يُعرض كرفض عادي ولا يُخترع له رقم', () async {
      // حوارٌ تعريفه «يذكر المبلغين» لا ينعقد بمبلغ واحد. البديل الوحيد لو
      // أكملنا الشكل هو رقم من عندنا، وهو أسوأ من عدم فتح الحوار.
      final api = FakeBidsApi(bid: serverBid())
        ..failWith = refusal(
          code: 'lower_needs_confirm',
          message: 'المبلغ أقل من مزايدتك الحالية.',
        );
      final repository = build(api);

      await expectLater(
        repository.placeBid(vehicleId: 'V-1', amount: '9000.00'),
        throwsA(isA<ApiFailure>()),
      );
    });
  });

  group('كل سبب رفض يصل برسالته المُعدَّدة (F2 / J7)', () {
    // القائمة تُقرأ من `test/support/server_refusal_reasons.dart` ولا تُكتب
    // هنا. كانت مكتوبة هنا، وحملت أربعة رموز لا يرسلها الخادم أصلاً وغابت
    // عنها خمسة يرسلها — ومرّت خضراء، لأن الاختبار كان يزوّد الواجهة المزيَّفة
    // بالرمز الذي يتوقّعه ثم يتحقّق أنه وصل. الآن يحرس التطابقَ مع تعداد
    // الخلفية فحصٌ يقرأ التعداد من مصدره:
    // `test/architecture/refusal_codes_match_the_server_test.dart`.
    //
    // الاختبار لا يتحقق من صياغة عربية عندنا — يتحقق أنه **لا صياغة عندنا**:
    // ما يصل الشاشة هو نصّ الخادم حرفاً بحرف.
    for (final entry in serverRefusalReasons.entries) {
      test(entry.key, () async {
        final api = FakeBidsApi(bid: serverBid())
          ..failWith = refusal(code: entry.key, message: entry.value);
        final repository = build(api);

        await expectLater(
          repository.placeBid(vehicleId: 'V-1', amount: '100.00'),
          throwsA(
            isA<ApiFailure>()
                .having((f) => f.code, 'code', entry.key)
                .having((f) => f.message, 'message', entry.value),
          ),
        );
      });
    }

    test('رمز لم يره التطبيق من قبل يمرّ برسالته ولا يُبتلع', () async {
      final api = FakeBidsApi(bid: serverBid())
        ..failWith = refusal(
          code: 'reason_added_next_month',
          message: 'سبب جديد لم يكن موجوداً يوم كُتب التطبيق.',
        );
      final repository = build(api);

      await expectLater(
        repository.placeBid(vehicleId: 'V-1', amount: '100.00'),
        throwsA(
          isA<ApiFailure>().having(
            (f) => f.message,
            'message',
            'سبب جديد لم يكن موجوداً يوم كُتب التطبيق.',
          ),
        ),
      );
    });
  });

  group('سحب المزايدة', () {
    test('السحب يُرسَل بمعرّف المزايدة وترجع بحالتها الجديدة', () async {
      final api = FakeBidsApi(
        bid: serverBid(status: BidStatus.withdrawn, statusLabel: 'مسحوبة'),
      );
      final repository = build(api);

      final bid = await repository.withdrawBid('BID-1');

      expect(api.withdrawn, <String>['BID-1']);
      expect(bid.state, BidState.withdrawn);
      expect(bid.isWithdrawn, isTrue);
      expect(bid.stateLabel, 'مسحوبة');
    });

    test('مزايدة ليست له: جواب الخادم كما هو، لا فحص ملكية عندنا', () async {
      final api = FakeBidsApi(bid: serverBid())
        ..failWith = refusal(
          code: 'not_your_bid',
          message: 'هذه المزايدة ليست مزايدتك.',
          statusCode: 404,
        );
      final repository = build(api);

      await expectLater(
        repository.withdrawBid('BID-9'),
        throwsA(
          isA<ApiFailure>().having(
            (f) => f.message,
            'message',
            'هذه المزايدة ليست مزايدتك.',
          ),
        ),
      );
      // النداء خرج فعلاً: الشاشة لم تمنعه بحكمٍ من عندها.
      expect(api.withdrawn, <String>['BID-9']);
    });
  });

  group('مزايداتي', () {
    PaginatedBidList page() =>
        PaginatedBidList(count: 1, results: <Bid>[serverBid()]);

    test('النجاح يرجع نسخة طازجة ويكتبها في الكاش', () async {
      final cache = MemoryResponseCache();
      final repository = build(FakeBidsApi(page: page()), cache: cache);

      final snapshot = await repository.myBids();

      expect(snapshot.origin, DataOrigin.network);
      expect(snapshot.fetchedAt, fetchedAt);
      expect(snapshot.value.single.money.amount, '12600.00');
      expect(cache.writeCount, 1);
    });

    test('حالة المزايدة تُعرض بوصفها العربي من الخادم', () async {
      final repository = build(
        FakeBidsApi(
          page: PaginatedBidList(
            count: 1,
            results: <Bid>[
              serverBid(status: BidStatus.leading, statusLabel: 'الأعلى'),
            ],
          ),
        ),
      );

      final snapshot = await repository.myBids();

      expect(snapshot.value.single.stateLabel, 'الأعلى');
    });

    test('حالة لم يعرفها التطبيق لا تُسقط الاستجابة', () async {
      // المادة ٢-٣: كلمة الطرف الآخر تُحفظ ولا يُبنى عليها منطق. الوصف العربي
      // يبقى صحيحاً حتى لحالة لا يعرفها هذا الإصدار.
      final decoded = PaginatedBidList.fromJson(<String, Object?>{
        'count': 1,
        'results': <Object?>[
          <String, Object?>{
            'id': 'BID-7',
            'vehicle_id': 'V-2',
            'amount': '900.00',
            'currency': 'SAR',
            'status': 'reserved_for_review',
            'status_label': 'قيد المراجعة',
            'placed_at': '2026-09-01T07:30:00Z',
          },
        ],
      });
      final repository = build(FakeBidsApi(page: decoded));

      final snapshot = await repository.myBids();

      expect(snapshot.value.single.state, BidState.unknown);
      expect(snapshot.value.single.stateLabel, 'قيد المراجعة');
    });

    test('انقطاع الشبكة بعد نجاح سابق يعرض المحفوظ بطابعه', () async {
      final cache = MemoryResponseCache();
      final api = FakeBidsApi(page: page());
      final repository = build(api, cache: cache);
      await repository.myBids();

      api.failWith = offline();
      final snapshot = await repository.myBids();

      expect(snapshot.origin, DataOrigin.cache);
      expect(snapshot.isStale, isTrue);
      expect(snapshot.value.single.money.amount, '12600.00');
    });

    test('انقطاع بلا كاش يرمي العطب ولا يرجع قائمة فارغة', () async {
      // «لا مزايدات لك» لمن زايد قبل دقيقة كذبة، وهي أسوأ من «تعذّر التحديث».
      final api = FakeBidsApi(page: page())..failWith = offline();
      final repository = build(api);

      await expectLater(repository.myBids(), throwsA(isA<TransportFailure>()));
    });

    test('خطأ ردّ به الخادم لا يُخفى خلف بيانات قديمة', () async {
      final cache = MemoryResponseCache();
      final api = FakeBidsApi(page: page());
      final repository = build(api, cache: cache);
      await repository.myBids();

      api.failWith = refusal(
        code: 'not_authenticated',
        message: 'يلزم تسجيل الدخول',
        statusCode: 401,
      );

      await expectLater(repository.myBids(), throwsA(isA<ApiFailure>()));
    });
  });
}
