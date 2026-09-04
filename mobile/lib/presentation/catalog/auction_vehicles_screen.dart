import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app/providers.dart';
import '../../app/router.dart';
import '../../domain/catalog/entities/vehicle_query.dart';
import '../../domain/catalog/entities/vehicle_summary.dart';
import '../../domain/common/failure.dart';
import '../../domain/common/snapshot.dart';
import '../../l10n/generated/app_localizations.dart';
import '../common/snapshot_view.dart';
import 'widgets/vehicle_filters.dart';
import 'widgets/vehicle_results.dart';

/// قائمة مركبات المزاد: بحث وترشيح وترقيم صفحات — **كلها من الخادم** (T708).
///
/// لا يوجد في هذا الملف موضعٌ واحد يرشّح قائمةً أو يرتّبها أو يقصّها. المعايير
/// تُرسَل كما هي، وما يعود يُعرض كما عاد. السبب عملي لا عقائدي: ترشيحٌ يحسبه
/// التطبيق نسخةٌ ثانية من «أي المركبات تطابق؟»، وأول تعديل على الأصل يجعل
/// الويب والتطبيق يجيبان عن البحث نفسه بجوابين، فيسأل العميل أيّهما الصادق ولا
/// جواب.
///
/// **بلا تمويه** (قاعدة التصميم 5 في الفيز 008): `BackdropFilter` في عنصر قائمة
/// يقتل التمرير على الأجهزة المتوسطة، وH2 يقيس ذلك بمئتي مركبة.
class AuctionVehiclesScreen extends ConsumerStatefulWidget {
  const AuctionVehiclesScreen({required this.auctionId, super.key});

  final String auctionId;

  @override
  ConsumerState<AuctionVehiclesScreen> createState() =>
      _AuctionVehiclesScreenState();
}

class _AuctionVehiclesScreenState extends ConsumerState<AuctionVehiclesScreen> {
  /// كم مركبة قبل نهاية القائمة نطلب الصفحة التالية.
  static const int _prefetchThreshold = 3;

  VehicleQuery _query = const VehicleQuery();
  AsyncValue<Snapshot<VehiclePage>> _first =
      const AsyncValue<Snapshot<VehiclePage>>.loading();

  final List<VehicleSummary> _vehicles = <VehicleSummary>[];
  int _totalCount = 0;
  bool _hasMore = false;
  bool _loadingMore = false;
  Failure? _moreFailure;

  /// كل بحثٍ جديد يبطل ما قبله. بلا هذا العدّاد يستطيع ردٌّ بطيء لبحثٍ قديم أن
  /// يصل بعد ردّ البحث الجديد فيدهسه، فيرى العميل نتائج كلمةٍ محاها.
  int _generation = 0;

  @override
  void initState() {
    super.initState();
    _reload();
  }

  Future<void> _reload() async {
    final generation = ++_generation;
    setState(() {
      _first = const AsyncValue<Snapshot<VehiclePage>>.loading();
      _moreFailure = null;
      // وينزل هنا علَم «أُحمّل الآن» أيضاً: الطلب الذي أبطله هذا البحث يعود
      // صامتاً عند حارس الجيل أدناه، فلا يبلغ السطر الذي كان سينزله. علَمٌ بقي
      // مرفوعاً يصير قفلاً — كل طلب صفحةٍ تالية يرجع من أول سطر، والدوّامة في
      // ذيل القائمة تدور على طلبٍ لن يحدث، فلا يرى العميل من نتائج ترشيحه إلا
      // صفحتها الأولى حتى يغلق الشاشة ويفتحها.
      _loadingMore = false;
    });

    try {
      final snapshot = await ref.read(loadAuctionVehiclesProvider)(
        widget.auctionId,
        _query.atPage(1),
      );
      if (!mounted || generation != _generation) return;
      setState(() {
        _first = AsyncValue<Snapshot<VehiclePage>>.data(snapshot);
        _vehicles
          ..clear()
          ..addAll(snapshot.value.vehicles);
        _totalCount = snapshot.value.totalCount;
        _hasMore = snapshot.value.hasMore;
      });
    } on Object catch (error, stackTrace) {
      // `Object` لا `Failure`: عطبٌ غير متوقّع يجب أن يظهر مصنَّفاً في الشاشة،
      // لا أن يُفلت من فجوة غير متزامنة فيسقط في السجلّ وحده والشاشة تدور.
      if (!mounted || generation != _generation) return;
      setState(
        () =>
            _first = AsyncValue<Snapshot<VehiclePage>>.error(error, stackTrace),
      );
    }
  }

  Future<void> _loadMore() async {
    if (_loadingMore || !_hasMore || _moreFailure != null) return;
    final generation = _generation;
    setState(() => _loadingMore = true);

    final next = _query.page + 1;
    try {
      final snapshot = await ref.read(loadAuctionVehiclesProvider)(
        widget.auctionId,
        _query.atPage(next),
      );
      if (!mounted || generation != _generation) return;
      setState(() {
        _query = _query.atPage(next);
        _vehicles.addAll(snapshot.value.vehicles);
        _totalCount = snapshot.value.totalCount;
        _hasMore = snapshot.value.hasMore;
        _loadingMore = false;
      });
    } on Object catch (error, stackTrace) {
      if (!mounted || generation != _generation) return;
      // فشل صفحةٍ تالية لا يمحو ما وصل: يبقى المعروض معروضاً ويظهر الخطأ في
      // ذيل القائمة بزرّ إعادة محاولة.
      setState(() {
        _moreFailure = error is Failure
            ? error
            : UnexpectedFailure(error, stackTrace: stackTrace);
        _loadingMore = false;
      });
    }
  }

  void _apply(VehicleQuery query) {
    setState(() => _query = query.atPage(1));
    _reload();
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);

    return Scaffold(
      appBar: AppBar(title: Text(l10n.vehiclesTitle)),
      body: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: <Widget>[
          // النموذج فوق الحالة لا داخلها: عميلٌ رشّح فأخطأ الخادم يجب أن يبقى
          // قادراً على إزالة الترشيح، لا أن يواجه شاشة خطأ بلا مخرج.
          VehicleFilters(query: _query, onApply: _apply),
          Expanded(
            child: SnapshotView<VehiclePage>(
              state: _first,
              onRetry: _reload,
              // نفس مكوّن النتائج الذي تعرضه الرئيسية، بتخطيط قائمة لا شبكة:
              // العدّ والترقيم والحالة الفارغة وفشل الصفحة التالية سلوكٌ واحد،
              // ونسختان منه تفترقان عند أول إصلاح يُنسى في إحداهما.
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
                emptyMessage: l10n.vehiclesEmpty,
                prefetchThreshold: _prefetchThreshold,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
