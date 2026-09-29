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
import 'widgets/vehicle_filters.dart';
import 'widgets/vehicle_results.dart';

/// الرئيسية: **قائمة مركبات مسطّحة عبر المزادات.**
///
/// المزاد واحد في الأسبوع وحالته تتغيّر، فالسؤال الذي يفتح به العميل التطبيق
/// ليس «أي المزادات موجود؟» بل «إيش المعروض دلوقتي؟». ولذلك حلّت المركبات محلّ
/// قائمة المزادات، وصار الطور عملياً هو «أي مزادٍ أنظر إليه الآن».
///
/// **هيئةُ تصميم المالك** (٣٠ سبتمبر ٢٠٢٦): رأسٌ أبيض بالشعار والاسم وزرَّي
/// الإشعارات والحساب، ثم حقلُ بحثٍ في طرفه «تصفية»، ثم شرائحُ الماركات، ثم
/// عنوانُ القسم وعدُّه، ثم الكروت، وفي آخرها سطرُ «العروض سرّية». وحلّ هذا
/// محلَّ لوحة الصورة الداكنة ومفتاحِ الأطوار الثلاثيّ.
///
/// **القسمة والعدّ من الخادم.** الطور يأتي في `phase` لكل مركبة، والعدّادات
/// الثلاثة تأتي مع الصفحة في **طلبٍ واحد** — في v1 كانت الأرقام الثلاثة تُطلب
/// في ستّة طلبات، فيصير كل رقم من لحظة.
///
/// **الطور في العنوان** (`?phase=active`) لا في حالة الشاشة وحدها: الرابط
/// يُشارَك، ويصمد عبر إعادة الفتح، ويفتحه الإشعار على طوره (H6). ومقبضُه
/// قائمةٌ صغيرة على طرف عنوان القسم، وفي ورقة «تصفية» أيضاً.
class HomeScreen extends ConsumerStatefulWidget {
  const HomeScreen({this.phase = AuctionPhase.defaultTab, super.key});

  /// الطور المعروض — يقرؤه جدول المسارات من `?phase=` ويمرّره.
  final AuctionPhase phase;

  @override
  ConsumerState<HomeScreen> createState() => _HomeScreenState();
}

