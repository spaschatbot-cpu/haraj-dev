import '../entities/bid_quote.dart';
import '../repositories/bidding_repository.dart';

/// «كم يصير المبلغ بعد الضريبة؟» — قبل أن يلتزم العميل.
final class QuoteBid {
  const QuoteBid(this._repository);

  final BiddingRepository _repository;

  Future<BidQuote> call(String amount) => _repository.quote(amount);
}
