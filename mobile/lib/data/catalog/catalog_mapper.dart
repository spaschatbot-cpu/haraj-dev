import '../../domain/catalog/entities/auction_phase.dart';
import '../../domain/catalog/entities/auction_summary.dart';
import '../../domain/catalog/entities/vehicle_detail.dart';
import '../../domain/catalog/entities/vehicle_feed.dart';
import '../../domain/catalog/entities/vehicle_query.dart';
import '../../domain/catalog/entities/vehicle_summary.dart';
import '../../domain/common/money.dart';
import '../api/generated/models/auction.dart' as api;
import '../api/generated/models/auction_phase.dart' as api;
import '../api/generated/models/paginated_vehicle_card_list.dart' as api;
import '../api/generated/models/phase_counts.dart' as api;
import '../api/generated/models/specification.dart' as api;
import '../api/generated/models/vehicle.dart' as api;
import '../api/generated/models/vehicle_card.dart' as api;
import '../api/generated/models/vehicle_feed_page.dart' as api;

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
    auctionId: auctionId,
    phase: phase.toDomain(),
    auctionEndsAt: auctionEndsAt.toUtc(),
  );
}

extension AuctionPhaseMapper on api.AuctionPhase {
  /// طورٌ لم يعرفه هذا الإصدار يصير `unknown` ولا يرمي: المادة ٢-٣ — كلمة
  /// الخادم تُحفظ ولا تُسقط الاستجابة التي تحملها. مركبةٌ بطورٍ مجهول تُعرض،
  /// ولا يُقال عنها «منتهية».
  AuctionPhase toDomain() => switch (this) {
    api.AuctionPhase.upcoming => AuctionPhase.upcoming,
    api.AuctionPhase.active => AuctionPhase.active,
    api.AuctionPhase.ended => AuctionPhase.ended,
    api.AuctionPhase.$unknown => AuctionPhase.unknown,
  };
}

/// الاتجاه المعاكس — طورٌ يُسأل عنه الخادم.
///
/// `unknown` لا يُرسَل: لا معنى لسؤال «وريني ما لا أفهمه»، وإرسال نصٍّ فارغ
/// يجعل الخادم يرشّح على قيمة لا وجود لها فيردّ فراغاً بلا سبب مكتوب.
api.AuctionPhase? apiPhaseOf(AuctionPhase? phase) => switch (phase) {
  AuctionPhase.upcoming => api.AuctionPhase.upcoming,
  AuctionPhase.active => api.AuctionPhase.active,
  AuctionPhase.ended => api.AuctionPhase.ended,
  AuctionPhase.unknown || null => null,
};

extension PhaseCountsMapper on api.PhaseCounts {
  PhaseCounts toDomain() =>
      PhaseCounts(upcoming: upcoming, active: active, ended: ended);
}

extension VehicleFeedMapper on api.VehicleFeedPage {
  VehicleFeed toDomain() => VehicleFeed(
    page: VehiclePage(
      vehicles: results.map((card) => card.toDomain()).toList(growable: false),
      totalCount: count,
      hasMore: next != null,
    ),
    counts: counts.toDomain(),
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
