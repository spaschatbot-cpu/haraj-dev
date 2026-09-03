/// الشاشة التي يفتحها إشعار — قراراً واحداً، قابلاً للاختبار بلا Flutter.
///
/// معيار القبول H6 «الإشعار يفتح الشاشة الصحيحة مباشرةً» مسألة **قرار** قبل أن
/// يكون مسألة تنقّل: أي حمولة تؤدّي إلى أي شاشة. القرار هنا نطاقي صافٍ،
/// والترجمة إلى عنوان سطران في `lib/app/routes.dart`. الفصل مقصود: قرار مدفون
/// داخل مستمع تنقّل لا يُختبر إلا بتشغيل تطبيق كامل، فلا يُختبر.
library;

/// نوع الشاشة المقصودة.
///
/// `home` ليست حالة خطأ بل الوجهة الافتراضية: حمولة لا نفهمها تفتح الرئيسية
/// ولا تُسقط شيئاً (المادة ٣-٥ — قيمة لم نرها من قبل لا تُسقط ما تحملها،
/// والمادة ٢-٢ — لا فرع ينتهي صامتاً).
enum PushTarget { home, auction, vehicle, bids, wallet, invoice }

/// وجهة مكتملة.
///
/// المنشئات مسمّاة عمداً، وكلٌّ منها يطلب ما لا تصلح الوجهة بدونه: وجهة مركبة
/// بلا رقم مركبة تولّد عنواناً مثل `/vehicles/null`، وهو ما يراه المستخدم شاشةَ
/// خطأ بعد ضغطه إشعاراً. ما لا يجوز أن يوجد لا يُترك للانتباه.
final class PushDestination {
  const PushDestination._(
    this.target, {
    this.auctionId,
    this.vehicleId,
    this.invoiceId,
  });

  const PushDestination.home() : this._(PushTarget.home);

  const PushDestination.auction(String auctionId)
    : this._(PushTarget.auction, auctionId: auctionId);

  /// المركبة تحمل مزادها معه حين يصل: شاشة المركبة تعرض المزاد الذي تنتمي إليه.
  const PushDestination.vehicle(String vehicleId, {String? auctionId})
    : this._(PushTarget.vehicle, vehicleId: vehicleId, auctionId: auctionId);

  const PushDestination.bids() : this._(PushTarget.bids);

  const PushDestination.wallet() : this._(PushTarget.wallet);

  /// فاتورة بعينها إن عُرف رقمها، وإلا قائمة الفواتير.
  const PushDestination.invoice({String? invoiceId})
    : this._(PushTarget.invoice, invoiceId: invoiceId);

  final PushTarget target;
  final String? auctionId;
  final String? vehicleId;
  final String? invoiceId;

  @override
  bool operator ==(Object other) =>
      other is PushDestination &&
      other.target == target &&
      other.auctionId == auctionId &&
      other.vehicleId == vehicleId &&
      other.invoiceId == invoiceId;

  @override
  int get hashCode => Object.hash(target, auctionId, vehicleId, invoiceId);

  @override
  String toString() =>
      'PushDestination($target, auction=$auctionId, vehicle=$vehicleId, '
      'invoice=$invoiceId)';
}
