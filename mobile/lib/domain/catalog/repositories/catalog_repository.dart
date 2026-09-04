import '../../common/snapshot.dart';
import '../entities/auction_summary.dart';
import '../entities/vehicle_detail.dart';
import '../entities/vehicle_feed.dart';
import '../entities/vehicle_query.dart';

/// عقد التصفّح: المزادات، مركبات المزاد، والمركبة الواحدة.
///
/// كلها ترجع `Snapshot` لا القيمة مجرَّدة — العرض يحتاج أن يعرف أهي آخر نسخة
/// من الخادم أم نسخة محفوظة ومتى جُلبت، وإلا تعذّر تنفيذ H5 بصدق.
abstract interface class CatalogRepository {
  /// مزادات الرئيسية. القسمة إلى «جارية» و«قادمة» من الخادم لا من التطبيق:
  /// استعلامان بحالتين، لا استعلام واحد يصنّفه العميل.
  Future<Snapshot<HomeAuctions>> loadHomeAuctions();

  /// صفحة من مركبات مزاد بمعايير الخادم.
  ///
  /// لا يوجد نظير يرجع «كل المركبات»: قائمة بمئتي مركبة تُقرأ صفحةً صفحة،
  /// وتحميلها كاملةً هو بالضبط ما يكسر H2.
  Future<Snapshot<VehiclePage>> loadAuctionVehicles(
    String auctionId,
    VehicleQuery query,
  );

  /// الشبكة المسطّحة عبر المزادات: صفحةُ تبويبٍ **وعدّاداته الثلاثة في طلب
  /// واحد**.
  ///
  /// لا نظير له يرجّع العدّادات وحدها: طلبٌ ثانٍ للأرقام يجعلها من لحظةٍ غير
  /// لحظة الصفحة، فيقول التبويب رقماً لا يصف ما يُفتح فيه.
  ///
  /// [query] لا بدّ أن يحمل `phase` — بلا تبويبٍ لا سؤال.
  Future<Snapshot<VehicleFeed>> loadVehicleFeed(VehicleQuery query);

  Future<Snapshot<VehicleDetail>> loadVehicle(String vehicleId);
}
