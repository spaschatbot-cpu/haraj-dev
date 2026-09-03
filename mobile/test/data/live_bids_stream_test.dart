import 'dart:async';

import 'package:flutter_test/flutter_test.dart';
import 'package:haraj_mobile/data/bidding/bidding_repository_impl.dart';
import 'package:haraj_mobile/domain/bidding/entities/live_bids_update.dart';

import '../support/fake_bids_api.dart';
import '../support/fake_sse_channel.dart';
import '../support/memory_response_cache.dart';

/// T710 / T624 — البثّ الحي.
///
/// المعيار الذي تدور حوله كل الاختبارات هنا جملة واحدة من التاسك: **رقم مزايدة
/// قديم يبدو حياً أسوأ من لا رقم.** فالمطلوب ليس أن تصل الأرقام، بل ألّا تبقى
/// معروضة بلا علامة حين يتوقّف وصولها — سواء انقطع الاتصال أو صمت الخادم
/// والمقبس مفتوح.
void main() {
  BiddingRepositoryImpl build(
    FakeSseChannel channel, {
    Duration silence = const Duration(milliseconds: 50),
    Duration reconnect = Duration.zero,
  }) => BiddingRepositoryImpl(
    api: FakeBidsApi(),
    cache: MemoryResponseCache(),
    live: channel,
    reconnectDelay: reconnect,
    silenceTimeout: silence,
  );

  test('يبدأ بـ«جارٍ الاتصال» قبل أن يصل أي إطار', () async {
    final channel = FakeSseChannel(<Stream<String>>[]);
    final repository = build(channel);

    final first = await repository.watchLive().first;

    expect(first.connection, LiveConnection.connecting);
    expect(first.bids, isEmpty);
    await channel.dispose();
  });

  test('إطار الحالة يجعل الاتصال حياً ويحمل المبلغ نصّاً كما وصل', () async {
    final channel = FakeSseChannel(<Stream<String>>[
      Stream<String>.fromIterable(<String>[
        stateFrame(liveBidPayload(amount: '12500.10')),
      ]),
    ]);
    final repository = build(channel);

    final updates = await repository.watchLive().take(2).toList();

    expect(updates.last.connection, LiveConnection.live);
    expect(updates.last.bids.single.amount, '12500.10');
    expect(updates.last.isStale, isFalse);
    await channel.dispose();
  });

  test('النبضة تُبقي الاتصال حياً ولا تُصدر تحديثاً بلا تغيّر', () async {
    // إعادة بناء الشاشة كل ثانيتين بلا تغيّر تكلفة بلا قارئ. والأهم أن النبضة
    // ليست حدثاً للمستخدم: هي دليل حياة لا خبر.
    final channel = FakeSseChannel(<Stream<String>>[
      Stream<String>.fromIterable(<String>[
        heartbeatFrame,
        stateFrame(liveBidPayload()),
        heartbeatFrame,
        heartbeatFrame,
      ]),
    ]);
    final repository = build(channel);

    final updates = await repository.watchLive().take(3).toList();

    // «جارٍ الاتصال» ثم «حي» عند أول نبضة ثم إطار الحالة — والنبضتان بعده
    // لم تُصدرا شيئاً، ولو أصدرتا لكان الثالث منهما لا حالةً.
    expect(updates.map((u) => u.connection), <LiveConnection>[
      LiveConnection.connecting,
      LiveConnection.live,
      LiveConnection.live,
    ]);
    expect(updates.last.bids, hasLength(1));
    await channel.dispose();
  });

  test('انقطاع البثّ يُعلَن ويُعاد الاتصال من تلقاء التطبيق', () async {
    final channel = FakeSseChannel(<Stream<String>>[
      Stream<String>.fromIterable(<String>[
        stateFrame(liveBidPayload(amount: '900.00')),
      ]),
      Stream<String>.fromIterable(<String>[
        stateFrame(liveBidPayload(amount: '1000.00')),
      ]),
    ]);
    final repository = build(channel);

    final updates = await repository.watchLive().take(5).toList();

    expect(updates.map((u) => u.connection), <LiveConnection>[
      LiveConnection.connecting,
      LiveConnection.live,
      LiveConnection.lost,
      LiveConnection.connecting,
      LiveConnection.live,
    ]);
    expect(updates.last.bids.single.amount, '1000.00');
    expect(channel.opened, 2);
    await channel.dispose();
  });

  test('الأرقام تبقى معروضة عند الانقطاع، ومعها العلامة', () async {
    // محو القائمة عند أول انقطاع يخفي عن العميل ما زايد به فعلاً. الأرقام
    // تبقى، و`isStale` هي التي تقول كم تُصدَّق.
    final channel = FakeSseChannel(<Stream<String>>[
      Stream<String>.fromIterable(<String>[
        stateFrame(liveBidPayload(amount: '900.00')),
      ]),
    ]);
    final repository = build(channel);

    final updates = await repository.watchLive().take(3).toList();
    final lost = updates.last;

    expect(lost.connection, LiveConnection.lost);
    expect(lost.isStale, isTrue);
    expect(lost.bids.single.amount, '900.00');
    await channel.dispose();
  });

  test('خادم صامت والمقبس مفتوح يُعلَن انقطاعاً بعد مهلة النبض', () async {
    // أخطر حالة: لا خطأ شبكة، ولا إغلاق. الشاشة تبدو سليمة وأرقامها بائتة.
    final channel = FakeSseChannel(<Stream<String>>[]);
    final repository = build(
      channel,
      silence: const Duration(milliseconds: 30),
    );

    final updates = await repository
        .watchLive()
        .take(2)
        .toList()
        .timeout(const Duration(seconds: 5));

    expect(updates.last.connection, LiveConnection.lost);
    await channel.dispose();
  });

  test('إطار لا يُقرأ لا يمحو آخر ما نعرف', () async {
    final channel = FakeSseChannel(<Stream<String>>[
      Stream<String>.fromIterable(<String>[
        stateFrame(liveBidPayload(amount: '900.00')),
        stateFrame('{ليس JSON'),
      ]),
    ]);
    final repository = build(channel);

    final updates = await repository.watchLive().take(3).toList();

    // الإطار التالف لم يُصدر تحديثاً أصلاً، فآخر ما وصل هو «حي» بـ900 ثم
    // «انقطع» بعد انتهاء البثّ — والرقم كما هو في الحالتين.
    expect(updates[1].bids.single.amount, '900.00');
    expect(updates[2].bids.single.amount, '900.00');
    await channel.dispose();
  });

  test('المسحوبة والمستبدَلة ليستا «مزايدتي القائمة»', () async {
    final channel = FakeSseChannel(<Stream<String>>[
      Stream<String>.fromIterable(<String>[
        stateFrame(liveBidPayload(amount: '900.00', isWithdrawn: true)),
      ]),
    ]);
    final repository = build(channel);

    final updates = await repository.watchLive().take(2).toList();

    expect(updates.last.bids, hasLength(1));
    expect(updates.last.standingOn('V-1'), isNull);
    await channel.dispose();
  });
}
