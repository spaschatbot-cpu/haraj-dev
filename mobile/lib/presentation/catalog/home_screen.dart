import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../app/providers.dart';
import '../../app/router.dart';
import '../../app/theme.dart';
import '../../domain/catalog/entities/auction_phase.dart';
import '../../domain/catalog/entities/vehicle_feed.dart';
import '../../domain/catalog/entities/vehicle_query.dart';
import '../../domain/catalog/entities/vehicle_summary.dart';
import '../../domain/common/failure.dart';
import '../../domain/common/snapshot.dart';
import '../../l10n/generated/app_localizations.dart';
import '../common/snapshot_view.dart';
import 'widgets/home_hero.dart';
import 'widgets/vehicle_filters.dart';
import 'widgets/vehicle_results.dart';

/// الرئيسية: **قائمة مركبات مسطّحة عبر المزادات، تحت لوحة فتحٍ داكنة.**
///
/// المزاد واحد في الأسبوع وحالته تتغيّر، فالسؤال الذي يفتح به العميل التطبيق
/// ليس «أي المزادات موجود؟» بل «إيش المعروض دلوقتي؟». ولذلك حلّت المركبات محلّ
/// قائمة المزادات، وصار الطور عملياً هو «أي مزادٍ أنظر إليه الآن».
///
/// **القسمة والعدّ من الخادم.** الطور يأتي في `phase` لكل مركبة، والعدّادات
/// الثلاثة تأتي مع الصفحة في **طلبٍ واحد**. لا الشاشة تصنّف مزاداً بنفسها، ولا
/// تعدّ الأطوار من طول القائمة: في v1 كانت الأرقام الثلاثة تُطلب في ستّة
/// طلبات، فيصير كل رقم من لحظة، ويقع التبويب على «٣» ثم يُفتح فيه صفر.
///
/// **الطور في العنوان** (`?phase=active`) لا في حالة الشاشة وحدها: الرابط
/// يُشارَك، ويصمد عبر إعادة الفتح، ويفتحه الإشعار على طوره (H6). ومقبضُه
/// انتقل من شريط تبويباتٍ أسفل الهيدر إلى ورقة «الفرز والتصفية» — نفس
/// المسار، بلا صفٍّ ثالث يأكل من الشاشة.
///
/// **ولا `AppBar` هنا.** بقيّة الشاشات تحمل `HarajAppBar` الأخضر؛ وهذه وحدها
/// تحمل `HomeHero` — والسبب مكتوب عنده.
class HomeScreen extends ConsumerStatefulWidget {
  const HomeScreen({this.phase = AuctionPhase.defaultTab, super.key});

  /// الطور المعروض — يقرؤه جدول المسارات من `?phase=` ويمرّره.
  final AuctionPhase phase;

  @override
  ConsumerState<HomeScreen> createState() => _HomeScreenState();
}

/// ارتفاعُ حقل البحث داخل صندوق البحث.
const double _searchHeight = 48;

/// حاشيةُ صندوق البحث العلويّة.
///
/// **عشرةٌ** بطلب المالك (١٣ سبتمبر ٢٠٢٦): هي الفراغُ فوق الحقل حين تثبت
/// الشريحةُ في رأس الشاشة — بصفرٍ كان يلتصق بالحافّة. ولا يُفقَد التراكبُ
/// على الصورة: `_searchOverlap` زِيد بقدرها.
const double _searchCardTop = 10;

/// ارتفاعُ الشريحة المثبَّتة **بالضبط** — `SliverPersistentHeader` يفرضه ولا
/// يقيسه، فأيُّ زيادةٍ في محتواه تفيض وتُقصّ. وهو مجموعُ ما فيه:
/// الحاشيةُ العلويّة + حقلُ البحث + الفاصلُ + حاويةُ التبويبات (٤٢).
const double _searchCardExtent =
    _searchCardTop + _searchHeight + 12 + 42 + _searchCardBottom;

