import 'package:flutter/material.dart';

import '../../../app/theme.dart';
import '../../../domain/catalog/entities/vehicle_summary.dart';
import '../../../domain/common/failure.dart';
import '../../../l10n/generated/app_localizations.dart';
import '../../common/failure_view.dart';
import 'vehicle_card.dart';

/// نتائج المركبات المرقَّمة — **مصفوفة الكروت وحدها**، لا جلبها.
///
/// من أين تأتي الصفحات قرارُ الشاشة المضيفة (مركبات مزادٍ بعينه، أو الشبكة
/// المسطّحة عبر المزادات بتبويب الطور). وما يُعرض ويُطلب بعده واحد.
///
/// **عمودٌ واحد في كل مكان، ولا شبكة.** كان هنا `VehicleResultsLayout` بوضعين،
/// والرئيسيّةُ والمفضلةُ تطلبان الشبكة. وكرتُ المركبة صار **صفّاً** — صورةٌ في
/// جهة وبياناتٌ في الأخرى — وصفٌّ داخل خليّة شبكةٍ عرضُها مئتا بكسل يصير كرتاً
/// ثالثاً بهيئةٍ ثالثة. فحُذف الوضعان: هيئةٌ واحدة للكرت تعني مصفوفةً واحدة له
/// (المادة ٤-٥).
///
/// **كسولٌ:** `SliverList.builder` يبني العنصر عند ظهوره، فمئتا مركبة لا تعني
/// مئتي كرت ولا مئتي تنزيل — وهو نصف معيار H2.
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
    this.trailing,
    this.showCount = true,
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

  /// ما يقف في الطرف الآخر من سطر العدّ — زرّ الفرز في الرئيسية.
  ///
  /// **في هذا السطر لا فوقه:** سطرُ العدّ وزرُّ الفرز جوابان عن سؤالٍ واحد
  /// («كم، وكيف رتّبتها؟»)، وسطرٌ ثالث لأحدهما يأكل من ارتفاع الشاشة كرتاً
  /// كاملاً. و`null` في بقيّة الشاشات: المفضلة لا تُفرَز، وقائمةُ مزادٍ بعينه
  /// مفروزةٌ برقم اللوت أصلاً.
  final Widget? trailing;

  /// هل يُعرض سطر «كذا نتيجة» فوق القائمة.
  ///
  /// **مفتاحٌ لا حذفٌ من المكوّن**: المفضلة وقائمةُ مزادٍ بعينه ما زالتا
  /// تعرضانه، ورُفع من الرئيسية وحدها بطلب المالك في ٩ سبتمبر ٢٠٢٦ — فوقه
  /// مفتاحُ الأطوار وعدّاداتُه الثلاثة، والرقمُ الرابع تحتها يكرّر أحدها.
  ///
  /// وحين يسقط السطرُ ولا `trailing` معه **يسقط شريطُه كلُّه**، لا يبقى
  /// فارغاً: حشوةٌ بثمانية بكسلات فوق أول كرتٍ بلا شيء فيها.
  final bool showCount;

  /// كم مركبة قبل نهاية القائمة نطلب الصفحة التالية.
  final int prefetchThreshold;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final theme = Theme.of(context);
    final palette = HarajPalette.of(context);

    if (vehicles.isEmpty) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Text(emptyMessage, textAlign: TextAlign.center),
        ),
      );
    }

    return CustomScrollView(
      slivers: <Widget>[
        if (showCount || trailing != null)
          SliverToBoxAdapter(
            child: Padding(
              padding: const EdgeInsets.fromLTRB(20, 6, 20, 2),
              child: Row(
                children: <Widget>[
                  if (showCount)
                    Expanded(
                      child: Text(
                        // العدد الكلي من الخادم، لا طول ما وصل: قائمةٌ من مئتي
                        // مركبة عُرض منها عشرون تقول «مئتان»، لا «عشرون».
                        l10n.vehiclesResultsCount(totalCount),
                        style: theme.textTheme.bodyMedium?.copyWith(
                          color: palette.inkMuted,
                          fontWeight: FontWeight.w500,
                        ),
                      ),
                    )
                  else
                    const Spacer(),
                  if (trailing case final Widget widget) widget,
                ],
              ),
            ),
          ),
        SliverList.builder(itemCount: vehicles.length, itemBuilder: _buildCard),
        SliverToBoxAdapter(child: _tail()),
        // مكانُ الشريط السفليّ، من `MediaQuery` لا رقماً مكتوباً: القشرة هي
        // التي تعرف ارتفاعه، وتضيفه إلى الحشوة. بلا هذا يقع آخر صفٍّ تحته
        // فيُقرأ نصفه.
        SliverToBoxAdapter(
          child: SizedBox(height: MediaQuery.paddingOf(context).bottom),
        ),
      ],
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
