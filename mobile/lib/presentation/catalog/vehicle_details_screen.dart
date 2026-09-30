import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart' show DateFormat;

import '../../app/providers.dart';
import '../../app/theme.dart';
import '../../domain/catalog/entities/auction_phase.dart';
import '../../domain/catalog/entities/vehicle_summary.dart';
import '../../l10n/generated/app_localizations.dart';
import '../common/money_text.dart';
import 'favourites_controller.dart';
import 'widgets/remote_image.dart';
import 'widgets/vehicle_bid_sheet.dart';

/// يفتح صفحةَ تفاصيل المركبة فوق القشرة — بلا الشريط السفليّ، فللصفحة شريطُها.
///
/// و[siblings] القائمةُ التي فُتحت منها (الرئيسية، المفضلة…): بها يُسحب إلى
/// السابقة والتالية. وبلا قائمةٍ تُفتح المركبةُ وحدها.
Future<void> openVehicleDetails(
  BuildContext context, {
  required VehicleSummary vehicle,
  List<VehicleSummary>? siblings,
}) {
  final list = (siblings != null && siblings.any((v) => v.id == vehicle.id))
      ? List<VehicleSummary>.of(siblings)
      : <VehicleSummary>[vehicle];
  final index = list.indexWhere((v) => v.id == vehicle.id);
  return Navigator.of(context, rootNavigator: true).push(
    MaterialPageRoute<void>(
      builder: (_) => VehicleDetailsScreen(vehicles: list, initialIndex: index),
    ),
  );
}

/// المركباتُ صفحاتٌ متتالية — **السحبُ يميناً أو شمالاً ينقل إلى السابقة
/// والتالية** بطلب المالك (٣٠ سبتمبر ٢٠٢٦): «طريقة سهلة للتنقّل بين
/// السيارات… أسحب من أيّ منطقة ما فيهاش صورة».
///
/// **`PageView` داخل `PageView`**: معرضُ الصور صفحاتٌ أفقيّةٌ أيضاً، والسحبُ
/// الذي يبدأ عليه يأخذه هو (يقلّب الصور)، والذي يبدأ في أيّ مكانٍ آخر تأخذه
/// الصفحاتُ الخارجيّة (تنقل المركبة). ذلك تحكيمُ الإيماءات في Flutter نفسه:
/// أعمقُ متعرّفٍ يفوز بما بدأ عليه — فلا منطقةَ تُحسب باليد.
///
/// وفي الشاشة العربيّة التاليةُ تأتي من الشمال: السحبُ يميناً ← التالية، كما
/// تُقلَّب صفحاتُ كتابٍ عربيّ.
class VehicleDetailsScreen extends StatefulWidget {
  const VehicleDetailsScreen({
    required this.vehicles,
    required this.initialIndex,
    super.key,
  });

  final List<VehicleSummary> vehicles;
  final int initialIndex;

  @override
  State<VehicleDetailsScreen> createState() => _VehicleDetailsScreenState();
}

class _VehicleDetailsScreenState extends State<VehicleDetailsScreen> {
  late final PageController _vehicles = PageController(
    initialPage: widget.initialIndex,
  );
  late int _current = widget.initialIndex;

  @override
  void dispose() {
    _vehicles.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final palette = HarajPalette.of(context);
    return Scaffold(
      backgroundColor: palette.pageBackground,
      body: SafeArea(
        bottom: false,
        child: PageView.builder(
          controller: _vehicles,
          itemCount: widget.vehicles.length,
          onPageChanged: (index) => setState(() => _current = index),
          itemBuilder: (context, index) => _VehicleDetailsPage(
            key: ValueKey<String>(widget.vehicles[index].id),
            vehicle: widget.vehicles[index],
            position: widget.vehicles.length > 1
                ? '${index + 1} / ${widget.vehicles.length}'
                : null,
            active: index == _current,
          ),
        ),
      ),
    );
  }
}