/// فراغٌ أسفل التبويبات قبل أول كرت — بطلب المالك (١٣ سبتمبر ٢٠٢٦): كانت
/// حاويةُ الأطوار تلامس حافّة الكرت الأول فتُقرأان كتلةً واحدة.
const double _searchCardBottom = 10;

/// ارتفاعُ اللوحة الغنيّة **بلا** حاشية النظام العلويّة — تُضاف في البناء.
///
/// مكتوبٌ لا مقيس، لأن `SliverPersistentHeader` يفرض ارتفاعه: حاشيةٌ علويّة
/// (١٢) + صفُّ العلامة (٣٦ بعد أن حلّ الشعارُ محلّ الأيقونة) + فاصلٌ (١٠) +
/// سطرُ التمهيد (١٣) + فاصلٌ (٦) + العنوان (١٨) + حاشيةٌ سفلى (٢٦)، وبكسلان
/// احتياطاً.
///
/// **والرقمُ يُراجَع مع كل تغييرٍ في محتوى اللوحة**: الشريحةُ تفرض ارتفاعها
/// ولا تقيسه، فبكسلان ناقصان يُخرجان شريطَ الفيضان الأصفر — وهو ما حدث حين
/// كبُر صفُّ العلامة من ٣٤ إلى ٣٦ (١٤ سبتمبر ٢٠٢٦).
const double _heroExtent = 124;

/// العرضُ الذي تنقلب عنده الترويسة إلى صفٍّ واحد.
///
/// **٨٦٠**: دون ذلك لا يسع الصفُّ نصَّ اللوحة وصندوقَ بحثٍ بعرض ٤٤٠ معاً.
const double _wideAt = 860;

/// ارتفاعُ ترويسة اللاب — صفُّ العلامة والنصُّ، وصندوقُ البحث والتبويبات
/// فوق الصورة. رُفع إلى ٢١٦ حين نزل العنوانُ وكبُر خطُّه.
const double _wideHeaderExtent = 216;

/// فراغٌ بين أسفل الصورة وأول صفٍّ من الكروت على اللاب — بطلب المالك: كانت
/// الكروتُ تلتصق بحافّة الصورة فتُقرأ امتداداً لها.
const double _wideHeaderGap = 16;

/// كم يعلو صندوقُ البحث على أسفل صورة اللوحة، على موكاب المالك.
///
/// ويتلاشى مع الانطواء: بلا تلاشٍ يبقى شريطٌ شفّافٌ بعرض عشرين فوق الشريحة
/// المثبَّتة، تظهر فيه الكروتُ وهي تمرّ من خلف الحقل.
const double _searchOverlap = 30;

class _HomeScreenState extends ConsumerState<HomeScreen> {
  VehicleQuery _query = const VehicleQuery();
  AsyncValue<Snapshot<VehicleFeed>> _first =
      const AsyncValue<Snapshot<VehicleFeed>>.loading();

  final List<VehicleSummary> _vehicles = <VehicleSummary>[];
  int _totalCount = 0;
  bool _hasMore = false;
  bool _loadingMore = false;
  Failure? _moreFailure;

  /// كل طلبٍ جديد يبطل ما قبله: ردٌّ بطيء لطورٍ غادره العميل كان سيصل بعد ردّ
  /// الطور الذي يقف فيه فيدهسه، فيرى مركبات طورٍ آخر تحت عنوان طوره.
  int _generation = 0;

  /// آخر عدّادات وصلت — رقمُ كل تبويب. تبقى معروضة أثناء تحميل الطور التالي
  /// بدل أن تختفي الأرقام ثم تعود: وميضٌ يجعل الخانات الثلاث ترقص عند كل
  /// ضغطة.
  PhaseCounts? _counts;

  @override
  void initState() {
    super.initState();
    _reload();
  }

  @override
  void didUpdateWidget(HomeScreen oldWidget) {
    super.didUpdateWidget(oldWidget);
    // الطور تغيّر من العنوان (اختيارٌ في الورقة، أو رجوع، أو رابط). المعايير
    // تبقى: من بحث عن «كامري» ثم بدّل الطور يسأل عن كامري في الطور الجديد،
    // لا يبدأ من الصفر.
    if (oldWidget.phase != widget.phase) _reload();
  }

