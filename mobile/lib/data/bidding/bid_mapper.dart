import '../../domain/bidding/entities/live_bids_update.dart';
import '../../domain/bidding/entities/placed_bid.dart';
import '../../domain/common/money.dart';
import '../api/generated/models/bid.dart' as api;
import '../api/generated/models/bid_status.dart' as api;
import '../api/generated/models/live_bid.dart' as api;
import '../api/generated/models/live_state.dart' as api;

/// تحويل نماذج المخطط المولَّدة إلى كيانات النطاق.
///
/// كما في `wallet_mapper.dart`: الطبقة موجودة كي لا يسافر نموذج مولَّد إلى
/// الشاشات، فيصير كل تغيير في المخطط تغييراً في كل شاشة. والمبلغ يُحفظ
/// **نصّاً كما وصل** — لا `double.parse` ولا تنسيق (المادة ٣-٢).
extension BidMapper on api.Bid {
  PlacedBid toDomain() => PlacedBid(
    id: id,
    vehicleId: vehicleId,
    vehicleTitle: vehicleTitle,
    money: Money(amount: amount, currency: currency),
    state: status.toDomain(),
    stateLabel: statusLabel,
    placedAtUtc: placedAt.toUtc(),
  );
}

extension BidStatusMapper on api.BidStatus {
  /// قيمة جديدة من الخادم تصير `unknown` ولا تُسقط الاستجابة (المادة ٢-٣).
  BidState toDomain() => switch (this) {
    api.BidStatus.placed => BidState.placed,
    api.BidStatus.outbid => BidState.outbid,
    api.BidStatus.leading => BidState.leading,
    api.BidStatus.withdrawn => BidState.withdrawn,
    api.BidStatus.won => BidState.won,
    api.BidStatus.lost => BidState.lost,
    api.BidStatus.$unknown => BidState.unknown,
  };
}

extension LiveStateMapper on api.LiveState {
  /// المركبات في الإطار تُهمَل هنا عمداً.
  ///
  /// البثّ يحملها لأنها حقائق عامة (حالة المزاد وحالة المركبة)، وشاشة
  /// المزايدة لا تعرض شيئاً منها: صفحة المركبة (T709) هي صاحبة ذلك العرض.
  /// إهمالها هنا أصدق من تمريرها إلى كيان لا يقرؤها أحد.
  List<LiveStandingBid> toDomainBids() =>
      bids.map((bid) => bid.toDomain()).toList(growable: false);
}

extension LiveBidMapper on api.LiveBid {
  LiveStandingBid toDomain() => LiveStandingBid(
    id: id,
    vehicleId: vehicleId,
    amount: amount,
    isWithdrawn: isWithdrawn,
    isSuperseded: isSuperseded,
  );
}
