import 'vehicle_summary.dart';

/// معايير البحث والترشيح والصفحة — **تُرسَل إلى الخادم**، ولا تُطبَّق هنا.
///
/// لماذا لا ترشيح في التطبيق: نتيجةٌ يحسبها التطبيق تختلف عن نتيجة الويب لنفس
/// المعايير، فيسأل العميل «ليه الموقع لقى أربع سيارات والتطبيق لقى اثنتين؟»
/// ولا جواب. الحقول هنا هي بعينها مُعاملات الاستعلام التي يعلنها العقد.
final class VehicleQuery {
  const VehicleQuery({
    this.search,
    this.make,
    this.yearFrom,
    this.yearTo,
    this.page = 1,
  });

  final String? search;
  final String? make;
  final int? yearFrom;
  final int? yearTo;

  /// الصفحة تبدأ من 1 كما يعدّها العقد.
  final int page;

  bool get isFiltered =>
      (search?.isNotEmpty ?? false) ||
      (make?.isNotEmpty ?? false) ||
      yearFrom != null ||
      yearTo != null;

  /// الصفحة الأولى بلا ترشيح — الطلب الوحيد الذي يبقى جوابه ذا معنى بلا خادم،
  /// فهو وحده ما يُحفظ في الكاش. صفحةٌ ثالثة من بحثٍ قديم ليست «آخر ما نعرف»،
  /// وعرضها بلا اتصال يجيب عن سؤال لم يُسأل.
  bool get isFirstUnfilteredPage => page == 1 && !isFiltered;

  VehicleQuery atPage(int page) => VehicleQuery(
    search: search,
    make: make,
    yearFrom: yearFrom,
    yearTo: yearTo,
    page: page,
  );
}

/// صفحة نتائج كما ردّ بها الخادم.
final class VehiclePage {
  const VehiclePage({
    required this.vehicles,
    required this.totalCount,
    required this.hasMore,
  });

  final List<VehicleSummary> vehicles;

  /// العدد الكلي **من الخادم**، لا `vehicles.length`: الأول يجيب «كم مركبة
  /// طابقت؟» والثاني «كم وصلني في هذه الصفحة؟»، وخلطهما يجعل قائمةً من مئتي
  /// مركبة تقول «٢٠ نتيجة».
  final int totalCount;

  /// هل بعد هذه الصفحة صفحة؟ من `next` في الاستجابة، لا من حسابٍ هنا على
  /// طول القائمة وحجم الصفحة.
  final bool hasMore;
}