/// صفحةُ تفاصيل المركبة — **مكانَ نافذة المزايدة** بطلب المالك (٣٠ سبتمبر
/// ٢٠٢٦) وعلى تصميمه: معرضُ صور، وبطاقةُ الاسم والموعد، والمواصفات، وقواعدُ
/// المزايدة المغلقة، ومراحلُ المزاد، وشريطٌ سفليّ بزرّ «زايد الآن».
///
/// **والبياناتُ بياناتُنا لا بياناتُ التصميم** (بأمره): نافذةُ v1 كانت تعرض
/// الطرازَ والسنةَ واللونَ والممشى والمدينةَ والحالةَ والرسومَ والسعرَ مع
/// الضريبة — وهي حقولُ كرت الخادم نفسُها، ومعها الصورُ من `/images/`. وسقط من
/// التصميم ما لا يرسله الخادم: المحرّكُ وناقلُ الحركة والدفعُ والفرشُ الداخليّ،
/// و«تقرير الفحص» ودرجتُه وملفُّه، و«جولة 360»، و«المزايدة الحالية» — المزادُ
/// مغلقٌ فلا سعرَ جارياً يُعرض (قرارٌ في `ce013b9`).
class _VehicleDetailsPage extends ConsumerStatefulWidget {
  const _VehicleDetailsPage({
    required this.vehicle,
    required this.position,
    required this.active,
    super.key,
  });

  final VehicleSummary vehicle;

  /// «٣ / ١٨» — موضعُ المركبة في قائمتها، أو `null` حين تُفتح وحدها.
  final String? position;

  /// الصفحةُ المعروضة الآن. الجارتان تُبنيان مسبقاً للسحب، ولا تطلبان صورَهما
  /// إلا حين تصلهما العين.
  final bool active;

  @override
  ConsumerState<_VehicleDetailsPage> createState() =>
      _VehicleDetailsPageState();
}

class _VehicleDetailsPageState extends ConsumerState<_VehicleDetailsPage> {
  final PageController _pages = PageController();
  int _page = 0;

  /// حالُ القلب بعد ضغطةٍ **نجحت** — لا قبل ردّ الخادم.
  bool? _saved;
  bool _busy = false;

  VehicleSummary get vehicle => widget.vehicle;
  bool get _isFavourite => _saved ?? vehicle.isFavourite;

  @override
  void dispose() {
    _pages.dispose();
    super.dispose();
  }

