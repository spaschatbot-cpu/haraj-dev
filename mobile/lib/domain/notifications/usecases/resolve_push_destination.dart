import '../entities/push_destination.dart';
import '../entities/push_notification.dart';

/// من حمولة الإشعار إلى الشاشة — نقطة القرار الوحيدة (المادة ٤-٥).
///
/// **العقد:** الخادم يضع في `data` مفتاح `type`، ومعه معرّفات ما يشير إليه
/// (`auction_id` / `vehicle_id` / `invoice_id`). ما عداها يُتجاهل.
///
/// قاعدتان تحكمان الاشتقاق:
///
/// * **نوع لم نره من قبل يفتح الرئيسية ولا يُسقط الإشعار.** التطبيق المنشور
///   أقدم من الخادم دائماً؛ يوم يضيف الخادم نوعاً جديداً يبقى إشعاره يفتح
///   شيئاً بدل أن يُبتلع (المادتان ٢-٣ و٣-٥).
/// * **وجهة تحتاج معرّفاً ولم يصل تسقط إلى أقرب وجهة صالحة.** «افتح مركبة بلا
///   رقم» شاشة خطأ في وجه المستخدم؛ «افتح المزاد» جواب أنقص لكنه صحيح.
abstract final class ResolvePushDestination {
  /// مفتاح النوع في الحمولة.
  static const String typeKey = 'type';

  static PushDestination call(PushNotification notification) {
    final data = notification.data;
    final auctionId = _id(data['auction_id']);
    final vehicleId = _id(data['vehicle_id']);
    final invoiceId = _id(data['invoice_id']);

    return switch (data[typeKey]) {
      // المزايدة: العميل يريد المركبة نفسها ليردّ فوراً، لا قائمة المزاد.
      'outbid' ||
      'bid_placed' ||
      'bid_won' ||
      'bid_lost' => _vehicleOrAuction(auctionId, vehicleId),

      'auction_starting' || 'auction_ended' || 'auction_updated' =>
        auctionId == null
            ? const PushDestination.home()
            : PushDestination.auction(auctionId),

      'invoice_issued' ||
      'invoice_due' ||
      'invoice_paid' => PushDestination.invoice(invoiceId: invoiceId),

      'topup_settled' ||
      'refund_decided' ||
      'hold_placed' ||
      'hold_released' => const PushDestination.wallet(),

      'bids_summary' => const PushDestination.bids(),

      // يشمل `null`: إشعار بلا نوع أصلاً، وهو ما يصل لو أرسل الخادم إشعار عرض
      // بحت. يفتح الرئيسية.
      _ => const PushDestination.home(),
    };
  }

  static PushDestination _vehicleOrAuction(
    String? auctionId,
    String? vehicleId,
  ) {
    if (vehicleId != null) {
      return PushDestination.vehicle(vehicleId, auctionId: auctionId);
    }
    if (auctionId != null) return PushDestination.auction(auctionId);
    return const PushDestination.bids();
  }

  /// معرّف فارغ أو مسافات ليس معرّفاً — `''` في المسار يولّد `/vehicles//`.
  static String? _id(String? raw) {
    final trimmed = raw?.trim();
    return (trimmed == null || trimmed.isEmpty) ? null : trimmed;
  }
}
