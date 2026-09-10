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
    this.trailing,
    this.header,
    this.pinnedHeader,
    this.pinnedHeaderExtent = 0,
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

  /// ما يعلو القائمة **وينزلق معها** — لوحةُ الترحيب وحقلُ البحث ومفتاحُ
  /// الأطوار في الرئيسية.
  ///
  /// **داخل `CustomScrollView` لا فوقه**: كان ثلاثتُها ثابتةً في عمودٍ فوق
  /// القائمة، فتأكل من الشاشة القصيرة نحو مئةٍ وأربعين بكسلاً **في كل
  /// تمريرة** — ولا يبقى للسيّارات إلا كرتان. وv1 تُنزلقها، فطلب المالك
  /// مثلَها في ٩ سبتمبر ٢٠٢٦.
  ///
  /// و`null` في بقيّة الشاشات: لا شيء فوق قوائمها ينزلق.
  final Widget? header;

  /// ما يعلو القائمة **ويثبت فوقها** حين تنزلق — حقلُ البحث ومفتاحُ الأطوار.
  ///
  /// **ثابتٌ لا منزلق** بطلب المالك في ٩ سبتمبر ٢٠٢٦: هما مقبضا القائمة، ومن
  /// نزل عشرين كرتاً ثم أراد تبديل الطور كان عليه أن يصعد كلَّها. ولوحةُ
  /// الترحيب فوقهما تنزلق لأنها تُقرأ مرّةً ولا تُستعمل.
  final Widget? pinnedHeader;

  /// ارتفاعُ `pinnedHeader` بالضبط — `SliverPersistentHeader` يفرضه ولا
  /// يقيسه، فالمكوّنُ يُبنى بارتفاعٍ مضبوطٍ في الشاشة المضيفة ويُمرَّر معه.
  final double pinnedHeaderExtent;

  /// كم مركبة قبل نهاية القائمة نطلب الصفحة التالية.
  final int prefetchThreshold;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final theme = Theme.of(context);
    final palette = HarajPalette.of(context);

    return CustomScrollView(
      slivers: <Widget>[
        if (header case final Widget widget) SliverToBoxAdapter(child: widget),
        if (pinnedHeader case final Widget widget)
          SliverPersistentHeader(
            pinned: true,
            delegate: _PinnedHeader(
              extent: pinnedHeaderExtent,
              // **أرضيّةٌ معتمة**: الشريحةُ الثابتة تقف فوق الكروت وهي
              // تمرّ تحتها، وبلا أرضيّةٍ تُقرأ الكروتُ من خلال حقل البحث.
              //
              // وبلون الصفحة لا بيضاء: جُرِّبت البيضاء في ١٠ سبتمبر ٢٠٢٦
              // ورُدَّت — الشريحةُ ليست بطاقةً فوق الصفحة، هي الصفحةُ نفسها
              // ثابتةً.
              child: ColoredBox(color: palette.pageBackground, child: widget),
            ),
          ),
        // **الفراغُ شريحةٌ لا خروجٌ مبكّر**: كان `return Center` قبل بناء
        // القائمة، فيأخذ معه الترويسةَ — ومن بحث عن كلمةٍ لم تطابق كان يفقد
        // حقلَ بحثه فلا يستطيع تصحيحها.
        if (vehicles.isEmpty)
          SliverFillRemaining(
            hasScrollBody: false,
            child: Padding(
              padding: const EdgeInsets.all(24),
              child: Center(
                child: Text(emptyMessage, textAlign: TextAlign.center),
              ),
            ),
          ),
        if (vehicles.isNotEmpty && (showCount || trailing != null))
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
        if (vehicles.isNotEmpty) _cards(),
        if (vehicles.isNotEmpty) SliverToBoxAdapter(child: _tail()),
        // مكانُ الشريط السفليّ، من `MediaQuery` لا رقماً مكتوباً: القشرة هي
        // التي تعرف ارتفاعه، وتضيفه إلى الحشوة. بلا هذا يقع آخر صفٍّ تحته
        // فيُقرأ نصفه.
        SliverToBoxAdapter(
          child: SizedBox(height: MediaQuery.paddingOf(context).bottom),
        ),
      ],
    );
  }

  /// الكروتُ: عمودٌ واحد على الجوّال، وثلاثةٌ جنباً إلى جنب على اللوح
  /// والحاسوب — بطلب المالك في ٩ سبتمبر ٢٠٢٦.
  ///
  /// **`SliverLayoutBuilder` لا `MediaQuery`**: المقياسُ هو عرضُ القائمة نفسها
  /// لا عرضُ النافذة — والقائمةُ قد تقف في عمودٍ نصفَ الشاشة، فعرضُ النافذة
  /// يقول «ثلاثة» حيث لا يسع إلا واحد.
  ///
  /// **وحدٌّ أقصى للعمود لا عددٌ مكتوب**: `440` هو حدُّ الكرت نفسه، فالعمودُ لا
  /// يتمدّد أوسع منه مهما اتّسعت الشاشة، والعددُ يخرج من القسمة — أربعةٌ على
  /// شاشةٍ أعرض، بلا سطرٍ يُكتب.
  ///
  /// **والارتفاعُ مفروضٌ في الشبكة** (`mainAxisExtent`) لأن الشبكةَ لا تقيس
  /// أبناءَها: ١٧٢ هي حدُّ الكرت الأدنى (١٤٤) وحشوتُه (٥+٥) وثمانيةَ عشرَ
  /// احتياطاً لخطٍّ أكبر في إعدادات الجهاز.
  Widget _cards() => SliverLayoutBuilder(
    builder: (context, constraints) {
      final columns = (constraints.crossAxisExtent / _maxColumnWidth).floor();
      if (columns < 2) {
        return SliverList.builder(
          itemCount: vehicles.length,
          itemBuilder: _buildCard,
        );
      }
      return SliverGrid.builder(
        gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
          crossAxisCount: columns,
          mainAxisExtent: _cardExtent,
          // **فاصلٌ بين الصفوف**: حشوةُ الكرت الرأسيّة (٥+٥) وحدها تترك
          // عشرةَ بكسلات بين صفَّين، فتُقرأ الصفوفُ شبكةً ملتصقة لا كروتاً.
          mainAxisSpacing: 12,
        ),
        itemCount: vehicles.length,
        itemBuilder: _buildCard,
      );
    },
  );

  Widget _buildCard(BuildContext context, int index) {
    if (hasMore &&
        index >= vehicles.length - prefetchThreshold &&
        !loadingMore &&
        moreFailure == null) {
      WidgetsBinding.instance.addPostFrameCallback((_) => onLoadMore());
    }

    final vehicle = vehicles[index];
    // **بلا `onTap`**: الكرتُ يفتح صندوقَ المزايدة بنفسه منذ حُذفت صفحةُ
    // المركبة في ٩ سبتمبر ٢٠٢٦، فلا وجهةَ تُمرَّر إليه من الشاشة المضيفة.
    return VehicleCard(key: ValueKey<String>(vehicle.id), vehicle: vehicle);
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

/// شريحةٌ ثابتة بارتفاعٍ واحد لا يتغيّر بالتمرير.
///
/// `min` و`max` متساويان: ترويسةٌ تنكمش تحتاج تخطيطاً يتجاوب مع الانكماش،
/// وحقلُ بحثٍ نصفُ ارتفاعه ليس حقلَ بحث.
class _PinnedHeader extends SliverPersistentHeaderDelegate {
  const _PinnedHeader({required this.extent, required this.child});

  final double extent;
  final Widget child;

  @override
  double get minExtent => extent;

  @override
  double get maxExtent => extent;

  @override
  Widget build(
    BuildContext context,
    double shrinkOffset,
    bool overlapsContent,
  ) => SizedBox.expand(child: child);

  @override
  bool shouldRebuild(_PinnedHeader oldDelegate) =>
      oldDelegate.extent != extent || oldDelegate.child != child;
}

/// أوسعُ ما يبلغه عمودٌ واحد من الكروت — حدُّ الكرت نفسه.
const double _maxColumnWidth = 440;

/// ارتفاعُ خليّة الشبكة.
///
/// كان ١٧٢ — حدُّ الكرت الأدنى (١٤٤) وحشوتُه (١٠) واحتياطٌ يسير. ورُفع إلى
/// ١٩٢ بطلب المالك في ٩ سبتمبر ٢٠٢٦: الكرتُ على اللوح أوسع، فصورتُه أوسع،
/// فارتفاعٌ يساوي ارتفاعَ الجوّال يجعله مفلطحاً.
const double _cardExtent = 192;