  Future<void> _toggleFavourite() async {
    if (_busy) return;
    setState(() => _busy = true);
    final was = _isFavourite;
    final l10n = AppLocalizations.of(context);
    final messenger = ScaffoldMessenger.maybeOf(context);
    try {
      await ref.read(toggleFavouriteProvider)(
        vehicleId: vehicle.id,
        isFavourite: was,
      );
      if (mounted) setState(() => _saved = !was);
    } on Object {
      messenger?.showSnackBar(SnackBar(content: Text(l10n.favouriteFailed)));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  /// المشاركةُ نسخُ الاسم والرقم — لا `share_plus` في التبعيّات.
  Future<void> _share() async {
    final l10n = AppLocalizations.of(context);
    final messenger = ScaffoldMessenger.maybeOf(context);
    await Clipboard.setData(
      ClipboardData(text: '${vehicle.title} — ${vehicle.reference}'),
    );
    messenger?.showSnackBar(SnackBar(content: Text(l10n.vehicleShareCopied)));
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final palette = HarajPalette.of(context);
    // الصورُ من نداءٍ ثانٍ؛ وحتى يصل تُعرض المصغَّرةُ وحدها — صفحةٌ لا تنتظر
    // صورَها لتُقرأ.
    final detail = widget.active
        ? ref.watch(vehicleProvider(vehicle.id)).asData?.value.value
        : null;
    final images = (detail?.imageUrls.isNotEmpty ?? false)
        ? detail!.imageUrls
        : <String>[if (vehicle.thumbnailUrl != null) vehicle.thumbnailUrl!];
    final locale = Localizations.localeOf(context).toLanguageTag();
    final endsAt = vehicle.auctionEndsAt.toLocal();
    final when = DateFormat('EEEE HH:mm', locale).format(endsAt);

    return ColoredBox(
      color: palette.pageBackground,
      child: Column(
        children: <Widget>[
          _TopBar(
            // **اسمُ المركبة في رأس الصفحة** مكانَ «تفاصيل المركبة» — بطلب
            // المالك (٣٠ سبتمبر ٢٠٢٦).
            title: '${vehicle.title} ${vehicle.year}',
            lot: widget.position == null
                ? l10n.vehicleLotPosition(vehicle.lotNumber)
                : '${l10n.vehicleLotPosition(vehicle.lotNumber)} • ${widget.position}',
            isFavourite: _isFavourite,
            onBack: () => Navigator.of(context).maybePop(),
            onShare: _share,
            onFavourite: _toggleFavourite,
          ),
          Expanded(
            child: ListView(
              padding: const EdgeInsets.only(bottom: 16),
              children: <Widget>[
                _Gallery(
                  images: images,
                  controller: _pages,
                  page: _page,
                  onPage: (page) => setState(() => _page = page),
                  lotBadge:
                      '${l10n.vehicleLotPosition(vehicle.lotNumber)} • ${vehicle.reference}',
                  sealedBadge: l10n.vehicleSealedEnvelope,
                ),
                if (images.length > 1)
                  _Thumbnails(
                    images: images,
                    page: _page,
                    onTap: (index) => _pages.animateToPage(
                      index,
                      duration: const Duration(milliseconds: 260),
                      curve: Curves.easeOut,
                    ),
                  ),
                const SizedBox(height: 12),
                _Section(
                  child: _Headline(
                    vehicle: vehicle,
                    when: when,
                    l10n: l10n,
                    palette: palette,
                  ),
                ),
                _Section(
                  title: l10n.vehicleSpecifications,
                  child: _Specs(vehicle: vehicle, l10n: l10n),
                ),
                // **قواعدُ المزايدة ومراحلُ المزاد أُلغيتا** بطلب المالك.
              ],
            ),
          ),
          _BottomBar(vehicle: vehicle, l10n: l10n),
        ],
      ),
    );
  }
}

class _TopBar extends StatelessWidget {
  const _TopBar({
    required this.title,
    required this.lot,
    required this.isFavourite,
    required this.onBack,
    required this.onShare,
    required this.onFavourite,
  });

  final String title;
  final String lot;
  final bool isFavourite;
  final VoidCallback onBack;
  final VoidCallback onShare;
  final VoidCallback onFavourite;

  @override
  Widget build(BuildContext context) {
    final palette = HarajPalette.of(context);
    return Container(
      padding: const EdgeInsets.fromLTRB(8, 6, 8, 6),
      decoration: BoxDecoration(
        color: palette.cardSurface,
        border: Border(bottom: BorderSide(color: palette.navInactive)),
      ),
      child: Row(
        children: <Widget>[
          IconButton(
            onPressed: onBack,
            icon: Icon(Icons.arrow_forward_rounded, color: palette.ink),
            tooltip: MaterialLocalizations.of(context).backButtonTooltip,
          ),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
            decoration: BoxDecoration(
              color: palette.pageBackground,
              borderRadius: BorderRadius.circular(8),
            ),
            child: Text(
              lot,
              style: TextStyle(
                fontFamily: HarajTheme.fontFamily,
                fontSize: 11.5,
                fontWeight: FontWeight.w700,
                color: palette.inkMuted,
              ),
            ),
          ),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              title,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: TextStyle(
                fontFamily: HarajTheme.fontFamily,
                fontSize: 16,
                fontWeight: FontWeight.w700,
                color: palette.ink,
              ),
            ),
          ),
          IconButton(
            onPressed: onShare,
            icon: Icon(Icons.share_outlined, color: palette.ink, size: 21),
          ),
          IconButton(
            onPressed: onFavourite,
            icon: Icon(
              isFavourite
                  ? Icons.favorite_rounded
                  : Icons.favorite_border_rounded,
              color: isFavourite ? const Color(0xFFEF4444) : palette.ink,
              size: 22,
            ),
          ),
        ],
      ),
    );
  }
}

