import '../entities/live_bids_update.dart';
import '../repositories/bidding_repository.dart';

/// «خلّي أرقامي حيّة — وقل لي إن لم تعد.»
final class WatchLiveBids {
  const WatchLiveBids(this._repository);

  final BiddingRepository _repository;

  Stream<LiveBidsUpdate> call() => _repository.watchLive();
}
