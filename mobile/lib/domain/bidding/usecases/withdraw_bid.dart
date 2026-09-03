import '../entities/placed_bid.dart';
import '../repositories/bidding_repository.dart';

/// «اسحب هذه المزايدة.»
///
/// لا تسأل إن كانت المزايدة له، ولا إن كان الوقت يسمح. مزايدة غيره ترجع 404
/// من الخادم، وفحصُ الملكية في شاشةٍ هو فحصٌ غائب عن كل طريق آخر إلى النقطة.
final class WithdrawBid {
  const WithdrawBid(this._repository);

  final BiddingRepository _repository;

  Future<PlacedBid> call(String bidId) => _repository.withdrawBid(bidId);
}
