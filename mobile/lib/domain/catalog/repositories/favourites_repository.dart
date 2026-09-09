import '../../common/snapshot.dart';
import '../entities/vehicle_query.dart';

/// مركبات حفظها العميل ليعود إليها.
///
/// **واجهةٌ مستقلّة عن `CatalogRepository`** رغم أن الاثنتين تُرجعان مركبات:
/// التصفّح سؤالٌ عن معروضٍ عامّ، والمفضلة سؤالٌ عن **قائمة هذا العميل** — تحتاج
/// جلسةً، وتتغيّر بفعله لا بفعل المزاد. جمعُهما في واجهةٍ واحدة يجعل نصفها
/// يحتاج تسجيلَ دخولٍ ونصفها لا، فينسى أحدهم أيُّ نصف.
abstract interface class FavouritesRepository {
  /// صفحةٌ من مفضّلات العميل.
  Future<Snapshot<VehiclePage>> loadFavourites({int page = 1});

  /// يُضيف مركبةً إلى المفضلة.
  ///
  /// **مُتسامحٌ مع التكرار عمداً**: إضافةُ ما هو مضافٌ ليست خطأً يُعرض للعميل،
  /// وضغطتان سريعتان على القلب لا يجوز أن تنتهيا برسالة حمراء.
  Future<void> mark(String vehicleId);

  /// يزيلها منها.
  Future<void> unmark(String vehicleId);
}