  Future<void> _reload() async {
    final generation = ++_generation;
    setState(() {
      _first = const AsyncValue<Snapshot<VehicleFeed>>.loading();
      _moreFailure = null;
      _loadingMore = false;
    });

    try {
      final snapshot = await ref.read(loadVehicleFeedProvider)(
        _query.inPhase(widget.phase),
      );
      if (!mounted || generation != _generation) return;
      setState(() {
        _query = _query.atPage(1);
        _first = AsyncValue<Snapshot<VehicleFeed>>.data(snapshot);
        _vehicles
          ..clear()
          ..addAll(snapshot.value.page.vehicles);
        _totalCount = snapshot.value.page.totalCount;
        _hasMore = snapshot.value.page.hasMore;
        _counts = snapshot.value.counts;
      });
    } on Object catch (error, stackTrace) {
      // `Object` لا `Failure`: عطبٌ غير متوقّع يجب أن يظهر مصنَّفاً في الشاشة،
      // لا أن يُفلت من فجوة غير متزامنة فيسقط في السجلّ وحده والشاشة تدور.
      if (!mounted || generation != _generation) return;
      setState(
        () =>
            _first = AsyncValue<Snapshot<VehicleFeed>>.error(error, stackTrace),
      );
    }
  }

  Future<void> _loadMore() async {
    if (_loadingMore || !_hasMore || _moreFailure != null) return;
    final generation = _generation;
    setState(() => _loadingMore = true);

    final next = _query.page + 1;
    try {
      final snapshot = await ref.read(loadVehicleFeedProvider)(
        _query.inPhase(widget.phase).atPage(next),
      );
      if (!mounted || generation != _generation) return;
      setState(() {
        _query = _query.atPage(next);
        _vehicles.addAll(snapshot.value.page.vehicles);
        _totalCount = snapshot.value.page.totalCount;
        _hasMore = snapshot.value.page.hasMore;
        // العدّادات تُحدَّث مع كل صفحة لأنها تصل معها: رقمٌ من الصفحة الأولى
        // يبقى معروضاً بينما الصفحة الثالثة تعرف رقماً أحدث كذبةٌ مجانية.
        _counts = snapshot.value.counts;
        _loadingMore = false;
      });
    } on Object catch (error, stackTrace) {
      if (!mounted || generation != _generation) return;
      setState(() {
        _moreFailure = error is Failure
            ? error
            : UnexpectedFailure(error, stackTrace: stackTrace);
        _loadingMore = false;
      });
    }
  }

  void _apply(VehicleQuery query) {
    setState(() => _query = query.inPhase(widget.phase));
    _reload();
  }