class _Gallery extends StatelessWidget {
  const _Gallery({
    required this.images,
    required this.controller,
    required this.page,
    required this.onPage,
    required this.lotBadge,
    required this.sealedBadge,
  });

  final List<String> images;
  final PageController controller;
  final int page;
  final ValueChanged<int> onPage;
  final String lotBadge;
  final String sealedBadge;

  @override
  Widget build(BuildContext context) {
    return AspectRatio(
      aspectRatio: 4 / 3,
      child: Stack(
        fit: StackFit.expand,
        children: <Widget>[
          if (images.isEmpty)
            const ColoredBox(color: Color(0xFF0E2136))
          else
            PageView.builder(
              controller: controller,
              itemCount: images.length,
              onPageChanged: onPage,
              itemBuilder: (context, index) =>
                  RemoteImage(url: images[index], decodeWidth: 1200),
            ),
          PositionedDirectional(
            top: 10,
            start: 10,
            child: _Badge(text: lotBadge),
          ),
          PositionedDirectional(
            top: 10,
            end: 10,
            child: _Badge(text: sealedBadge, icon: Icons.lock_rounded),
          ),
          if (images.length > 1)
            PositionedDirectional(
              bottom: 10,
              end: 10,
              child: _Badge(text: '${page + 1} / ${images.length}', ltr: true),
            ),
        ],
      ),
    );
  }
}

class _Badge extends StatelessWidget {
  const _Badge({required this.text, this.icon, this.ltr = false});

  final String text;
  final IconData? icon;
  final bool ltr;

  @override
  Widget build(BuildContext context) => DecoratedBox(
    decoration: BoxDecoration(
      color: const Color(0xFF0E2136).withValues(alpha: 0.8),
      borderRadius: BorderRadius.circular(9),
    ),
    child: Padding(
      padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 4),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: <Widget>[
          if (icon != null) ...<Widget>[
            Icon(icon, size: 13, color: Colors.white),
            const SizedBox(width: 4),
          ],
          Text(
            text,
            textDirection: ltr ? TextDirection.ltr : null,
            style: const TextStyle(
              fontFamily: HarajTheme.fontFamily,
              fontSize: 11.5,
              fontWeight: FontWeight.w700,
              color: Colors.white,
            ),
          ),
        ],
      ),
    ),
  );
}

class _Thumbnails extends StatelessWidget {
  const _Thumbnails({
    required this.images,
    required this.page,
    required this.onTap,
  });

  final List<String> images;
  final int page;
  final ValueChanged<int> onTap;

  @override
  Widget build(BuildContext context) {
    final palette = HarajPalette.of(context);
    return Container(
      height: 72,
      color: palette.cardSurface,
      child: ListView.separated(
        scrollDirection: Axis.horizontal,
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
        itemCount: images.length,
        separatorBuilder: (_, _) => const SizedBox(width: 8),
        itemBuilder: (context, index) => GestureDetector(
          onTap: () => onTap(index),
          child: Container(
            width: 76,
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(10),
              border: Border.all(
                color: index == page ? palette.gold : Colors.transparent,
                width: 2,
              ),
            ),
            clipBehavior: Clip.antiAlias,
            child: RemoteImage(url: images[index], decodeWidth: 200),
          ),
        ),
      ),
    );
  }
}

/// بطاقةُ قسمٍ بيضاء بعنوانٍ اختياريّ.
class _Section extends StatelessWidget {
  const _Section({required this.child, this.title});

  final Widget child;
  final String? title;

  @override
  Widget build(BuildContext context) {
    final palette = HarajPalette.of(context);
    return Container(
      margin: const EdgeInsets.fromLTRB(16, 0, 16, 12),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: palette.cardSurface,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: palette.navInactive.withValues(alpha: 0.7)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: <Widget>[
          if (title != null) ...<Widget>[
            Text(
              title!,
              style: TextStyle(
                fontFamily: HarajTheme.fontFamily,
                fontSize: 16,
                fontWeight: FontWeight.w700,
                color: palette.ink,
              ),
            ),
            const SizedBox(height: 12),
          ],
          child,
        ],
      ),
    );
  }
}

