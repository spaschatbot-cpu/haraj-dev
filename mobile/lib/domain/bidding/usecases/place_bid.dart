import '../entities/bid_outcome.dart';
import '../repositories/bidding_repository.dart';

/// «زايد بهذا المبلغ على هذه المركبة.»
///
/// رقيقة عمداً: لا شيء تقرّره. وجودها أن يكون في التطبيق **اسمٌ واحد** تناديه
/// كل شاشة تريد إرسال مزايدة — الرئيسية، وصفحة المركبة، ومزايداتي — فلا يتكرّر
/// مسار الإرسال ست مرات كما تكرّر في v1.
final class PlaceBid {
  const PlaceBid(this._repository);

  final BiddingRepository _repository;

  Future<BidOutcome> call({
    required String vehicleId,
    required String amount,
    bool confirmLower = false,
  }) => _repository.placeBid(
    vehicleId: vehicleId,
    amount: amount,
    confirmLower: confirmLower,
  );
}