  void _search(String text) => _apply(
    VehicleQuery(
      search: text.trim(),
      make: _query.make,
      yearFrom: _query.yearFrom,
      yearTo: _query.yearTo,
    ),
  );

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);

    return AnnotatedRegion<SystemUiOverlayStyle>(
      // ساعةُ النظام وبطّاريّتُه فوق لوحةٍ داكنة: تُركا للثيم الفاتح كانا
      // سيُرسمان أسودَين على أسود.
      value: SystemUiOverlayStyle.light,
      child: Scaffold(
        // **الهيدرُ ينزلق والبحثُ يثبت** بطلب المالك (١٣ سبتمبر ٢٠٢٦، على
        // سلوك v1): اللوحةُ الغنيّة شريحةٌ أولى تمضي إلى أعلى مع الكروت،
        // وصندوقُ البحث والتبويبات شريحةٌ **مثبَّتة** تبقى فوق القائمة — فهما
        // مقبضاها، ومن نزل عشرين كرتاً ثم أراد تبديل الطور لا يصعد كلَّها.
        //
        // وبهذا ذهبت الورقةُ الكريميّة ذاتُ الزاويتين المدوّرتين: كانت تحيط
        // بعمودٍ ثابتٍ فوق القائمة، ولا عمودَ الآن. وحافّةُ الهيدر السفلى
        // مدوّرةٌ أصلاً (`HomeHero`) فلا يُفقَد شيءٌ من الشكل.
        body: SnapshotView<VehicleFeed>(
          state: _first,
          onRetry: _reload,
          builder: (context, snapshot) => VehicleResults(
            vehicles: _vehicles,
            totalCount: _totalCount,
            hasMore: _hasMore,
            loadingMore: _loadingMore,
            moreFailure: _moreFailure,
            onLoadMore: _loadMore,
            onRetryMore: () {
              setState(() => _moreFailure = null);
              _loadMore();
            },
            emptyMessage: _emptyMessage(l10n),
            showCount: false,
            // **هيئتان للترويسة**: على الجوّال شريحةٌ تنطوي — اللوحةُ تنزلق
            // وصندوقُ البحث يثبت. وعلى اللاب صفٌّ واحد: النصُّ يميناً
            // وصندوقُ البحث والتبويبات شمالاً داخل الصورة، على هيئة v1
            // (بطلب المالك، ١٣ سبتمبر ٢٠٢٦) — ولا تثبيتَ هناك لأن الشاشة
            // العريضة لا يضيق بها الطول.
            sliverHeader: MediaQuery.sizeOf(context).width >= _wideAt
                ? SliverToBoxAdapter(child: _wideHeader(context))
                : SliverPersistentHeader(
                    pinned: true,
                    delegate: _HomeHeader(
                      palette: HarajPalette.of(context),
                      heroExtent:
                          _heroExtent + MediaQuery.paddingOf(context).top,
                      card: _searchCard(),
                      hero: HomeHero(
                        onOpenNotifications: () =>
                            context.go(Routes.myActivityPath),
                        onOpenAccount: () => context.go(Routes.profilePath),
                      ),
                    ),
                  ),
            // **لا زرّ فرزٍ ولا ورقة تصفية** — مُحي بطلب المالك في ٩ سبتمبر
            // ٢٠٢٦، مرّتين: من سطر العدّ أوّلاً، ثم من جانب حقل البحث.
            //
            // وثمنُه مكتوبٌ هنا لأنه لا يُرى في الشاشة: الماركةُ والسنتان
            // (`VehicleQuery.make` و`yearFrom` و`yearTo`) تعمل ويرسلها
            // `_apply` إلى الخادم، **ولا مقبضَ لها في الرئيسية**.
            // و`VehicleFiltersButton` باقيةٌ تعمل في شاشة مركبات المزاد.
            // والطورُ له مفتاحُه في الترويسة.
          ),
        ),
      ),
    );
  }

  /// صندوقُ البحث والتبويبات — متراكبٌ على أسفل صورة الهيدر بلا بطاقةٍ تحته.
  ///
  /// **قوائمُ الترشيح (الكل/الماركة/السعر/من-إلى) بصريّةٌ بعد**: الماركةُ
  /// والسنتان تعملان في `VehicleQuery` بلا منتقٍ في الرئيسية، فالقوائمُ تقول
  /// «لم يُفعَّل بعد» بدل منتقٍ لا يفتح — تُوصَل حين يُبنى المنتقي.
  Widget _searchCard() => Container(
    margin: const EdgeInsets.fromLTRB(14, _searchCardTop, 14, 0),
    // **بلا أرضيّةٍ بيضاءَ خلف صندوق البحث** بطلب المالك (١٣ سبتمبر ٢٠٢٦):
    // كانت بطاقةٌ بيضاءُ شفّافةٌ بظلٍّ تحمل الحقلَ والتبويبات، فصارت ثلاثةَ
    // صناديقَ متداخلة — الحقلُ أبيضُ أصلاً والتبويباتُ لها حوضُها، فالأرضيّةُ
    // الثالثة زائدة.
    //
    // ولا إزاحةَ تسحبه فوق الصورة بعد اليوم: صار شريحةً مثبَّتةً داخل
    // القائمة، وما يعلو حدَّها يقصّه إطارُ التمرير عند التثبيت.
    child: Column(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: <Widget>[
        SizedBox(
          height: _searchHeight,
          child: VehicleSearchField(
            search: _query.search,
            onSubmitted: _search,
          ),
        ),
        // صفُّ قوائم الترشيح (الكل/الماركة/السعر/من-إلى) حُذف بطلب المالك
        // (١٣ سبتمبر ٢٠٢٦).
        const SizedBox(height: 12),
        _PhaseTabs(
          current: widget.phase,
          counts: _counts,
          onSelect: (phase) => Routes.goToPhase(context, phase),
        ),
      ],
    ),
  );

  /// ترويسةُ اللاب: النصُّ يميناً وصندوقُ البحث شمالاً **داخل الصورة**.
  ///
  /// `PositionedDirectional` لا `Positioned`: «شمال» في العربية هي `end`،
  /// و`left` مكتوبةً تضع الصندوقَ في الجهة الخطأ لو فُتح التطبيق بالإنجليزية.
  Widget _wideHeader(BuildContext context) => Container(
    height: _wideHeaderExtent,
    margin: const EdgeInsets.only(bottom: _wideHeaderGap),
    child: Stack(
      children: <Widget>[
        Positioned.fill(
          child: HomeHero(
            onOpenNotifications: () => context.go(Routes.myActivityPath),
            onOpenAccount: () => context.go(Routes.profilePath),
          ),
        ),
        PositionedDirectional(
          end: 24,
          top: 64,
          width: 440,
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: <Widget>[
              SizedBox(
                height: _searchHeight,
                child: VehicleSearchField(
                  search: _query.search,
                  onSubmitted: _search,
                ),
              ),
              const SizedBox(height: 12),
              _PhaseTabs(
                current: widget.phase,
                counts: _counts,
                onSelect: (phase) => Routes.goToPhase(context, phase),
              ),
            ],
          ),
        ),
      ],
    ),
  );

  /// الطور الفارغ يقول **لماذا** هو فارغ.
  ///
  /// وفراغُ بحثٍ غير فراغِ طور: من بحث عن «لكزس» في طورٍ نشط ولم يجد يجب أن
  /// يقرأ «لا مركبات مطابقة» لا «لا مزاد نشط الآن» — الثانية تقول له إن المزاد
  /// مقفل وهو مفتوح، فيغلق التطبيق.
  String _emptyMessage(AppLocalizations l10n) {
    if (_query.isFiltered) return l10n.vehiclesEmpty;
    return switch (widget.phase) {
      AuctionPhase.upcoming => l10n.homeEmptyUpcoming,
      AuctionPhase.active || AuctionPhase.unknown => l10n.homeEmptyActive,
      AuctionPhase.ended => l10n.homeEmptyEnded,
    };
  }
}