/// ارتفاعُ الشريحة الثابتة **بالضبط** — `SliverPersistentHeader` يفرضه ولا
/// يقيسه: حاشيةٌ (١٠) + البحث (٥٢) + فاصلٌ (١٠) + الشرائح (٤٠) + حاشيةٌ (٨).
const double _pinnedExtent = 10 + 52 + 10 + 40 + 8;

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
  /// الطور الذي يقف فيه فيدهسه.
  int _generation = 0;

  /// آخر عدّادات وصلت — تبقى معروضةً أثناء تحميل الطور التالي.
  PhaseCounts? _counts;

  /// ماركاتُ الشرائح — **من المركبات نفسها لا قائمةٌ مكتوبة**: ما في المزاد
  /// الآن. تُجمع من الصفحة غير المرشَّحة وتبقى حين يُختار أحدها، وإلا
  /// اختفت الشرائحُ الأخرى بمجرّد الضغط على واحدة.
  List<String> _makes = const <String>[];

  @override
  void initState() {
    super.initState();
    _reload();
  }

  @override
  void didUpdateWidget(HomeScreen oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.phase != widget.phase) {
      _makes = const <String>[];
      _reload();
    }
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
        if ((_query.make ?? '').isEmpty) _makes = _makesOf(_vehicles);
      });
    } on Object catch (error, stackTrace) {
      if (!mounted || generation != _generation) return;
      setState(
        () =>
            _first = AsyncValue<Snapshot<VehicleFeed>>.error(error, stackTrace),
      );
    }
  }

  static List<String> _makesOf(List<VehicleSummary> vehicles) {
    final seen = <String>{};
    for (final vehicle in vehicles) {
      final make = vehicle.make.trim();
      if (make.isNotEmpty) seen.add(make);
    }
    return seen.toList(growable: false);
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
        _counts = snapshot.value.counts;
        _loadingMore = false;
        if ((_query.make ?? '').isEmpty) {
          _makes = <String>{..._makes, ..._makesOf(_vehicles)}.toList();
        }
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

  void _pickMake(String? make) => _apply(
    VehicleQuery(
      search: _query.search,
      make: make,
      yearFrom: _query.yearFrom,
      yearTo: _query.yearTo,
    ),
  );

  void _openFilters() => showVehicleFilters(
    context,
    query: _query,
    phase: widget.phase,
    counts: _counts,
    onApply: _apply,
    onPhase: (phase) => Routes.goToPhase(context, phase),
  );

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final palette = HarajPalette.of(context);

    return AnnotatedRegion<SystemUiOverlayStyle>(
      // الرأسُ أبيض: ساعةُ النظام وبطّاريّتُه داكنتان فوقه.
      value: SystemUiOverlayStyle.dark,
      child: Scaffold(
        backgroundColor: palette.pageBackground,
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
            // **الرأسُ ينزلق، والبحثُ والشرائحُ تثبت** — هما مقبضا القائمة،
            // ومن نزل عشرين كرتاً ثم أراد ماركةً أخرى لا يصعد كلَّها.
            header: _BrandBar(
              onOpenNotifications: () => context.go(Routes.myActivityPath),
              onOpenAccount: () => context.go(Routes.profilePath),
            ),
            pinnedHeader: _searchAndMakes(l10n, palette),
            pinnedHeaderExtent: _pinnedExtent,
            listHeader: _SectionTitle(
              phase: widget.phase,
              count: _totalCount,
              counts: _counts,
              onPhase: (phase) => Routes.goToPhase(context, phase),
            ),
            listFooter: const _SealedNote(),
          ),
        ),
      ),
    );
  }

  Widget _searchAndMakes(AppLocalizations l10n, HarajPalette palette) {
    final selected = (_query.make ?? '').trim();
    final all = _counts?.of(widget.phase) ?? _totalCount;
    return Padding(
      padding: const EdgeInsets.only(top: 10, bottom: 8),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: <Widget>[
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16),
            child: SizedBox(
              height: 52,
              child: VehicleSearchField(
                search: _query.search,
                onSubmitted: _search,
                hint: l10n.homeSearchHintFull,
                trailing: _FilterButton(
                  label: l10n.homeFilter,
                  active: _query.isFiltered,
                  onTap: _openFilters,
                ),
              ),
            ),
          ),
          const SizedBox(height: 10),
          SizedBox(
            height: 40,
            child: ListView(
              scrollDirection: Axis.horizontal,
              padding: const EdgeInsets.symmetric(horizontal: 16),
              children: <Widget>[
                _MakeChip(
                  label: l10n.homeAllChip(all),
                  selected: selected.isEmpty,
                  onTap: () => _pickMake(null),
                ),
                for (final make in _makes) ...<Widget>[
                  const SizedBox(width: 8),
                  _MakeChip(
                    label: make,
                    selected: selected == make,
                    onTap: () => _pickMake(make),
                  ),
                ],
              ],
            ),
          ),
        ],
      ),
    );
  }

  /// الطور الفارغ يقول **لماذا** هو فارغ — وفراغُ بحثٍ غيرُ فراغِ طور.
  String _emptyMessage(AppLocalizations l10n) {
    if (_query.isFiltered) return l10n.vehiclesEmpty;
    return switch (widget.phase) {
      AuctionPhase.upcoming => l10n.homeEmptyUpcoming,
      AuctionPhase.active || AuctionPhase.unknown => l10n.homeEmptyActive,
      AuctionPhase.ended => l10n.homeEmptyEnded,
    };
  }
}

/// الرأسُ الأبيض: الشعارُ في مربّعٍ أزرق، والاسمُ وشارةُ الإصدار، وسطرُ
/// التعريف، وفي الطرف الآخر زرّا الإشعارات والحساب.
class _BrandBar extends StatelessWidget {
  const _BrandBar({
    required this.onOpenNotifications,
    required this.onOpenAccount,
  });

  final VoidCallback onOpenNotifications;
  final VoidCallback onOpenAccount;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final palette = HarajPalette.of(context);
    final top = MediaQuery.paddingOf(context).top;

