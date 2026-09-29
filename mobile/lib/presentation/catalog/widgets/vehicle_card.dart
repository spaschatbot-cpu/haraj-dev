import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../app/theme.dart';
import '../../../domain/catalog/entities/auction_phase.dart';
import '../../../domain/catalog/entities/vehicle_summary.dart';
import '../../../l10n/generated/app_localizations.dart';
import '../favourites_controller.dart';
import 'countdown_text.dart';
import 'remote_image.dart';
import 'vehicle_bid_sheet.dart';

/// كرت المركبة — **مكوّن واحد، ولا رسم لكرت خارجه** (T708).
///
/// في v1 كانت الصفحة الرئيسية وحدها فيها أربعة مسارات لرسم هذا الكرت وثلاث
/// قوائم حقول، فأي حقل يُضاف للمنتج يظهر في بعضها ويختفي في الباقي **بصمت**.
/// فهذا الكرتُ وحده يُرسم في الرئيسية والمفضلة ومركبات المزاد.
///
/// **هيئةُ تصميم المالك** (٣٠ سبتمبر ٢٠٢٦): الصورةُ يميناً بأربع شاراتٍ عليها
/// (الموقف، والمفضّلة، والسنة، و«سري»)، وفي الجهة الأخرى الاسمُ وحالتُه،
/// والموقع، وأربعُ خاناتٍ في شبكة، وزرُّ «زايد الآن» بعرضها.
///
/// **والخاناتُ من حقول الخادم لا من التصميم.** التصميمُ يكتب المحرّكَ وناقلَ
/// الحركة، والخادمُ لا يرسلهما في الكرت؛ فالأربعُ: الممشى، واللون، والحالة،
/// وكم بقي على الإغلاق — وهو ما يسأله المزايدُ أوّلاً.
///
/// **«انتهى» يقولها الخادم** (`phase`)، والعدّاد يقول «كم بقي» فقط؛ ولا يُقارن
/// `auctionEndsAt` بساعة الجهاز ليستنتجه — عدّادُ v1 على ساعة العميل كتب
/// «انتهى» على مزادٍ مفتوحٍ لمن ساعته متقدّمة دقيقتين.
class VehicleCard extends StatelessWidget {
  const VehicleCard({required this.vehicle, super.key});

  final VehicleSummary vehicle;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final palette = HarajPalette.of(context);