/// الماركةُ والرقمُ المرجعيّ، والاسمُ والسنة، والموقع، وموعدُ إغلاق السومات.
class _Headline extends StatelessWidget {
  const _Headline({
    required this.vehicle,
    required this.when,
    required this.l10n,
    required this.palette,
  });

  final VehicleSummary vehicle;
  final String when;
  final AppLocalizations l10n;
  final HarajPalette palette;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: <Widget>[
        Text(
          <String>[
            if (vehicle.make.isNotEmpty) vehicle.make,
            vehicle.reference,
          ].join(' • '),
          style: TextStyle(
            fontFamily: HarajTheme.fontFamily,
            fontSize: 12.5,
            fontWeight: FontWeight.w600,
            color: palette.gold,
          ),
        ),
        const SizedBox(height: 6),
        Row(
          children: <Widget>[
            Icon(Icons.location_on_outlined, size: 16, color: palette.gold),
            const SizedBox(width: 4),
            Expanded(
              child: Text(
                vehicle.location,
                style: TextStyle(
                  fontFamily: HarajTheme.fontFamily,
                  fontSize: 13,
                  color: palette.inkMuted,
                ),
              ),
            ),
          ],
        ),
      ],
    );
  }
}

/// المواصفات — **حقولُ نافذة v1 نفسُها** من كرت الخادم، في شبكةٍ من عمودين.
class _Specs extends StatelessWidget {
  const _Specs({required this.vehicle, required this.l10n});

  final VehicleSummary vehicle;
  final AppLocalizations l10n;

  @override
  Widget build(BuildContext context) {
    final odometer = vehicle.odometerKm;
    // **ترتيبُ v1 وحقولُه**: نافذةُ «مواصفات المركبة» (`specsModal`) — المعرّف،
    // والموديل، ورقمُ الهيكل، والسنة، وحالةُ المركبة، وحالةُ المحرّك،
    // والمفاتيح، والوقود — ثمّ ما في نافذة المزايدة: اللونُ والممشى والمدينة،
    // ومعها نوعُ اللوحة (شارةُ كرت v1) والناقل. والغيابُ شرطةٌ كما في v1، لا
    // صفرٌ ولا خانةٌ تختفي فتتزحزح الشبكة.
    String or(String value) => value.trim().isEmpty ? '—' : value;
    final tiles = <(IconData, String, String)>[
      (Icons.tag_rounded, l10n.vehicleSpecId, vehicle.reference),
      (Icons.badge_outlined, l10n.vehicleSpecModel, vehicle.title),
      (Icons.qr_code_2_rounded, l10n.vehicleSpecVin, or(vehicle.vin)),
      (Icons.calendar_today_outlined, l10n.vehicleSpecYear, '${vehicle.year}'),
      (
        Icons.build_circle_outlined,
        l10n.vehicleSpecCondition,
        or(vehicle.conditionLabel),
      ),
      (
        Icons.settings_suggest_outlined,
        l10n.vehicleSpecEngine,
        or(vehicle.runsStatus),
      ),
      (Icons.key_outlined, l10n.vehicleSpecKeys, or(vehicle.keyStatus)),
      (
        Icons.local_gas_station_outlined,
        l10n.vehicleSpecFuel,
        or(vehicle.fuelTypeLabel),
      ),
      (
        Icons.settings_outlined,
        l10n.vehicleSpecTransmission,
        or(vehicle.transmissionLabel),
      ),
      (Icons.palette_outlined, l10n.vehicleSpecColour, or(vehicle.colourLabel)),
      (
        Icons.speed_rounded,
        l10n.vehicleSpecOdometer,
        odometer == null ? '—' : l10n.vehicleOdometerShort(odometer),
      ),
      (
        Icons.credit_card_outlined,
        l10n.vehicleSpecPlateType,
        or(vehicle.plateTypeLabel),
      ),
      (
        Icons.location_city_outlined,
        l10n.vehicleSpecCity,
        or(vehicle.location),
      ),
    ];
    return LayoutBuilder(
      builder: (context, box) {
        final width = (box.maxWidth - 10) / 2;
        return Wrap(
          spacing: 10,
          runSpacing: 10,
          children: <Widget>[
            for (final (icon, label, value) in tiles)
              SizedBox(
                width: width,
                child: _SpecTile(icon: icon, label: label, value: value),
              ),
          ],
        );
      },
    );
  }
}