    return Container(
      padding: EdgeInsets.fromLTRB(16, top + 14, 16, 14),
      decoration: BoxDecoration(
        color: palette.cardSurface,
        border: Border(
          bottom: BorderSide(color: palette.navInactive.withValues(alpha: 0.6)),
        ),
      ),
      child: Row(
        children: <Widget>[
          Container(
            width: 52,
            height: 52,
            padding: const EdgeInsets.all(9),
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(16),
              gradient: LinearGradient(
                begin: Alignment.topRight,
                end: Alignment.bottomLeft,
                colors: <Color>[palette.gold, palette.goldDeep],
              ),
              boxShadow: <BoxShadow>[
                BoxShadow(
                  color: palette.gold.withValues(alpha: 0.30),
                  blurRadius: 12,
                  offset: const Offset(0, 4),
                ),
              ],
            ),
            child: Image.asset(
              'assets/images/logo.png',
              fit: BoxFit.contain,
              errorBuilder: (_, _, _) =>
                  const Icon(Icons.gavel_rounded, color: Colors.white),
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Row(
                  children: <Widget>[
                    Flexible(
                      child: Text(
                        l10n.homeBrand,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: TextStyle(
                          fontFamily: HarajTheme.fontFamily,
                          fontSize: 18,
                          fontWeight: FontWeight.w700,
                          color: palette.ink,
                          height: 1.25,
                        ),
                      ),
                    ),
                    const SizedBox(width: 6),
                    Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 7,
                        vertical: 1,
                      ),
                      decoration: BoxDecoration(
                        color: palette.gold.withValues(alpha: 0.10),
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: Text(
                        'v2',
                        textDirection: TextDirection.ltr,
                        style: TextStyle(
                          fontFamily: HarajTheme.fontFamily,
                          fontSize: 11,
                          fontWeight: FontWeight.w700,
                          color: palette.gold,
                        ),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 2),
                Text(
                  l10n.homeBrandSubtitle,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: TextStyle(
                    fontFamily: HarajTheme.fontFamily,
                    fontSize: 12,
                    color: palette.inkMuted,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(width: 8),
          _SquareAction(
            icon: Icons.notifications_none_rounded,
            tooltip: l10n.homeNotifications,
            onTap: onOpenNotifications,
            badge: true,
          ),
          const SizedBox(width: 8),
          _SquareAction(
            icon: Icons.person_rounded,
            tooltip: l10n.homeAccountAction,
            onTap: onOpenAccount,
            tinted: true,
          ),
        ],
      ),
    );
  }
}

class _SquareAction extends StatelessWidget {
  const _SquareAction({
    required this.icon,
    required this.tooltip,
    required this.onTap,
    this.badge = false,
    this.tinted = false,
  });

  final IconData icon;
  final String tooltip;
  final VoidCallback onTap;
  final bool badge;

  /// المربّعُ المظلَّل بالأزرق — زرُّ الحساب في التصميم.
  final bool tinted;

  @override
  Widget build(BuildContext context) {
    final palette = HarajPalette.of(context);
    return Tooltip(
      message: tooltip,
      child: Stack(
        clipBehavior: Clip.none,
        children: <Widget>[
          Material(
            color: tinted
                ? palette.gold.withValues(alpha: 0.10)
                : palette.cardSurface,
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(14),
              side: BorderSide(
                color: tinted
                    ? palette.gold.withValues(alpha: 0.25)
                    : palette.navInactive,
              ),
            ),
            child: InkWell(
              onTap: onTap,
              borderRadius: BorderRadius.circular(14),
              child: SizedBox(
                width: 44,
                height: 44,
                child: Icon(
                  icon,
                  size: 22,
                  color: tinted ? palette.gold : palette.ink,
                ),
              ),
            ),
          ),
          if (badge)
            PositionedDirectional(
              top: 8,
              end: 9,
              child: Container(
                width: 9,
                height: 9,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: const Color(0xFFE53935),
                  border: Border.all(color: palette.cardSurface, width: 1.5),
                ),
              ),
            ),
        ],
      ),
    );
  }
}

/// «تصفية» داخل حقل البحث — يفتح ورقةَ الطور والماركة والسنتين. ونقطةٌ عليه
/// حين يكون ترشيحٌ قائماً: بدونها لا شيء يقول إن النتائج مُضيَّقة.
class _FilterButton extends StatelessWidget {
  const _FilterButton({
    required this.label,
    required this.active,
    required this.onTap,
  });

  final String label;
  final bool active;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final palette = HarajPalette.of(context);
    return Material(
      color: palette.gold.withValues(alpha: 0.08),
      borderRadius: BorderRadius.circular(11),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(11),
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: <Widget>[
              Icon(Icons.tune_rounded, size: 17, color: palette.ink),
              const SizedBox(width: 6),
              Text(
                label,
                style: TextStyle(
                  fontFamily: HarajTheme.fontFamily,
                  fontSize: 13,
                  fontWeight: FontWeight.w700,
                  color: palette.ink,
                ),
              ),
              if (active) ...<Widget>[
                const SizedBox(width: 5),
                Container(
                  width: 6,
                  height: 6,
                  decoration: BoxDecoration(
                    color: palette.gold,
                    shape: BoxShape.circle,
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

class _MakeChip extends StatelessWidget {
  const _MakeChip({
    required this.label,
    required this.selected,
    required this.onTap,
  });

  final String label;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final palette = HarajPalette.of(context);
    return Semantics(
      selected: selected,
      button: true,
      child: Material(
        color: selected ? palette.gold : palette.cardSurface,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(12),
          side: BorderSide(
            color: selected ? palette.gold : palette.navInactive,
          ),
        ),
        child: InkWell(
          onTap: onTap,
          borderRadius: BorderRadius.circular(12),
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16),
            child: Center(
              child: Text(
                label,
                style: TextStyle(
                  fontFamily: HarajTheme.fontFamily,
                  fontSize: 13,
                  fontWeight: selected ? FontWeight.w700 : FontWeight.w600,
                  color: selected ? Colors.white : palette.ink,
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

/// عنوانُ القسم وعدُّه، وفي الطرف الآخر الطورُ المعروض — قائمةٌ تبدّله.
class _SectionTitle extends StatelessWidget {
  const _SectionTitle({
    required this.phase,
    required this.count,
    required this.counts,
    required this.onPhase,
  });

  final AuctionPhase phase;
  final int count;
  final PhaseCounts? counts;
  final void Function(AuctionPhase phase) onPhase;

  String _label(AppLocalizations l10n, AuctionPhase phase) => switch (phase) {
    AuctionPhase.upcoming => l10n.homeTabUpcoming,
    AuctionPhase.active || AuctionPhase.unknown => l10n.homeTabActive,
    AuctionPhase.ended => l10n.homeTabEnded,
  };

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final palette = HarajPalette.of(context);
    final pill = phase == AuctionPhase.active || phase == AuctionPhase.unknown
        ? l10n.homeAvailableCount(count)
        : l10n.homeTabWithCount(_label(l10n, phase), count);

    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 6, 16, 4),
      child: Row(
        children: <Widget>[
          // **يصغر ولا يُقصّ** — «مركبات المظا…» رُئيت على عرض ٣٧٥.
          Flexible(
            child: FittedBox(
              fit: BoxFit.scaleDown,
              alignment: AlignmentDirectional.centerStart,
              child: Text(
                l10n.homeSectionTitle,
                maxLines: 1,
                style: TextStyle(
                  fontFamily: HarajTheme.fontFamily,
                  fontSize: 17,
                  fontWeight: FontWeight.w700,
                  color: palette.ink,
                ),
              ),
            ),
          ),
          const SizedBox(width: 8),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 2),
            decoration: BoxDecoration(
              color: palette.gold.withValues(alpha: 0.08),
              borderRadius: BorderRadius.circular(999),
              border: Border.all(color: palette.gold.withValues(alpha: 0.3)),
            ),
            child: Text(
              pill,
              style: TextStyle(
                fontFamily: HarajTheme.fontFamily,
                fontSize: 11.5,
                fontWeight: FontWeight.w700,
                color: palette.gold,
              ),
            ),
          ),
          const Spacer(),
          PopupMenuButton<AuctionPhase>(
            tooltip: l10n.filterPhase,
            onSelected: onPhase,
            itemBuilder: (context) => <PopupMenuEntry<AuctionPhase>>[
              for (final option in AuctionPhase.tabs)
                PopupMenuItem<AuctionPhase>(
                  value: option,
                  child: Text(
                    counts == null
                        ? _label(l10n, option)
                        : l10n.homeTabWithCount(
                            _label(l10n, option),
                            counts!.of(option),
                          ),
                  ),
                ),
            ],
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: <Widget>[
                Text(
                  _label(l10n, phase),
                  style: TextStyle(
                    fontFamily: HarajTheme.fontFamily,
                    fontSize: 12.5,
                    fontWeight: FontWeight.w600,
                    color: palette.inkMuted,
                  ),
                ),
                Icon(
                  Icons.keyboard_arrow_down_rounded,
                  size: 18,
                  color: palette.inkMuted,
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

/// سطرُ الختام: قاعدةُ المزايدة المغلقة كما هي في الخادم — لا يرى أحدٌ مبلغَ
/// غيره، والأعلى يُعرف عند النهاية.
///
/// **والتصميمُ كتب «تُحفظ بتشفيرٍ آمن وتُفتح آلياً بحضور لجنة المزاد»**، ولا
/// لجنةَ في النظام ولا فتحَ آليّاً بحضورها — فكُتب ما يفعله النظام فعلاً.
class _SealedNote extends StatelessWidget {
  const _SealedNote();

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final palette = HarajPalette.of(context);
    return Center(
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 560),
        child: Container(
          margin: const EdgeInsets.fromLTRB(16, 10, 16, 20),
          padding: const EdgeInsets.fromLTRB(14, 12, 12, 12),
          decoration: BoxDecoration(
            color: palette.cardSurface,
            borderRadius: BorderRadius.circular(16),
            border: Border.all(
              color: palette.navInactive.withValues(alpha: 0.6),
            ),
          ),
          child: Row(
            children: <Widget>[
              Icon(Icons.lock_rounded, size: 20, color: palette.gold),
              const SizedBox(width: 10),
              Expanded(
                child: Text(
                  l10n.homeSealedNote,
                  style: TextStyle(
                    fontFamily: HarajTheme.fontFamily,
                    fontSize: 12.5,
                    color: palette.inkMuted,
                    height: 1.5,
                  ),
                ),
              ),
              const SizedBox(width: 8),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 4),
                decoration: BoxDecoration(
                  color: palette.pageBackground,
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Text(
                  l10n.homeSealedPill,
                  style: TextStyle(
                    fontFamily: HarajTheme.fontFamily,
                    fontSize: 11.5,
                    fontWeight: FontWeight.w700,
                    color: palette.ink,
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