/// تبويبات الطور الثلاثة تحت حقل البحث — **مفتاحٌ مقسوم، لا ثلاثةُ صناديق**.
///
/// جُرِّبت ثلاثُ هيئاتٍ قبلها وردَّها المالك: خاناتٌ بأرضيّةٍ بنّيّة، ثم
/// خاناتٌ بإطارٍ ذهبيٍّ محيط، ثم خاناتٌ بشريطٍ ذهبيٍّ جانبيّ. وعلّتُها واحدة:
/// **ثلاثةُ صناديق منفصلة فوق قائمةِ كروتٍ كلُّها صناديق** — فلا تُقرأ مفتاحاً
/// يختار واحداً من ثلاثة، بل ثلاثةَ أزرارٍ لا رابط بينها. والحاوية الواحدة
/// هي الرابط: الأقسامُ داخلها فلا تُقرأ إلا معاً.
///
/// **الترتيب من `AuctionPhase.tabs` لا مكتوباً هنا**: التعداد يعرف ترتيبه،
/// وقائمةٌ ثانية تفترق عنه عند أول تعديل فيُفتح التبويبُ الخطأ (المادة ٤-٥).
///
/// **والاختيار يمرّ بالعنوان** (`?phase=`) لا بحالةٍ في الشاشة: الرابطُ
/// يُشارَك، ويصمد عبر إعادة الفتح، ويفتحه الإشعار على طوره (H6).
///
/// **والعدّاد على كلٍّ منها** — يصل مع الصفحة في نفس الطلب. وهو ما يجعل
/// التبويب الفارغ مفهوماً: من يفتح «نشط» فيجده خالياً يرى «قريباً ٢» بجانبه
/// فيعرف إلى أين يذهب، بدل أن يظنّ التطبيق معطّلاً.
class _PhaseTabs extends StatelessWidget {
  const _PhaseTabs({
    required this.current,
    required this.counts,
    required this.onSelect,
  });

