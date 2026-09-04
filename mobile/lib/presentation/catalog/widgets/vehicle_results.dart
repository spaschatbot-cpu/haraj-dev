import 'package:flutter/material.dart';

import '../../../domain/catalog/entities/vehicle_summary.dart';
import '../../../domain/common/failure.dart';
import '../../../l10n/generated/app_localizations.dart';
import '../../common/failure_view.dart';
import 'vehicle_card.dart';

/// كيف تُصفّ الكروت: عموداً واحداً في قائمة مزادٍ بعينه، أو شبكةً في الرئيسية.
///
/// التخطيط وحده هو الفرق. كل ما عداه — عدّ النتائج، وطلب الصفحة التالية قبل
/// النهاية، وفشل الصفحة التالية بلا محو ما وصل، والحالة الفارغة — واحدٌ في
/// الاثنتين، ولذلك يعيش في ملف واحد: نسختان منه تفترقان عند أول إصلاح يُنسى
/// في إحداهما (المادة ٤-٥).
enum VehicleResultsLayout { list, grid }

/// نتائج المركبات المرقَّمة — **مصفوفة الكروت وحدها**، لا جلبها.
///
/// من أين تأتي الصفحات قرارُ الشاشة المضيفة (مركبات مزادٍ بعينه، أو الشبكة
/// المسطّحة عبر المزادات بتبويب الطور). وما يُعرض ويُطلب بعده واحد.
///
/// **كسولٌ في الحالتين:** `SliverList.builder` و`SliverGrid.builder` يبنيان
/// العنصر عند ظهوره، فمئتا مركبة لا تعني مئتي كرت ولا مئتي تنزيل — وهو نصف
/// معيار H2، ويقيسه `test/presentation/auction_vehicles_performance_test.dart`.
class VehicleResults extends StatelessWidget {
  const VehicleResults({
    required this.vehicles,
    required this.totalCount,
    required this.hasMore,
    required this.loadingMore,
    required this.moreFailure,
    required this.onLoadMore,
    required this.onRetryMore,
    required this.emptyMessage,
    required this.onOpenVehicle,
    this.layout = VehicleResultsLayout.list,
    this.prefetchThreshold = 3,
    super.key,
  });

  final List<VehicleSummary> vehicles;

  /// العدد الكلي من الخادم، لا `vehicles.length`.
  final int totalCount;

  final bool hasMore;
  final bool loadingMore;
  final Failure? moreFailure;
  final VoidCallback onLoadMore;
  final VoidCallback onRetryMore;

  /// **لماذا يُمرَّر النصّ الفارغ ولا يُكتب هنا:** «فارغ» ليس معنى واحداً.
  /// «لا مركبات مطابقة» جوابُ بحثٍ لم يطابق، و«لا مزاد نشط الآن» خبرٌ عن
  /// المزادات لا عن البحث. نصٌّ واحد لهما يقول للعميل الشيء الخطأ في أحدهما.
  final String emptyMessage;

  final void Function(VehicleSummary vehicle) onOpenVehicle;

  final VehicleResultsLayout layout;

  /// كم مركبة قبل نهاية القائمة نطلب الصفحة التالية.
  final int prefetchThreshold;

  /// العرض المستهدَف لعمود في الشبكة، وارتفاع الخليّة.
  ///
  /// **لماذا عددُ الأعمدة يُقرَّب ولا يُقصّ:** خليّة الشبكة ارتفاعها ثابت،
  /// وارتفاع الكرت ليس دالّةً مطّردة في عرضه — كلما ضاق العمود انكسر نصّ السعر
  /// إلى أسطر أكثر فطال الكرت، وكلما اتّسع كبرت الصورة (4:3) فطال أيضاً. القياس
  /// على الكرت نفسه: عمود 100 يحتاج 631، و134 يحتاج 457، و195 يحتاج 390،
  /// و320 يحتاج 440. فالسلامة ليست في اختيار ارتفاعٍ كبير، بل في **حصر عرض
  /// العمود** في نطاقٍ ضيّق حول أدنى نقطة في المنحنى.
  ///
  /// التقريب يُبقي العمود بين 160 و250 عند كل عرض شاشةٍ نشحن إليه، وأعلى ما
  /// يطلبه الكرت في ذلك النطاق 416 — والسقف أدناه فوقه بقليل. فراغٌ صغير أسفل
  /// الكرت أهون من تجاوزٍ يقصّ السعر.
  static const double _gridTargetColumnWidth = 200;
  static const double _gridMainAxisExtent = 420;

  static int _columnsFor(double width) {
    final columns = (width / _gridTargetColumnWidth).round();
    return columns < 1 ? 1 : columns;
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);

    if (vehicles.isEmpty) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Text(emptyMessage, textAlign: TextAlign.center),
        ),
      );
    }

    return LayoutBuilder(
      builder: (context, constraints) => CustomScrollView(
        slivers: <Widget>[
          SliverToBoxAdapter(
            child: Padding(
              padding: const EdgeInsets.fromLTRB(16, 12, 16, 4),
              child: Text(
                // العدد الكلي من الخادم، لا طول ما وصل: قائمةٌ من مئتي مركبة
                // عُرض منها عشرون تقول «مئتان»، لا «عشرون».
                l10n.vehiclesResultsCount(totalCount),
                style: Theme.of(context).textTheme.bodySmall,
              ),
            ),
          ),
          switch (layout) {
            VehicleResultsLayout.list => SliverList.builder(
              itemCount: vehicles.length,
              itemBuilder: _buildCard,
            ),
            VehicleResultsLayout.grid => SliverGrid.builder(
              gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
                crossAxisCount: _columnsFor(constraints.maxWidth),
                mainAxisExtent: _gridMainAxisExtent,
              ),
              itemCount: vehicles.length,
              itemBuilder: _buildCard,
            ),
          },
          SliverToBoxAdapter(child: _tail()),
        ],
      ),
    );
  }

  Widget _buildCard(BuildContext context, int index) {
    if (hasMore &&
        index >= vehicles.length - prefetchThreshold &&
        !loadingMore &&
        moreFailure == null) {
      WidgetsBinding.instance.addPostFrameCallback((_) => onLoadMore());
    }

    final vehicle = vehicles[index];
    return VehicleCard(
      key: ValueKey<String>(vehicle.id),
      vehicle: vehicle,
      onTap: () => onOpenVehicle(vehicle),
    );
  }

  Widget _tail() {
    final failure = moreFailure;
    if (failure != null) {
      // فشل صفحةٍ تالية لا يمحو ما وصل: يبقى المعروض معروضاً ويظهر الخطأ في
      // ذيل القائمة بزرّ إعادة محاولة.
      return FailureView(failure: failure, onRetry: onRetryMore);
    }
    if (!hasMore) return const SizedBox.shrink();
    return const Padding(
      padding: EdgeInsets.all(16),
      child: Center(child: CircularProgressIndicator()),
    );
  }
}
