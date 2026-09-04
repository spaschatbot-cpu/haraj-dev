import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app/providers.dart';
import '../../app/router.dart';
import '../../domain/catalog/entities/auction_phase.dart';
import '../../domain/catalog/entities/vehicle_feed.dart';
import '../../domain/catalog/entities/vehicle_query.dart';
import '../../domain/catalog/entities/vehicle_summary.dart';
import '../../domain/common/failure.dart';
import '../../domain/common/snapshot.dart';
import '../../l10n/generated/app_localizations.dart';
import '../common/snapshot_view.dart';
import 'widgets/vehicle_filters.dart';
import 'widgets/vehicle_results.dart';

/// الرئيسية: **شبكة مركبات مسطّحة عبر المزادات، فوقها تبويبٌ بطور المزاد.**
///
/// المزاد واحد في الأسبوع وحالته تتغيّر، فالسؤال الذي يفتح به العميل التطبيق
/// ليس «أي المزادات موجود؟» بل «إيش المعروض دلوقتي؟». ولذلك حلّت المركبات محلّ
/// قائمة المزادات، وصار التبويب عملياً هو «أي مزادٍ أنظر إليه الآن».
///
/// **القسمة والعدّ من الخادم.** الطور يأتي في `phase` لكل مركبة، والعدّادات
/// الثلاثة تأتي مع الصفحة في **طلبٍ واحد**. لا الشاشة تصنّف مزاداً بنفسها، ولا
/// تعدّ التبويبات من طول القائمة: في v1 كانت الأرقام الثلاثة تُطلب في ستّة
/// طلبات، فيصير كل رقم من لحظة، ويقع التبويب على «٣» ثم يُفتح فيه صفر.
///
/// **التبويب في العنوان** (`?phase=active`) لا في حالة الشاشة وحدها: الرابط
/// يُشارَك، ويصمد عبر إعادة الفتح، ويفتحه الإشعار على تبويبه (H6).
class HomeScreen extends ConsumerStatefulWidget {
  const HomeScreen({this.phase = AuctionPhase.defaultTab, super.key});

  /// التبويب المعروض — يقرؤه جدول المسارات من `?phase=` ويمرّره.
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

  /// آخر عدّادات وصلت. تبقى معروضة أثناء تحميل التبويب التالي بدل أن تختفي
  /// الأرقام ثم تعود — وميضٌ يجعل التبويبات ترقص عند كل ضغطة.
  PhaseCounts? _counts;

  /// كل طلبٍ جديد يبطل ما قبله: ردٌّ بطيء لتبويبٍ غادره العميل كان سيصل بعد
  /// ردّ التبويب الذي يقف فيه فيدهسه، فيرى مركبات تبويبٍ آخر تحت عنوان تبويبه.
  int _generation = 0;

  @override
  void initState() {
    super.initState();
    _reload();
  }

  @override
  void didUpdateWidget(HomeScreen oldWidget) {
    super.didUpdateWidget(oldWidget);
    // التبويب تغيّر من العنوان (ضغطة تبويب، أو رجوع، أو رابط). المعايير تبقى:
    // من بحث عن «كامري» ثم بدّل التبويب يسأل عن كامري في التبويب الجديد، لا
    // يبدأ من الصفر.
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

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);

    return DefaultTabController(
      // المفتاح بالطور: التبويب المختار يأتي من العنوان، والمتحكّم يُعاد بناؤه
      // معه. بلا المفتاح يبقى المتحكّم على `initialIndex` الأول، فيصل رابطٌ
      // إلى `?phase=ended` ويُضاء «نشط».
      key: ValueKey<AuctionPhase>(widget.phase),
      length: AuctionPhase.tabs.length,
      initialIndex: AuctionPhase.tabs.indexOf(widget.phase),
      child: Scaffold(
        appBar: AppBar(
          title: Text(l10n.homeTitle),
          bottom: _PhaseTabs(counts: _counts),
        ),
        body: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: <Widget>[
            // النموذج فوق الحالة لا داخلها: عميلٌ رشّح فأخطأ الخادم يجب أن يبقى
            // قادراً على إزالة الترشيح، لا أن يواجه شاشة خطأ بلا مخرج. ولا
            // مفتاح عليه: من بحث عن «كامري» ثم بدّل التبويب يجب أن يجد كلمته
            // مكتوبة كما تركها.
            VehicleFilters(query: _query, onApply: _apply),
            Expanded(
              child: SnapshotView<VehicleFeed>(
                state: _first,
                onRetry: _reload,
                builder: (context, snapshot) => VehicleResults(
                  layout: VehicleResultsLayout.grid,
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
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  /// التبويب الفارغ يقول **لماذا** هو فارغ.
  ///
  /// وفراغُ بحثٍ غير فراغِ تبويب: من بحث عن «لكزس» في تبويب نشط ولم يجد يجب أن
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

/// شريط التبويبات الثلاثة بعدّاداتها.
///
/// `PreferredSizeWidget` لأنه يسكن أسفل `AppBar`؛ ولا `TabBarView` تحته: كل
/// تبويب عنوانٌ مستقلّ، والانتقال إليه تنقّلٌ في الموجّه لا تمريرٌ أفقي في
/// شاشة. لو كان تمريراً لضاع العنوان، ولعاد الرابط المشارَك إلى التبويب الأول.
class _PhaseTabs extends StatelessWidget implements PreferredSizeWidget {
  const _PhaseTabs({required this.counts});

  /// `null` قبل وصول أول ردّ: التبويب يظهر باسمه بلا رقم.
  ///
  /// **لا صفر مكانه.** «منتهي (٠)» جوابٌ لم يقله أحد، ومن قرأه لن يضغط التبويب
  /// أصلاً. الاسم وحده يقول «لا أعرف بعد»، وهو الصدق المتاح.
  final PhaseCounts? counts;

  @override
  Size get preferredSize => const Size.fromHeight(kTextTabBarHeight);

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final tally = counts;

    return TabBar(
      // الضغطة تنقّلٌ في الموجّه لا تبديلُ حالة هنا: العنوان هو مصدر التبويب،
      // والشاشة تُعاد بناؤها منه. لو بدّلت الحالة هنا لصار للتبويب مصدران —
      // العنوان وهذا المتحكّم — يفترقان عند أول رجوعٍ بزرّ النظام.
      onTap: (index) => Routes.goToPhase(context, AuctionPhase.tabs[index]),
      tabs: <Widget>[
        for (final phase in AuctionPhase.tabs)
          Tab(
            text: tally == null
                ? _label(l10n, phase)
                : l10n.homeTabWithCount(_label(l10n, phase), tally.of(phase)),
          ),
      ],
    );
  }

  String _label(AppLocalizations l10n, AuctionPhase phase) => switch (phase) {
    AuctionPhase.upcoming => l10n.homeTabUpcoming,
    AuctionPhase.active => l10n.homeTabActive,
    AuctionPhase.ended => l10n.homeTabEnded,
    AuctionPhase.unknown => l10n.homeTabActive,
  };
}
