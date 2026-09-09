import '../../domain/catalog/entities/auction_phase.dart';
import '../../domain/catalog/entities/auction_summary.dart';
import '../../domain/catalog/entities/vehicle_detail.dart';
// `VehiclePage` اسمٌ في الجانبين — صفحةُ النطاق وصفحةُ العقد. اللاحقة تفصل
// بينهما بلا إعادة تسمية أيٍّ منهما: كلاهما مسمّى بحقّه في موضعه.
import '../../domain/catalog/entities/vehicle_feed.dart' as domain;
import '../../domain/catalog/entities/vehicle_query.dart' as domain;
import '../../domain/catalog/entities/vehicle_state.dart';
import '../../domain/catalog/entities/vehicle_summary.dart';
import '../../domain/common/money.dart';
import '../api/generated/models/auction_card.dart' as api;
import '../api/generated/models/auction_page.dart' as api;
import '../api/generated/models/phase_counts.dart' as api;
import '../api/generated/models/vehicle_card.dart' as api;
import '../api/generated/models/vehicle_images.dart' as api;
import '../api/generated/models/vehicle_page.dart' as api;

/// تحويل نماذج المخطط المولَّدة إلى كيانات النطاق.
///
/// طبقة التحويل مقصودة: لولاها لسافر نموذج مولَّد إلى الشاشات، فصار كل تغيير في
/// المخطط تغييراً في كل شاشة. وقد أثبتت نفسها يوم نُقل التطبيق من مخططٍ وهميّ
/// إلى عقد الخلفية: انكسرت هي وحدها، ولم تُلمس شاشةٌ واحدة.
///
/// وهنا يُحفظ المبلغ **نصّاً** كما وصل — لا `double.parse` ولا تنسيق (المادة ٣-٢).
extension AuctionCardMapper on api.AuctionCard {
  AuctionSummary toDomain() => AuctionSummary(
    id: '$id',
    title: title,
    startsAt: startsAt.toUtc(),
    endsAt: endsAt.toUtc(),
    // الخادم يُرجعه `null` حين لا يكون قد عُدّ (قوائم لا تحتاجه). صفرٌ هنا
    // كذبة: «لا مركبات» غير «لم يُعدّ»، فيبقى الغياب غياباً حتى الشاشة.
    vehiclesCount: vehicleCount,
  );
}

extension AuctionPageMapper on api.AuctionPage {
  List<AuctionSummary> toDomain() =>
      results.map((card) => card.toDomain()).toList(growable: false);
}

extension VehicleCardMapper on api.VehicleCard {
  VehicleSummary toDomain() => VehicleSummary(
    id: '$id',
    lotNumber: '$lotNumber',
    title: title,
    thumbnailUrl: thumbnailUrl,
    reference: reference,
    adminFee: Money(amount: adminFee, currency: _currency),
    adminFeeWithVat: Money(amount: adminFeeWithVat, currency: _currency),
    auctionId: '$auctionId',
    phase: AuctionPhase.fromSlug(phase),
    state: VehicleState.fromSlug(state),
    isFavourite: isFavourite,
    auctionEndsAt: auctionEndsAt.toUtc(),
  );

  /// المواصفات من حقول الكرت نفسها.
  ///
  /// الخادم لا يرسل قائمة `specifications` — يرسل الحقول وتسمياتها المعروضة
  /// (`colour_label`، `condition_label`). فالقيمة من الخادم دائماً، واسمُ
  /// الحقل نصُّ واجهةٍ يأتي من المتصل بهذه الدالة عبر `labels`.
  List<VehicleSpecification> specifications(VehicleSpecificationLabels labels) {
    final rows = <VehicleSpecification>[
      VehicleSpecification(label: labels.make, value: make),
      VehicleSpecification(label: labels.model, value: model),
      VehicleSpecification(label: labels.year, value: '$year'),
      VehicleSpecification(label: labels.colour, value: colourLabel),
      VehicleSpecification(label: labels.condition, value: conditionLabel),
    ];
    // الممشى قد يغيب، والغياب لا يُعرض صفراً: «٠ كم» ادّعاءٌ لم يقله أحد.
    final odometer = odometerKm;
    if (odometer != null) {
      rows.add(
        VehicleSpecification(label: labels.odometer, value: '$odometer'),
      );
    }
    if (location.isNotEmpty) {
      rows.add(VehicleSpecification(label: labels.location, value: location));
    }
    return List<VehicleSpecification>.unmodifiable(rows);
  }
}

/// أسماء حقول المواصفات، من ملف الترجمة لا من هذه الطبقة.
///
/// تُمرَّر بدل أن تُكتب هنا لأن النصّ المعروض شأنُ الواجهة (المادة ٣-٣: لا نصّ
/// عربيّ مكتوب داخل طبقةٍ غير طبقة العرض).
final class VehicleSpecificationLabels {
  const VehicleSpecificationLabels({
    required this.make,
    required this.model,
    required this.year,
    required this.colour,
    required this.condition,
    required this.odometer,
    required this.location,
  });

  final String make;
  final String model;
  final String year;
  final String colour;
  final String condition;
  final String odometer;
  final String location;
}

extension PhaseCountsMapper on api.PhaseCounts {
  domain.PhaseCounts toDomain() =>
      domain.PhaseCounts(upcoming: soon, active: active, ended: ended);
}

extension VehicleFeedMapper on api.VehiclePage {
  domain.VehicleFeed toDomain() => domain.VehicleFeed(
    page: domain.VehiclePage(
      vehicles: results.map((card) => card.toDomain()).toList(growable: false),
      totalCount: total,
      // «هل من مزيد؟» — الخادم يرسل الإجمالي، فالمزيد هو ما لم يصل بعد.
      // حسابُه من طول القائمة وحجم الصفحة تخمينٌ يخطئ في آخر صفحة ممتلئة.
      hasMore: results.length < total,
    ),
    counts: counts.toDomain(),
  );

  domain.VehiclePage toPage() => domain.VehiclePage(
    vehicles: results.map((card) => card.toDomain()).toList(growable: false),
    totalCount: total,
    hasMore: results.length < total,
  );
}

extension VehicleImagesMapper on api.VehicleImages {
  /// روابط العرض بترتيبها، والغلاف أولاً كما رتّبه الخادم.
  ///
  /// `preview_url` لا `thumbnail_url`: هذه صفحة المركبة لا الكرت. والصورة بلا
  /// رابطٍ تُسقَط ولا تصير سلسلةً فارغة تحاول الشاشة تحميلها.
  List<String> toDomain() => List<String>.unmodifiable(
    results
        .map((image) => image.previewUrl ?? image.thumbnailUrl)
        .whereType<String>(),
  );
}

/// عملة النظام — ريال سعودي.
///
/// **الخادم لا يرسل عملةً مع كل مبلغ**، ولا يجب: النظام كلّه بعملةٍ واحدة،
/// وحملُها على كل حقلٍ يوحي بأن ثمّة ثانية. تُكتب هنا مرّةً، وتُقرأ من
/// `Money` في كل شاشة — فيوم تُضاف عملة ثانية يكون التغيير في العقد لا في
/// ثلاثين موضعاً.
const String _currency = 'SAR';
