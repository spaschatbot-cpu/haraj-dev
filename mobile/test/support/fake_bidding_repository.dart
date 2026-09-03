import 'dart:async';

import 'package:haraj_mobile/domain/bidding/entities/bid_outcome.dart';
import 'package:haraj_mobile/domain/bidding/entities/live_bids_update.dart';
import 'package:haraj_mobile/domain/bidding/entities/placed_bid.dart';
import 'package:haraj_mobile/domain/bidding/repositories/bidding_repository.dart';
import 'package:haraj_mobile/domain/common/money.dart';
import 'package:haraj_mobile/domain/common/snapshot.dart';

/// مستودع مزايدة مزيَّف لاختبارات الشاشات.
///
/// يسجّل ما طلبته الشاشة لأن أهم ما يُختبر في الشاشة ليس ما تعرضه فقط، بل
/// **ما ترسله**: أن النداء الأول لا يحمل تأكيد الخفض، وأن الثاني لا يخرج إلا
/// بعد أن أكّد المستخدم فعلاً.
final class FakeBiddingRepository implements BiddingRepository {
  FakeBiddingRepository({
    this.outcomes = const <Object>[],
    this.bids = const <PlacedBid>[],
    this.live,
    this.myBidsFailure,
    this.withdrawFailure,
    this.myBidsDelay = Duration.zero,
  });

  /// الجواب المرتَّب لكل نداء `placeBid`: إمّا `BidOutcome` يُرجَع، وإمّا
  /// `Failure` يُرمى. اللائحة مرتّبة لأن ما يميّز الخفض أن النداء الثاني يختلف
  /// عن الأول، وجوابٌ واحد ثابت لا يستطيع وصف ذلك.
  final List<Object> outcomes;

  final List<PlacedBid> bids;
  final Stream<LiveBidsUpdate>? live;
  final Object? myBidsFailure;
  final Object? withdrawFailure;

  /// تأخير مقصود كي تُرى حالة التحميل — بلا تأخير تُحلّ الـFuture في نفس
  /// الإطار، فيمرّ اختبار «تظهر الدوّامة» بلا أن يرى دوّامة قط.
  final Duration myBidsDelay;

  final List<({String amount, bool confirmLower})> submissions =
      <({String amount, bool confirmLower})>[];
  final List<String> withdrawn = <String>[];

  bool cached = false;

  @override
  Future<BidOutcome> placeBid({
    required String vehicleId,
    required String amount,
    bool confirmLower = false,
  }) async {
    submissions.add((amount: amount, confirmLower: confirmLower));
    final index = submissions.length - 1;
    if (index >= outcomes.length) throw StateError('لا جواب مُعدّ لهذا النداء');
    final outcome = outcomes[index];
    if (outcome is BidOutcome) return outcome;
    throw outcome;
  }

  @override
  Future<PlacedBid> withdrawBid(String bidId) async {
    withdrawn.add(bidId);
    final failure = withdrawFailure;
    if (failure != null) throw failure;
    return bids.first;
  }

  @override
  Future<Snapshot<List<PlacedBid>>> myBids() async {
    if (myBidsDelay > Duration.zero) await Future<void>.delayed(myBidsDelay);
    final failure = myBidsFailure;
    if (failure != null) throw failure;
    return cached
        ? Snapshot<List<PlacedBid>>.cached(
            bids,
            storedAt: DateTime.utc(2026, 9, 1, 5),
          )
        : Snapshot<List<PlacedBid>>.fresh(
            bids,
            at: DateTime.utc(2026, 9, 1, 8),
          );
  }

  @override
  Stream<LiveBidsUpdate> watchLive() =>
      live ??
      Stream<LiveBidsUpdate>.value(
        const LiveBidsUpdate(
          connection: LiveConnection.live,
          bids: <LiveStandingBid>[],
        ),
      );
}

/// مزايدة نطاق جاهزة للعرض.
PlacedBid domainBid({
  String id = 'BID-1',
  String vehicleId = 'V-1',
  String? vehicleTitle = 'تويوتا كامري 2021',
  String amount = '12600.00',
  BidState state = BidState.placed,
  String stateLabel = 'مزايدة قائمة',
}) => PlacedBid(
  id: id,
  vehicleId: vehicleId,
  vehicleTitle: vehicleTitle,
  money: Money(amount: amount, currency: 'SAR'),
  state: state,
  stateLabel: stateLabel,
  placedAtUtc: DateTime.utc(2026, 9, 1, 7, 30),
);
