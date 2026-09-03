import '../../common/money.dart';
import 'invoice.dart';

/// حالة المركبة التي رست على المشتري — من الخادم.
enum PurchaseState { awarded, invoiced, paid, handedOver, cancelled, unknown }

/// مركبة رست على العميل، ومعها فاتورتها إن صدرت.
///
/// الفاتورة **مضمَّنة** لا مطابَقة بمعرّف في الشاشة: ربط المشتريات بالفواتير
/// قاعدة عمل، ومكانها الخادم (`PurchaseSerializer.get_invoice`).
final class Purchase {
  const Purchase({
    required this.id,
    required this.vehicleId,
    required this.lotNumber,
    required this.title,
    required this.auctionTitle,
    required this.awardedPrice,
    required this.awardedAt,
    required this.state,
    required this.stateLabel,
    this.invoice,
  });

  final String id;
  final String vehicleId;
  final String lotNumber;
  final String title;
  final String auctionTitle;

  final Money awardedPrice;

  /// بتوقيت UTC.
  final DateTime awardedAt;

  final PurchaseState state;

  /// حالة المركبة بالعربية من الخادم.
  final String stateLabel;

  /// تغيب حتى تصدر الفاتورة — والغياب حالة تُعرض، لا فراغ يُملأ باجتهاد.
  final Invoice? invoice;
}