    return Center(
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: _maxWidth),
        child: Padding(
          padding: const EdgeInsets.fromLTRB(16, 7, 16, 7),
          child: Material(
            color: palette.cardSurface,
            surfaceTintColor: Colors.transparent,
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(22),
              side: BorderSide(
                color: palette.navInactive.withValues(alpha: 0.55),
              ),
            ),
            clipBehavior: Clip.antiAlias,
            elevation: 2,
            shadowColor: palette.ink.withValues(alpha: 0.12),
            child: InkWell(
              // الكرتُ كلُّه يفتح صندوقَ المزايدة (٩ سبتمبر ٢٠٢٦)، والزرُّ يقول
              // ماذا يحدث عند الضغط.
              onTap: () => showVehicleBidSheet(context, vehicle: vehicle),
              child: Padding(
                padding: const EdgeInsets.all(12),
                child: IntrinsicHeight(
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: <Widget>[
                      // أوّلُ ابنٍ في الصفّ هو **اليمين** في العربية.
                      Expanded(
                        flex: 44,
                        child: ConstrainedBox(
                          constraints: const BoxConstraints(minHeight: 190),
                          child: _Photo(vehicle: vehicle, l10n: l10n),
                        ),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        flex: 56,
                        child: _Details(
                          vehicle: vehicle,
                          palette: palette,
                          l10n: l10n,
                          onBid: () =>
                              showVehicleBidSheet(context, vehicle: vehicle),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

/// أوسعُ ما يبلغه الكرت — وعمودُ الشبكة في `vehicle_results.dart` يقرؤه.
const double _maxWidth = 560;

class _Details extends StatelessWidget {
  const _Details({
    required this.vehicle,
    required this.palette,
    required this.l10n,
    required this.onBid,
  });

  final VehicleSummary vehicle;
  final HarajPalette palette;
  final AppLocalizations l10n;
  final VoidCallback onBid;

  @override
  Widget build(BuildContext context) {
    final odometer = vehicle.odometerKm;
    final ended = vehicle.phase == AuctionPhase.ended;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: <Widget>[
        Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Expanded(
              child: Text(
                vehicle.title,
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
                style: TextStyle(
                  fontFamily: HarajTheme.fontFamily,
                  fontSize: 15,
                  fontWeight: FontWeight.w700,
                  color: palette.ink,
                  height: 1.3,
                ),
              ),
            ),
            const SizedBox(width: 6),
            _StatusPill(phase: vehicle.phase, l10n: l10n, palette: palette),
          ],
        ),
        const SizedBox(height: 4),
        Row(
          children: <Widget>[
            Icon(Icons.location_on_rounded, size: 14, color: palette.gold),
            const SizedBox(width: 3),
            Expanded(
              child: Text(
                vehicle.location,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: TextStyle(
                  fontFamily: HarajTheme.fontFamily,
                  fontSize: 12,
                  color: palette.inkMuted,
                  height: 1.3,
                ),
              ),
            ),
          ],
        ),
        const SizedBox(height: 10),
        // أربعُ خاناتٍ في صفّين — الممشى قد يغيب، والغيابُ لا يُعرض صفراً:
        // «٠ كم» ادّعاءٌ لم يقله أحد، فتأخذ السنةُ مكانه.
        Row(
          children: <Widget>[
            Expanded(
              child: odometer != null
                  ? _Fact(
                      icon: Icons.speed_rounded,
                      text: l10n.vehicleOdometerShort(odometer),
                      palette: palette,
                    )
                  : _Fact(
                      icon: Icons.calendar_today_rounded,
                      text: '${vehicle.year}',
                      palette: palette,
                    ),
            ),
            const SizedBox(width: 6),
            Expanded(
              child: _Fact(
                icon: Icons.palette_outlined,
                text: vehicle.colourLabel,
                palette: palette,
              ),
            ),
          ],
        ),
        const SizedBox(height: 6),
        Row(
          children: <Widget>[
            Expanded(
              child: _Fact(
                icon: Icons.directions_car_outlined,
                text: vehicle.conditionLabel,
                palette: palette,
              ),
            ),
            const SizedBox(width: 6),
            Expanded(
              child: _Fact(
                icon: Icons.timer_outlined,
                palette: palette,
                text: ended ? l10n.vehicleAuctionEnded : '',
                // **`FittedBox` يصغّر العدّاد ولا يقصّه**: «يوم 20:39:55» أعرضُ
                // من نصف عمود البيانات على هاتفٍ بعرض ٣٧٥ بعشرين بكسلاً —
                // رُئي في كونسول المالك (RenderFlex overflowed by 20 pixels).
                child: ended
                    ? null
                    : FittedBox(
                        fit: BoxFit.scaleDown,
                        alignment: AlignmentDirectional.centerStart,
                        child: CountdownText(
                          at: vehicle.auctionEndsAt,
                          target: CountdownTarget.end,
                          digital: true,
                          style: _factStyle(palette),
                        ),
                      ),
              ),
            ),
          ],
        ),
        const SizedBox(height: 12),
        _BidButton(
          label: l10n.vehicleSealedBidAction,
          palette: palette,
          onTap: onBid,
        ),
      ],
    );
  }
}

TextStyle _factStyle(HarajPalette palette) => TextStyle(
  fontFamily: HarajTheme.fontFamily,
  fontSize: 11.5,
  fontWeight: FontWeight.w600,
  color: palette.ink,
  height: 1.2,
);

/// حالةُ المركبة — خضراءُ «متاحة» في المزاد الجاري، وإلا اسمُ طورها.
class _StatusPill extends StatelessWidget {
  const _StatusPill({
    required this.phase,
    required this.l10n,
    required this.palette,
  });

  final AuctionPhase phase;
  final AppLocalizations l10n;
  final HarajPalette palette;

  static const Color _okInk = Color(0xFF047857);
  static const Color _okSurface = Color(0xFFECFDF5);
  static const Color _okLine = Color(0xFFA7F3D0);

  @override
  Widget build(BuildContext context) {
    final (label, ink, surface, line) = switch (phase) {
      AuctionPhase.active || AuctionPhase.unknown => (
        l10n.vehicleStatusOpen,
        _okInk,
        _okSurface,
        _okLine,
      ),
      AuctionPhase.upcoming => (
        l10n.homeTabUpcoming,
        palette.gold,
        palette.gold.withValues(alpha: 0.08),
        palette.gold.withValues(alpha: 0.3),
      ),
      AuctionPhase.ended => (
        l10n.homeTabEnded,
        palette.inkMuted,
        palette.pageBackground,
        palette.navInactive,
      ),
    };
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(
        color: surface,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: line),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: <Widget>[
          Icon(Icons.check_circle_rounded, size: 12, color: ink),
          const SizedBox(width: 4),
          Text(
            label,
            style: TextStyle(
              fontFamily: HarajTheme.fontFamily,
              fontSize: 11,
              fontWeight: FontWeight.w700,
              color: ink,
              height: 1.2,
            ),
          ),
        ],
      ),
    );
  }
}

/// خانةُ مواصفة: أيقونةٌ رماديّة ونصٌّ، بإطارٍ فاتح.
class _Fact extends StatelessWidget {
  const _Fact({
    required this.icon,
    required this.text,
    required this.palette,
    this.child,
  });

  final IconData icon;
  final String text;
  final HarajPalette palette;

  /// محتوىً حيٌّ بدل النصّ — العدّاد.
  final Widget? child;

  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 7),
    decoration: BoxDecoration(
      borderRadius: BorderRadius.circular(10),
      border: Border.all(color: palette.navInactive.withValues(alpha: 0.7)),
    ),
    child: Row(
      children: <Widget>[
        Icon(icon, size: 14, color: palette.inkMuted),
        const SizedBox(width: 5),
        Expanded(
          child:
              child ??
              // **يصغر ولا يُقصّ**: «41,000 كم» كانت تُقرأ «41,00…» في نصف
              // عمودٍ على هاتفٍ بعرض ٣٧٥ — رُئي في اللقطة.
              FittedBox(
                fit: BoxFit.scaleDown,
                alignment: AlignmentDirectional.centerStart,
                child: Text(text, maxLines: 1, style: _factStyle(palette)),
              ),
        ),
      ],
    ),
  );
}

/// «زايد الآن» — أزرقُ ممتدٌّ بعرض البيانات. كان «قدّم سومتك السرية» كما في
/// التصميم، وبدّله المالك في اليوم نفسه (٣٠ سبتمبر ٢٠٢٦).
///
/// **يفتح نافذةَ المزايدة** ولا يزايد: زرٌّ في قائمةٍ يزايد مباشرةً أقصرُ
/// طريقٍ إلى مزايدةٍ بالخطأ، والحدُّ الأدنى وشروطُ الأهليّة في النافذة.
class _BidButton extends StatelessWidget {
  const _BidButton({
    required this.label,
    required this.palette,
    required this.onTap,
  });