class _SpecTile extends StatelessWidget {
  const _SpecTile({
    required this.icon,
    required this.label,
    required this.value,
  });

  final IconData icon;
  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    final palette = HarajPalette.of(context);
    return Container(
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: palette.navInactive.withValues(alpha: 0.8)),
      ),
      child: Row(
        children: <Widget>[
          Container(
            width: 36,
            height: 36,
            decoration: BoxDecoration(
              color: palette.gold.withValues(alpha: 0.08),
              borderRadius: BorderRadius.circular(10),
            ),
            child: Icon(icon, size: 19, color: palette.gold),
          ),
          const SizedBox(width: 8),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text(
                  label,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: TextStyle(
                    fontFamily: HarajTheme.fontFamily,
                    fontSize: 11,
                    color: palette.inkMuted,
                  ),
                ),
                FittedBox(
                  fit: BoxFit.scaleDown,
                  alignment: AlignmentDirectional.centerStart,
                  child: Text(
                    value,
                    maxLines: 1,
                    style: TextStyle(
                      fontFamily: HarajTheme.fontFamily,
                      fontSize: 14,
                      fontWeight: FontWeight.w700,
                      color: palette.ink,
                    ),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

/// الشريطُ السفليّ: الرسومُ مع الضريبة في جهة، وزرُّ «زايد الآن» في الأخرى.
///
/// **لا «مزايدة حالية»**: المزادُ مغلقٌ، فأعلى عرضٍ لا يُعرف قبل النهاية. وما
/// يُعرف سلفاً ويدفعه الفائزُ فوق سعره هو الرسوم — فهي الرقمُ هنا.
class _BottomBar extends StatelessWidget {
  const _BottomBar({required this.vehicle, required this.l10n});

  final VehicleSummary vehicle;
  final AppLocalizations l10n;

  @override
  Widget build(BuildContext context) {
    final palette = HarajPalette.of(context);
    final open = vehicle.phase != AuctionPhase.ended;
    return Container(
      padding: EdgeInsets.fromLTRB(
        16,
        10,
        16,
        10 + MediaQuery.paddingOf(context).bottom,
      ),
      decoration: BoxDecoration(
        color: palette.cardSurface,
        border: Border(top: BorderSide(color: palette.navInactive)),
      ),
      child: Row(
        children: <Widget>[
          Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Text(
                l10n.vehicleAdminFeeWithVat,
                style: TextStyle(
                  fontFamily: HarajTheme.fontFamily,
                  fontSize: 11.5,
                  color: palette.inkMuted,
                ),
              ),
              MoneyText(
                vehicle.adminFeeWithVat,
                style: TextStyle(
                  fontFamily: HarajTheme.fontFamily,
                  fontSize: 18,
                  fontWeight: FontWeight.w700,
                  color: palette.ink,
                ),
              ),
            ],
          ),
          const SizedBox(width: 14),
          Expanded(
            child: FilledButton.icon(
              onPressed: open
                  ? () => showVehicleBidEntry(context, vehicle: vehicle)
                  : null,
              icon: const Icon(Icons.gavel_rounded, size: 18),
              label: Text(
                open ? l10n.vehicleSealedBidAction : l10n.vehicleAuctionEnded,
              ),
              style: FilledButton.styleFrom(
                backgroundColor: palette.gold,
                foregroundColor: Colors.white,
                minimumSize: const Size.fromHeight(50),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(14),
                ),
                textStyle: const TextStyle(
                  fontFamily: HarajTheme.fontFamily,
                  fontSize: 15,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