  final AuctionPhase current;

  /// `null` قبل وصول أول صفحة. الرقم يُستبدل بشَرطةٍ ولا يُخفى: قسمٌ بلا رقمٍ
  /// ثم يظهر له رقمٌ يزحف بنصّه، والثلاثةُ تتزحزح معه.
  final PhaseCounts? counts;

  final void Function(AuctionPhase phase) onSelect;

  /// حشوةُ الحاوية حول اللوح — هي ما يجعل اللوح **داخلها** لا مساوياً لها.
  static const double _track = 4;

  static const double _height = 42;
  static const double _radius = 13;
  static const Duration _duration = Duration(milliseconds: 240);

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final palette = HarajPalette.of(context);
    final tabs = AuctionPhase.tabs;

    // `unknown` ليس قسماً، ورقمُه `-1` كان سيضع اللوح خارج الحاوية.
    final index = tabs.contains(current) ? tabs.indexOf(current) : 0;

    return Center(
      child: ConstrainedBox(
        // **بعرضٍ محدود لا بعرض الشاشة** — نفس حدّ لوحة الترحيب فوقها.
        // على شاشةٍ عريضة كان القسم الواحد يبلغ ٤٥٠ بكسلاً لكلمةٍ ورقم.
        constraints: const BoxConstraints(maxWidth: 440),
        child: Padding(
          // **بلا حاشيةٍ سفلى** (١٣ سبتمبر ٢٠٢٦): الصندوقُ مزاحٌ بعشرين
          // فوق الصورة، والتسعةُ تُضاف إليها فتصير الفجوةُ إلى أول كرتٍ
          // أربعين — ضِعفَ ما بين كرتين.
          padding: const EdgeInsets.fromLTRB(20, 0, 20, 0),
          child: SizedBox(
            height: _height,
            child: DecoratedBox(
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(_radius),
                // **أرضيّةٌ غائرة**: أغمقُ قليلاً من ورقة الصفحة لا أفتح.
                // الحاوية حوضٌ يجلس فيه اللوح، وحوضٌ أفتحُ من ورقته يطفو
                // فوقها فيصير صندوقاً رابعاً.
                color: Color.alphaBlend(
                  palette.gold.withValues(alpha: 0.09),
                  palette.pageBackground,
                ),
                border: Border.all(color: palette.gold.withValues(alpha: 0.18)),
              ),
              child: LayoutBuilder(
                builder: (context, constraints) {
                  // عرضُ القسم يُقسَم هنا لا يُخمَّن: اللوح يقف على قسمٍ
                  // بعينه، ورقمٌ مكتوبٌ سلفاً يزيغ عنه على كل عرضٍ آخر.
                  final segment =
                      (constraints.maxWidth - _track * 2) / tabs.length;

                  return Stack(
                    children: <Widget>[
                      // اللوح الذهبيّ — **ينزلق** ولا يظهر ويختفي.
                      //
                      // الانزلاق هو ما يجعل الثلاثة مفتاحاً واحداً: العين
                      // تتبع اللوح من قسمٍ إلى قسم فتفهم أنه واحدٌ ينتقل.
                      // وظهورٌ واختفاءٌ في مكانين يُقرأ ضوءَين ينطفئ أحدهما.
                      AnimatedPositionedDirectional(
                        duration: _duration,
                        curve: Curves.easeOutCubic,
                        start: _track + segment * index,
                        top: _track,
                        bottom: _track,
                        width: segment,
                        child: DecoratedBox(
                          decoration: BoxDecoration(
                            borderRadius: BorderRadius.circular(_radius - 4),
                            gradient: LinearGradient(
                              begin: Alignment.topCenter,
                              end: Alignment.bottomCenter,
                              colors: <Color>[palette.gold, palette.goldDeep],
                            ),
                            boxShadow: <BoxShadow>[
                              BoxShadow(
                                color: palette.goldDeep.withValues(alpha: 0.35),
                                blurRadius: 6,
                                offset: const Offset(0, 2),
                              ),
                            ],
                          ),
                        ),
                      ),
                      // **`Positioned.fill` لا صفٌّ عارٍ**: `Stack` محاذاتُه
                      // `topStart` و`fit` رخو، فابنٌ غيرُ موضَّع يأخذ ارتفاع
                      // محتواه ويلتصق بالأعلى. فوقف النصُّ في أعلى الحاوية
                      // واللوحُ ممتدٌّ بارتفاعها كلِّها تحته — يُقرأ كلاماً
                      // فوق مربّعٍ لا كلاماً في وسطه. والملءُ يعطي كل قسمٍ
                      // ارتفاع الحاوية فيتوسّط نصُّه فيه.
                      Positioned.fill(
                        child: Row(
                          children: <Widget>[
                            for (final phase in tabs)
                              Expanded(
                                child: _Segment(
                                  label: switch (phase) {
                                    AuctionPhase.upcoming =>
                                      l10n.homeTabUpcoming,
                                    AuctionPhase.active => l10n.homeTabActive,
                                    AuctionPhase.ended ||
                                    AuctionPhase.unknown => l10n.homeTabEnded,
                                  },
                                  count: counts?.of(phase),
                                  selected: phase == current,
                                  onTap: () => onSelect(phase),
                                ),
                              ),
                          ],
                        ),
                      ),
                    ],
                  );
                },
              ),
            ),
          ),
        ),
      ),
    );
  }
}