  final String label;
  final HarajPalette palette;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => Material(
    borderRadius: BorderRadius.circular(14),
    clipBehavior: Clip.antiAlias,
    color: Colors.transparent,
    child: Ink(
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(14),
        gradient: LinearGradient(
          colors: <Color>[palette.gold, palette.goldDeep],
        ),
      ),
      child: InkWell(
        onTap: onTap,
        child: SizedBox(
          height: 44,
          child: Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: <Widget>[
              const Icon(Icons.gavel_rounded, size: 17, color: Colors.white),
              const SizedBox(width: 8),
              Flexible(
                child: Text(
                  label,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                    fontFamily: HarajTheme.fontFamily,
                    fontSize: 14,
                    fontWeight: FontWeight.w700,
                    color: Colors.white,
                    height: 1.2,
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    ),
  );
}

/// الصورة بأربع شارات: الموقفُ أعلى اليمين، والقلبُ أعلى اليسار، والسنةُ
/// أسفل اليسار، و«سري» أسفل اليمين.
///
/// **والقلبُ عاد** بتصميم المالك (٣٠ سبتمبر ٢٠٢٦) بعد أن مُحي في ٩ سبتمبر:
/// التصميمُ الأحدثُ يعلو.
class _Photo extends StatelessWidget {
  const _Photo({required this.vehicle, required this.l10n});

  final VehicleSummary vehicle;
  final AppLocalizations l10n;

  @override
  Widget build(BuildContext context) => ClipRRect(
    borderRadius: BorderRadius.circular(16),
    child: Stack(
      fit: StackFit.expand,
      children: <Widget>[
        RemoteImage(url: vehicle.thumbnailUrl, decodeWidth: 500),
        PositionedDirectional(
          top: 8,
          start: 8,
          child: _DarkBadge(
            child: Text(
              l10n.vehicleLotPosition(vehicle.lotNumber),
              style: _badgeText,
            ),
          ),
        ),
        PositionedDirectional(
          top: 6,
          end: 6,
          child: _FavouriteButton(vehicle: vehicle),
        ),
        PositionedDirectional(
          bottom: 8,
          end: 8,
          child: _DarkBadge(child: Text('${vehicle.year}', style: _badgeText)),
        ),
        PositionedDirectional(
          bottom: 8,
          start: 8,
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: <Widget>[
              const Icon(
                Icons.shield_rounded,
                size: 14,
                color: Color(0xFF34D399),
              ),
              const SizedBox(width: 3),
              Text(
                l10n.vehicleSealedBadge,
                style: _badgeText.copyWith(
                  color: const Color(0xFF34D399),
                  shadows: const <Shadow>[
                    Shadow(color: Colors.black54, blurRadius: 6),
                  ],
                ),
              ),
            ],
          ),
        ),
      ],
    ),
  );
}

const TextStyle _badgeText = TextStyle(
  fontFamily: HarajTheme.fontFamily,
  fontSize: 11,
  fontWeight: FontWeight.w700,
  color: Colors.white,
  height: 1.2,
);

/// حوضٌ داكنٌ شبه معتم — الشارةُ تقع على صورةٍ لا نعرف لونها.
class _DarkBadge extends StatelessWidget {
  const _DarkBadge({required this.child});

  final Widget child;

  @override
  Widget build(BuildContext context) => DecoratedBox(
    decoration: BoxDecoration(
      color: const Color(0xFF0E2136).withValues(alpha: 0.82),
      borderRadius: BorderRadius.circular(8),
    ),
    child: Padding(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      child: child,
    ),
  );
}

/// القلب على الصورة. حالُه بعد ضغطةٍ **نجحت** فقط — قلبٌ يمتلئ قبل ردّ الخادم
/// ثم يفشل الطلب يترك العميل يظنّ أنه حفظ ما لم يُحفظ.
class _FavouriteButton extends ConsumerStatefulWidget {
  const _FavouriteButton({required this.vehicle});

  final VehicleSummary vehicle;

  @override
  ConsumerState<_FavouriteButton> createState() => _FavouriteButtonState();
}

class _FavouriteButtonState extends ConsumerState<_FavouriteButton> {
  bool? _saved;
  bool _busy = false;

  bool get _isFavourite => _saved ?? widget.vehicle.isFavourite;

  Future<void> _toggle() async {
    if (_busy) return;
    setState(() => _busy = true);
    final was = _isFavourite;
    final l10n = AppLocalizations.of(context);
    final messenger = ScaffoldMessenger.maybeOf(context);
    try {
      await ref.read(toggleFavouriteProvider)(
        vehicleId: widget.vehicle.id,
        isFavourite: was,
      );
      if (!mounted) return;
      setState(() => _saved = !was);
    } on Object {
      messenger?.showSnackBar(SnackBar(content: Text(l10n.favouriteFailed)));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final on = _isFavourite;
    return Semantics(
      button: true,
      label: on ? l10n.favouriteRemove : l10n.favouriteAdd,
      child: Material(
        color: Colors.black.withValues(alpha: 0.35),
        shape: const CircleBorder(),
        child: InkWell(
          customBorder: const CircleBorder(),
          onTap: _toggle,
          child: Padding(
            padding: const EdgeInsets.all(6),
            child: Icon(
              on ? Icons.favorite_rounded : Icons.favorite_border_rounded,
              size: 17,
              color: on ? const Color(0xFFF87171) : Colors.white,
            ),
          ),
        ),
      ),
    );
  }
}
