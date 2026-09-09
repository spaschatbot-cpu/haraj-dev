import '../../domain/bidding/entities/live_bids_update.dart';
import '../../domain/bidding/entities/placed_bid.dart';
import '../../domain/common/money.dart';
import '../api/generated/models/bid.dart' as api;
import '../api/generated/models/bid_page.dart' as api;
import '../wallet/wallet_mapper.dart' show walletCurrency;

extension BidMapper on api.Bid {
  PlacedBid toDomain() => PlacedBid(
    id: '$id',
    vehicleId: '$vehicleId',
    auctionId: '$auctionId',
    lotNumber: '$lotNumber',
    vehicleTitle: vehicleTitle,
    money: Money(amount: amount, currency: walletCurrency),
    state: _stateOf(isWithdrawn: isWithdrawn, isSuperseded: isSuperseded),
    placedAtUtc: placedAt.toUtc(),
  );
}

extension BidPageMapper on api.BidPage {
  List<PlacedBid> toDomain() =>
      results.map((bid) => bid.toDomain()).toList(growable: false);
}

/// حالُ المزايدة من العلمين اللذين يرسلهما الخادم.
///
/// **السحب يسبق التجاوز** حين يجتمعان: مزايدةٌ سحبها صاحبها ثم وضع أعلى منها
/// «مسحوبة» لا «متجاوَزة» — الأولى فعلُه والثانية أثرُ فعله، والذي يهمّه أن
/// يعرف أنها لم تعد قائمةً بيده.
BidState _stateOf({required bool isWithdrawn, required bool isSuperseded}) {
  if (isWithdrawn) return BidState.withdrawn;
  if (isSuperseded) return BidState.superseded;
  return BidState.standing;
}

/// مزايدةٌ قائمة في البثّ الحيّ.
///
/// تُفكّ من JSON بيد لا بنموذجٍ مولَّد: `/api/v1/live/` بثٌّ نصّيّ (SSE) لا
/// نقطةٌ لها مخطط استجابة، فلا يولّد المولّد لها شيئاً — وهذا صحيح، الإطار
/// ليس جسم استجابة.
LiveStandingBid? liveBidFrom(Object? row) {
  if (row is! Map<String, Object?>) return null;
  final id = row['id'];
  final vehicleId = row['vehicle_id'];
  final amount = row['amount'];
  if (id == null || vehicleId == null || amount is! String) return null;
  return LiveStandingBid(
    id: '$id',
    vehicleId: '$vehicleId',
    amount: amount,
    isWithdrawn: row['is_withdrawn'] == true,
    isSuperseded: row['is_superseded'] == true,
  );
}