/// قسمٌ واحد من المفتاح: اسمٌ ورقمُه، **بلا أرضيّةٍ ولا حدّ**.
///
/// اللوحُ الذهبيّ يمرّ تحته من `_PhaseTabs`، وهذا لا يرسم إلا نصَّه — فلو
/// رسم لنفسه أرضيّةً حجب اللوحَ الذي ينزلق تحته.
class _Segment extends StatelessWidget {
  const _Segment({
    required this.label,
    required this.count,
    required this.selected,
    required this.onTap,
  });

  final String label;
  final int? count;
  final bool selected;
  final VoidCallback onTap;

  static const Duration _duration = Duration(milliseconds: 240);

  @override
  Widget build(BuildContext context) {
    final palette = HarajPalette.of(context);

    // **نصٌّ شبه أسود على الذهبيّ الممتلئ لا أبيض**: الأبيض على `#B8860B`
    // نسبتُه ٣٫٣:١ وهي دون حدِّ النصّ الصغير، وهذا يبلغ نحو ٧:١. وهو
    // `heroBottom` — لونُ أسفل اللوحة الداكنة — لا لونٌ جديد.
    final colour = selected ? palette.heroBottom : palette.inkMuted;

    return Semantics(
      selected: selected,
      button: true,
      // القارئ الصوتيّ يقول «مختار» ولا يترك الفرق للّون ولا للوزن.
      label: label,
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: onTap,
          borderRadius: BorderRadius.circular(9),
          splashColor: palette.goldMuted,
          highlightColor: palette.goldMuted,
          child: Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: <Widget>[
              Flexible(
                child: AnimatedDefaultTextStyle(
                  duration: _duration,
                  curve: Curves.easeOutCubic,
                  style: TextStyle(
                    fontFamily: HarajTheme.fontFamily,
                    fontSize: 12,
                    // الوزنُ يتغيّر مع اللون: عينٌ لا تفرّق الذهبيَّ عن
                    // الكريميّ تفرّق العريضَ عن المتوسّط.
                    fontWeight: selected ? FontWeight.w700 : FontWeight.w600,
                    color: colour,
                    height: 1.2,
                  ),
                  child: Text(
                    label,
                    maxLines: 1,
                    // القصّ لا الالتفاف: «منتهي» في قسمٍ بتسعين بكسلاً على
                    // شاشةٍ ضيّقة، وسطرٌ ثانٍ يطيل الحاوية كلَّها.
                    overflow: TextOverflow.ellipsis,
                    textAlign: TextAlign.center,
                  ),
                ),
              ),
              const SizedBox(width: 5),
              // **الرقم بنفس اللون مخفَّفاً، لا في حوضٍ ملوّن**: حوضٌ داخل
              // اللوح الذهبيّ شكلٌ داخل شكلٍ داخل حاوية، وثلاثةُ حدودٍ
              // متداخلة في أربعين بكسلاً هي بعينها الفوضى التي رُفض من
              // أجلها الشكلُ السابق. والتخفيفُ يكفي ليُقرأ عدّاداً لا جزءاً
              // من الاسم.
              AnimatedDefaultTextStyle(
                duration: _duration,
                curve: Curves.easeOutCubic,
                style: TextStyle(
                  fontFamily: HarajTheme.fontFamily,
                  fontSize: 12,
                  fontWeight: FontWeight.w700,
                  color: colour.withValues(alpha: selected ? 0.7 : 0.85),
                  height: 1.2,
                ),
                child: Text(count?.toString() ?? '—'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}


/// ترويسةُ الرئيسية: **لوحةٌ تنطوي وصندوقُ بحثٍ يثبت**.
///
/// شريحةٌ واحدة لا شريحتان، لأن صندوق البحث يتراكب على أسفل صورة اللوحة —
/// وتراكبُ شريحتين منفصلتين يقصّه إطارُ التمرير. فاللوحةُ هنا تنزلق إلى أعلى
/// داخل الترويسة (`top: -shrinkOffset`)، والصندوقُ يلزم أسفلَها حتى يبلغ
/// رأسَ الشاشة فيثبت وحده.
///
/// وأرضيّةُ الصندوق **تنزل عشرين ثم تصعد معه**: في الأعلى تبدأ تحت الحقل
/// فيظهر الحقلُ على الصورة، وعند الانطواء تغطّي الشريحةَ كلَّها — وبلا ذلك
/// يبقى شريطٌ شفّافٌ تمرّ فيه الكروتُ من خلف الحقل.
class _HomeHeader extends SliverPersistentHeaderDelegate {
  const _HomeHeader({
    required this.palette,
    required this.heroExtent,
    required this.hero,
    required this.card,
  });

  final HarajPalette palette;
  final double heroExtent;
  final Widget hero;
  final Widget card;

  @override
  double get minExtent => _searchCardExtent;

  @override
  double get maxExtent => heroExtent + _searchCardExtent - _searchOverlap;

  @override
  Widget build(
    BuildContext context,
    double shrinkOffset,
    bool overlapsContent,
  ) {
    final travel = maxExtent - minExtent;
    final progress = travel <= 0 ? 1.0 : (shrinkOffset / travel).clamp(0.0, 1.0);
    return Stack(
      clipBehavior: Clip.hardEdge,
      children: <Widget>[
        Positioned(
          top: -shrinkOffset,
          left: 0,
          right: 0,
          height: heroExtent,
          child: hero,
        ),
        Positioned(
          bottom: 0,
          left: 0,
          right: 0,
          height: _searchCardExtent,
          child: Stack(
            children: <Widget>[
              Positioned(
                top: _searchOverlap * (1 - progress),
                left: 0,
                right: 0,
                bottom: 0,
                child: ColoredBox(color: palette.pageBackground),
              ),
              // **`Positioned.fill` لا طفلاً حرّاً**: الطفلُ الحرّ في `Stack`
              // يأخذ عرضَه الطبيعيّ، وعمودُ الصندوق بلا عرضٍ طبيعيّ فينكمش.
              Positioned.fill(child: card),
            ],
          ),
        ),
      ],
    );
  }

  @override
  bool shouldRebuild(_HomeHeader old) =>
      old.heroExtent != heroExtent ||
      old.hero != hero ||
      old.card != card ||
      old.palette != palette;
}
