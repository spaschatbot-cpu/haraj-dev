import '../../common/snapshot.dart';
import '../entities/placed_bid.dart';
import '../repositories/bidding_repository.dart';

/// «وريني مزايداتي.»
final class LoadMyBids {
  const LoadMyBids(this._repository);

  final BiddingRepository _repository;

  Future<Snapshot<List<PlacedBid>>> call() => _repository.myBids();
}
