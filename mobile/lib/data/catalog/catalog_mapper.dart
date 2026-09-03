import '../../domain/catalog/entities/auction_summary.dart';
import '../../domain/catalog/entities/vehicle_detail.dart';
import '../../domain/catalog/entities/vehicle_query.dart';
import '../../domain/catalog/entities/vehicle_summary.dart';
import '../../domain/common/money.dart';
import '../api/generated/models/auction.dart' as api;
import '../api/generated/models/paginated_vehicle_card_list.dart' as api;
import '../api/generated/models/specification.dart' as api;
import '../api/generated/models/vehicle.dart' as api;
import '../api/generated/models/vehicle_card.dart' as api;

/// تحويل نماذج المخطط المولَّدة إلى كيانات النطاق.
///
/// طبقة التحويل مقصودة: لولاها لسافر نموذج مولَّد إلى الشاشات، فصار كل تغيير في
/// المخطط تغييراً في كل شاشة. وهنا يُحفظ المبلغ **نصّاً** كما وصل — لا
/// `double.parse` ولا تنسيق (المادة ٣-٢).
extension AuctionMapper on api.Auction {
  AuctionSummary toDomain() => AuctionSummary(
    id: id,
    title: title,
    startsAt: startsAt.toUtc(),
    endsAt: endsAt.toUtc(),
    vehiclesCount: vehiclesCount,
  );
}

extension VehicleCardMapper on api.VehicleCard {
  VehicleSummary toDomain() => VehicleSummary(
    id: id,
    lotNumber: lotNumber,
    title: title,
    thumbnailUrl: thumbnailUrl,
    reservePrice: _money(reservePrice, currency),
    bidsCount: bidsCount,
  );
}

extension VehiclePageMapper on api.PaginatedVehicleCardList {
  VehiclePage toDomain() => VehiclePage(
    vehicles: results.map((card) => card.toDomain()).toList(growable: false),
    totalCount: count,
    // «هل من مزيد؟» سؤال أجاب عنه الخادم بـ`next`. حسابه هنا من طول القائمة
    // وحجم الصفحة تخمينٌ يخطئ في آخر صفحة ممتلئة تماماً.
    hasMore: next != null,
  );
}

extension VehicleMapper on api.Vehicle {
  VehicleDetail toDomain() => VehicleDetail(
    id: id,
    lotNumber: lotNumber,
    title: title,
    imageUrls: List<String>.unmodifiable(images),
    specifications: specifications
        .map((specification) => specification.toDomain())
        .toList(growable: false),
    reservePrice: _money(reservePrice, currency),
    biddingOpen: biddingOpen,
  );
}

extension SpecificationMapper on api.Specification {
  VehicleSpecification toDomain() =>
      VehicleSpecification(label: label, value: value);
}

/// مبلغٌ اختياري كما وصل نصّاً.
///
/// الغياب يبقى غياباً: مركبةٌ بلا سعر وقوف ليست مركبةً سعرها صفر، وتحويل
/// الأول إلى الثاني هنا يضع أمام العميل رقماً لم يختره أحد.
Money? _money(String? amount, String currency) =>
    amount == null ? null : Money(amount: amount, currency: currency);
