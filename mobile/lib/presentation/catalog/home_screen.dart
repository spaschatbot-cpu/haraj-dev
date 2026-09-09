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

/// ارتفاعُ حقل البحث داخل الشريحة الثابتة.
const double _searchHeight = 48;

/// ارتفاعُ الشريحة الثابتة كلِّها: حشوةُ البحث (١٠+٥) وحقلُه (٤٨)، ثم مفتاحُ
/// الأطوار بحشوته (٤+٤٢+٩).
///
/// والأرقامُ الأربعة تغيّرت في ٩ سبتمبر ٢٠٢٦: المفتاحُ ارتفع أربعةَ بكسلات
/// نحو حقل البحث، ونزل تسعةً عن أول كرت — كان ملتصقاً به.
const double _pinnedExtent = 10 + _searchHeight + 5 + 4 + 42 + 9;

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
    final palette = HarajPalette.of(context);

    return AnnotatedRegion<SystemUiOverlayStyle>(
      // ساعةُ النظام وبطّاريّتُه فوق لوحةٍ داكنة: تُركا للثيم الفاتح كانا
      // سيُرسمان أسودَين على أسود.
      value: SystemUiOverlayStyle.light,
      child: Scaffold(
        body: Column(
          children: <Widget>[
            HomeHero(
              // لا شاشةَ إشعاراتٍ في التطبيق بعد، وأقربُ ما يجيب عن «ما الذي
              // حدث لي؟» هو مشاركاتي. الجرس يذهب إليها ولا يبقى زرّاً لا
              // يفعل شيئاً — زرٌّ لا يستجيب يُقرأ عطلاً.
              onOpenNotifications: () => context.go(Routes.myActivityPath),
              onOpenAccount: () => context.go(Routes.profilePath),
            ),
            // **الورقة مسطّحةٌ لا مدوّرة**: البانر هو من يدوّر حافّته
            // السفلى الآن، وتدويرُ الاثنين معاً يترك بينهما هلالاً من أرضيّة
            // الـ`Scaffold` يُقرأ شقّاً.
            Expanded(
              child: ColoredBox(
                color: palette.pageBackground,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: <Widget>[
                    // **الترويسةُ تنزلق مع القائمة** — لوحةُ الترحيب
                    // وحقلُ البحث ومفتاحُ الأطوار داخل `CustomScrollView`
                    // لا فوقه، بطلب المالك في ٩ سبتمبر ٢٠٢٦ على مثال v1.
                    //
                    // **إلا حين لا تكون هناك قائمة**: أثناء أول تحميلٍ أو
                    // بعد فشله لا `VehicleResults` يحمل الترويسة، وحقلُ
                    // البحث يجب أن يبقى — عميلٌ بحث فأخطأ الخادم يجب أن
                    // يبقى قادراً على تعديل كلمته، لا أن يواجه شاشة خطأ بلا
                    // مخرج. والحالتان متنافيتان فلا تظهر مرّتين.
                    if (!_first.hasValue) ...<Widget>[
                      const _WelcomePanel(),
                      _pinnedHeader(),
                    ],
                    Expanded(
                      child: SnapshotView<VehicleFeed>(
                        state: _first,
                        onRetry: _reload,
                        builder: (context, snapshot) => VehicleResults(
                          header: const _WelcomePanel(),
                          pinnedHeader: _pinnedHeader(),
                          pinnedHeaderExtent: _pinnedExtent,
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
                          // **لا زرّ فرزٍ ولا ورقة تصفية** — مُحي
                          // بطلب المالك في ٩ سبتمبر ٢٠٢٦، مرّتين: من سطر
                          // العدّ أوّلاً، ثم من جانب حقل البحث.
                          //
                          // وثمنُه مكتوبٌ هنا لأنه لا يُرى في الشاشة:
                          // الماركةُ والسنتان (`VehicleQuery.make`
                          // و`yearFrom` و`yearTo`) تعمل ويرسلها `_apply`
                          // إلى الخادم، **ولا مقبضَ لها في الرئيسية**.
                          // و`VehicleFiltersButton` باقيةٌ تعمل في شاشة
                          // مركبات المزاد. والطورُ له مفتاحُه في الترويسة.
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  /// حقلُ البحث ومفتاحُ الأطوار — **ثابتان فوق القائمة** بطلب المالك في ٩
  /// سبتمبر ٢٠٢٦، ولوحةُ الترحيب وحدها تنزلق.
  ///
  /// **دالّةٌ لا مكوّنٌ مستقلّ**: الاثنان يقرآن `_query` و`_counts`
  /// و`widget.phase` ويكتبان عبر `_search`، ونقلُهما إلى مكوّنٍ خارج الشاشة
  /// يعني تمريرَ أربعة معاملات لتُعاد كما هي.
  Widget _pinnedHeader() => Column(
    mainAxisSize: MainAxisSize.min,
    crossAxisAlignment: CrossAxisAlignment.stretch,
    children: <Widget>[
      Padding(
        // **بعرض الحقل كلِّه**: كان بجانبه زرُّ «الفرز والتصفية» فيقتطع منه
        // نحو مئةٍ وعشرين بكسلاً، ومُحي بطلب المالك في ٩ سبتمبر ٢٠٢٦.
        padding: const EdgeInsets.fromLTRB(20, 10, 20, 5),
        // **ارتفاعٌ مضبوط**: الشريحةُ الثابتة تُبنى بارتفاعٍ يُفرَض عليها،
        // فلو نما الحقلُ بحجم خطّ الجهاز لفاض عن الشريحة.
        child: SizedBox(
          height: _searchHeight,
          child: VehicleSearchField(
            search: _query.search,
            onSubmitted: _search,
          ),
        ),
      ),
      _PhaseTabs(
        current: widget.phase,
        counts: _counts,
        onSelect: (phase) => Routes.goToPhase(context, phase),
      ),
    ],
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

/// لوحةُ الترحيب فوق حقل البحث — سطران بنصّ المالك حرفياً.
///
/// **موضعُها تحت اللوحة الداكنة لا داخلها**: الهيدر ارتفاعه ٥٨ ولا يتّسع
/// لسطرين (جُرِّب، وأفاض `Spacer` اللوحةَ ٤٦ بكسلاً)، وأرضيّتُه داكنة فسطرٌ
/// طويلٌ عليه يُقرأ بجهد. والورقةُ الكريميّة تحته فارغةٌ ومقروءة.
///
/// **ثابتةٌ لا تنزلق مع القائمة**: هي وحقلُ البحث كتلةٌ واحدة تفتتح الصفحة،
/// وتمريرُ إحداهما دون الأخرى يترك الحقلَ معلّقاً بلا سياق.
///
/// **بعرضٍ محدود (٤٤٠) لا بعرض الشاشة**: على شاشةٍ عريضة كان الخيطان يمتدّان
/// من حافةٍ لحافة فيصيران خطَّ فصلٍ يقطع الصفحة، ويقف العنوانُ في وسط فراغٍ
/// لا يخصّه. والكتلةُ المحدودة تُقرأ لوحةً معنونة.
class _WelcomePanel extends StatelessWidget {
  const _WelcomePanel();

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final palette = HarajPalette.of(context);

    return Center(
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 440),
        child: Padding(
          padding: const EdgeInsets.fromLTRB(20, 16, 20, 0),
          child: Column(
            children: <Widget>[
              const _Ornament(),
              const SizedBox(height: 9),
              // **العنوان ذهبيٌّ متدرّج** بطلب المالك في ٩ سبتمبر ٢٠٢٦.
              //
              // و`ShaderMask` لا لونٌ واحد: الذهبُ المسطّح على ورقةٍ كريميّة
              // يُقرأ خردليّاً باهتاً — ما يجعله ذهباً هو تحوّلُه من غائرٍ
              // إلى لامعٍ إلى غائر، كما ينعكس الضوءُ على معدن.
              //
              // **والأطرافُ الثلاثة كلُّها غائرة** (`#8A6508` و`#B8860B`):
              // الذهبيُّ الفاتح (`#E3BC57`) نسبتُه على الكريميّ ٢٫٥:١ ولا
              // يبلغ حدَّ العناوين، فيُقرأ العنوانُ باهتاً على شاشةٍ في
              // الشمس. وهذان يبلغان ٤٫١:١ فما فوق ويبقيان ذهباً.
              ShaderMask(
                blendMode: BlendMode.srcIn,
                shaderCallback: (bounds) => LinearGradient(
                  begin: Alignment.centerRight,
                  end: Alignment.centerLeft,
                  colors: <Color>[
                    palette.goldDeep,
                    palette.gold,
                    palette.goldDeep,
                  ],
                  stops: const <double>[0, 0.5, 1],
                ).createShader(bounds),
                child: Text(
                  l10n.homeTagline,
                  textAlign: TextAlign.center,
                  style: TextStyle(
                    fontFamily: HarajTheme.fontFamily,
                    fontSize: 19,
                    fontWeight: FontWeight.w700,
                    // اللون يُبتلع بـ`srcIn`، لكنه ليس زائداً: هو ما يظهر لو
                    // سقط الشيدر (بعض المتصفّحات في وضع التباين العالي).
                    color: palette.goldDeep,
                    height: 1.35,
                    letterSpacing: 0.2,
                  ),
                ),
              ),
              // **السطر الثاني لا يظهر على الجوّال** بطلب المالك في ٩
              // سبتمبر ٢٠٢٦: ارتفاع الشاشة هناك هو المورد النادر، وهذا
              // السطرُ ترحيبٌ يُقرأ مرّةً ويأكل من كل تمريرةٍ بعدها. وعلى
              // الشاشة العريضة الارتفاعُ فائضٌ فيبقى.
              //
              // **٦٠٠ حدّاً**: هو حدُّ اللوح المتعارف عليه، وأعرضُ جوّالٍ
              // قائمٍ دونه بفارقٍ مريح — فلا يقع جوّالٌ كبير في جهة اللوح.
              // و`sizeOf` لا `of`: هذه تُعيد بناءَ اللوحة عند تغيّر أي حقلٍ
              // في `MediaQuery` — حتى ظهورِ لوحة المفاتيح تحت حقل البحث.
              if (MediaQuery.sizeOf(context).width >= 600) ...<Widget>[
                const SizedBox(height: 6),
                Text(
                  l10n.homeSubtagline,
                  textAlign: TextAlign.center,
                  // سطران حدّاً أقصى: وثالثٌ يزيح حقلَ البحث لا يُقصّ.
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                  style: TextStyle(
                    fontFamily: HarajTheme.fontFamily,
                    fontSize: 12.5,
                    fontWeight: FontWeight.w500,
                    // خافتٌ لا رماديّ: الفرق بينه وبين العنوان شدّةٌ في نفس
                    // العائلة الدافئة، ورماديٌّ محايد بينهما يُقرأ
                    // «معطَّلاً».
                    color: palette.inkMuted,
                    height: 1.5,
                  ),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}

/// زخرفةٌ ذهبيّة فوق العنوان: خيطان قصيران بينهما معيّن.
///
/// **بعرضٍ ثابت لا `Expanded`**: خيطٌ يمتدّ بعرض الشاشة يُقرأ فاصلاً بين
/// قسمين، وهذه ليست فاصلاً — هي تاجُ العنوان. وعرضُها ثابتٌ لأنها لا تحمل
/// نصّاً يطول بالترجمة.
class _Ornament extends StatelessWidget {
  const _Ornament();

  @override
  Widget build(BuildContext context) {
    final gold = HarajPalette.of(context).gold;

    return Row(
      mainAxisSize: MainAxisSize.min,
      children: <Widget>[
        _OrnamentRule(gold: gold, fadeAtStart: true),
        const SizedBox(width: 8),
        // معيّنٌ لا نقطة: النقطةُ تُقرأ علامةَ ترقيمٍ سقطت، والمعيّنُ شكلٌ
        // مقصود. وهو مربّعٌ مُدارٌ ٤٥° لا مسارٌ مرسوم — ستّةُ بكسلات لا
        // تستحقّ `CustomPainter`.
        Transform.rotate(
          angle: 0.785398,
          child: Container(width: 5, height: 5, color: gold),
        ),
        const SizedBox(width: 8),
        _OrnamentRule(gold: gold, fadeAtStart: false),
      ],
    );
  }
}

class _OrnamentRule extends StatelessWidget {
  const _OrnamentRule({required this.gold, required this.fadeAtStart});

  final Color gold;

  /// أيُّ طرفٍ يتلاشى — الخارجيُّ دائماً، فالخيطان يخرجان من المعيّن ولا
  /// يدخلان إليه.
  final bool fadeAtStart;

  @override
  Widget build(BuildContext context) {
    final colours = <Color>[
      gold.withValues(alpha: 0),
      gold.withValues(alpha: 0.8),
    ];

    return Container(
      width: 34,
      height: 1,
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: fadeAtStart ? colours : colours.reversed.toList(),
        ),
      ),
    );
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
          padding: const EdgeInsets.fromLTRB(20, 4, 20, 9),
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
