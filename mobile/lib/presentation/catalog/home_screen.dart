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

class _HomeScreenState extends ConsumerState<HomeScreen> {
  VehicleQuery _query = const VehicleQuery();
  AsyncValue<Snapshot<VehicleFeed>> _first =
      const AsyncValue<Snapshot<VehicleFeed>>.loading();

  final List<VehicleSummary> _vehicles = <VehicleSummary>[];
  int _totalCount = 0;
  bool _hasMore = false;
  bool _loadingMore = false;
  Failure? _moreFailure;

  /// آخر عدّادات وصلت. تبقى معروضة أثناء تحميل الطور التالي بدل أن تختفي
  /// الأرقام ثم تعود — وميضٌ يجعل الخانات ترقص عند كل ضغطة.
  PhaseCounts? _counts;

  /// كل طلبٍ جديد يبطل ما قبله: ردٌّ بطيء لطورٍ غادره العميل كان سيصل بعد ردّ
  /// الطور الذي يقف فيه فيدهسه، فيرى مركبات طورٍ آخر تحت عنوان طوره.
  int _generation = 0;

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
                    // البحث فوق الحالة لا داخلها: عميلٌ بحث فأخطأ الخادم يجب
                    // أن يبقى قادراً على تعديل كلمته، لا أن يواجه شاشة خطأ
                    // بلا مخرج. ولا مفتاح عليه: من بحث عن «كامري» ثم بدّل
                    // الطور يجب أن يجد كلمته مكتوبة كما تركها.
                    Padding(
                      padding: const EdgeInsets.fromLTRB(20, 18, 20, 8),
                      child: VehicleSearchField(
                        search: _query.search,
                        onSubmitted: _search,
                      ),
                    ),
                    Expanded(
                      child: SnapshotView<VehicleFeed>(
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
                          onOpenVehicle: (vehicle) =>
                              Routes.goToVehicle(context, vehicle.id),
                          emptyMessage: _emptyMessage(l10n),
                          trailing: VehicleFiltersButton(
                            query: _query,
                            phase: widget.phase,
                            counts: _counts,
                            onApply: _apply,
                            onPhase: (phase) =>
                                Routes.goToPhase(context, phase),
                          ),
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
