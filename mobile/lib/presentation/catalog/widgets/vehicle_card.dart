import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../app/theme.dart';
import '../../../domain/catalog/entities/auction_phase.dart';
import '../../../domain/catalog/entities/vehicle_summary.dart';
import '../../../l10n/generated/app_localizations.dart';
import '../../common/money_text.dart';
import '../favourites_controller.dart';
import 'countdown_text.dart';
import 'remote_image.dart';

/// كرت المركبة — **مكوّن واحد، ولا رسم لكرت خارجه** (T708).
///
/// في v1 كانت الصفحة الرئيسية وحدها فيها أربعة مسارات لرسم هذا الكرت وثلاث
/// قوائم حقول، فأي حقل يُضاف للمنتج يظهر في بعضها ويختفي في الباقي **بصمت** —
/// ولم ينتبه أحد حتى سأل عميل لماذا يظهر الممشى في صفحة المزاد ولا يظهر في
/// نتائج البحث. الخلفية سدّت الثغرة نفسها في الفيز 005
/// (`ops/checks/one_vehicle_card.py`)، والويب في الفيز 011
/// (`ops/checks/web_one_vehicle_card.mjs`)، وهذا نظيرهما في التطبيق.
///
/// **صفٌّ لا عمود**: الصورة في جهة، والبيانات في الأخرى. الكرتُ العموديّ الذي
/// كان هنا يعطي صورةً بعرض العمود كلّه فلا يظهر منه في الشاشة إلا كرتٌ ونصف،
/// والصفُّ يُظهر أربعةً — والقائمةُ تُقرأ بالمقارنة بين الكروت لا بكرتٍ واحد.
///
/// **المال على الكرت `adminFeeWithVat` وحده.** التصميم يكتب فوقه «السعر
/// الافتتاحي»، ولا سعرَ افتتاحيّاً في هذا المنتج: المزاد **مغلق** (قرارٌ في
/// `ce013b9`) فالخادم لا يرسل `reserve_price` ولا `bids_count` أصلاً. فبقيت
/// هيئةُ التصميم — تسميةٌ صغيرة فوق رقمٍ عريض — وصدَقت التسمية.
///
/// **«انتهى» يقولها الخادم، والعدّاد يقول «كم بقي» فقط.** الطور يأتي جاهزاً في
/// `phase`، والكرت يطبعه كما وصل؛ ولا يقارن `auctionEndsAt` بساعة الجهاز
/// ليستنتجه. هذا بعينه ما فعله v1: عدّادٌ تنازلي على ساعة العميل كتب «انتهى»
/// على مزادٍ ما زال مفتوحاً لكل من ساعته متقدّمة دقيقتين، فأغلق باب المزايدة
/// أمامه وهو مفتوح.
class VehicleCard extends ConsumerStatefulWidget {
  const VehicleCard({required this.vehicle, this.onTap, super.key});

  final VehicleSummary vehicle;
  final VoidCallback? onTap;

  @override
  ConsumerState<VehicleCard> createState() => _VehicleCardState();
}

class _VehicleCardState extends ConsumerState<VehicleCard> {
  /// حالُ القلب بعد ضغطةٍ **نجحت**، حتى تصل قائمةٌ جديدة من الخادم.
  ///
  /// `null` يعني «لم يُضغط هنا» فيُقرأ من المركبة. ولماذا أصلاً: القائمة التي
  /// تحمل هذا الكرت مبنيّةٌ في الشاشة المضيفة ولا تُعاد قراءتها لضغطة قلب —
  /// وإعادةُ قراءة الصفحة كاملةً عند كل ضغطة تُقفز القائمةَ تحت إصبع من ضغط.
  /// ولا يُكتب إلا **بعد** ردّ الخادم: قلبٌ يمتلئ قبل الردّ ثم يفشل الطلب
  /// يترك العميل يظنّ أنه حفظ ما لم يُحفظ.
  bool? _saved;

  /// طلبٌ جارٍ — يمنع ضغطتين متتاليتين تُلغي ثانيتُهما أولاهما.
  bool _busy = false;

  VehicleSummary get vehicle => widget.vehicle;

  bool get _isFavourite => _saved ?? vehicle.isFavourite;

  Future<void> _toggle() async {
    if (_busy) return;
    setState(() => _busy = true);
    final was = _isFavourite;
    try {
      await ref.read(toggleFavouriteProvider)(
        vehicleId: vehicle.id,
        isFavourite: was,
      );
      if (!mounted) return;
      setState(() {
        _saved = !was;
        _busy = false;
      });
    } on Object {
      // الفشل يُقال ولا يُبتلع: القلب يبقى على حاله، ويظهر سطرٌ يشرح لماذا لم
      // يتغيّر. بلا هذا يضغط العميل ولا يحدث شيء فيظنّ الزرّ معطّلاً.
      if (!mounted) return;
      setState(() => _busy = false);
      final messenger = ScaffoldMessenger.maybeOf(context);
      messenger?.showSnackBar(
        SnackBar(content: Text(AppLocalizations.of(context).favouriteFailed)),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final theme = Theme.of(context);
    final palette = HarajPalette.of(context);

    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 7, 16, 7),
      child: Material(
        color: palette.cardSurface,
        borderRadius: BorderRadius.circular(22),
        clipBehavior: Clip.antiAlias,
        // ظلٌّ خفيفٌ واسع: الكرت أبيض على كريميّ، والفرقُ بينهما وحده لا يكفي
        // ليُقرأ الكرت مرفوعاً عن الصفحة.
        elevation: 1.5,
        shadowColor: palette.brown.withValues(alpha: 0.20),
        child: InkWell(
          onTap: widget.onTap,
          child: Padding(
            padding: const EdgeInsets.all(10),
            child: Row(
              children: <Widget>[
                _Photo(
                  vehicle: vehicle,
                  palette: palette,
                  isFavourite: _isFavourite,
                  busy: _busy,
                  onToggleFavourite: _toggle,
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    mainAxisSize: MainAxisSize.min,
                    children: <Widget>[
                      _TitleRow(
                        title: vehicle.title,
                        palette: palette,
                        theme: theme,
                      ),
                      const SizedBox(height: 8),
                      _Specifications(
                        vehicle: vehicle,
                        palette: palette,
                        l10n: l10n,
                        theme: theme,
                      ),
                      const SizedBox(height: 10),
                      Row(
                        children: <Widget>[
                          // السعر في جهة القراءة الأولى (اليمين في العربية)،
                          // والزرُّ في الطرف الآخر: الرقم يُقرأ قبل أن يُقرَّر،
                          // وزرٌّ يسبق سعرَه يُضغط قبل أن يُعرف الثمن.
                          Flexible(
                            child: _Price(
                              vehicle: vehicle,
                              palette: palette,
                              l10n: l10n,
                              theme: theme,
                            ),
                          ),
                          const SizedBox(width: 8),
                          _DetailsButton(
                            palette: palette,
                            label: l10n.vehicleDetailsAction,
                            onTap: widget.onTap,
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

/// الصورة، وعليها القلب والعدّاد.
class _Photo extends StatelessWidget {
  const _Photo({
    required this.vehicle,
    required this.palette,
    required this.isFavourite,
    required this.busy,
    required this.onToggleFavourite,
  });

  final VehicleSummary vehicle;
  final HarajPalette palette;
  final bool isFavourite;
  final bool busy;
  final VoidCallback onToggleFavourite;

  /// مقاسٌ ثابت لا نسبة: الصورةُ بنسبةٍ من عرض الكرت تتغيّر مع عرض الشاشة،
  /// فيصير للكرت هيئتان — واحدةٌ على جوّالٍ ضيّق وأخرى على لوحيّ.
  static const double _width = 152;
  static const double _height = 130;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final ended = vehicle.phase == AuctionPhase.ended;

    return SizedBox(
      width: _width,
      height: _height,
      child: Stack(
        fit: StackFit.expand,
        children: <Widget>[
          ClipRRect(
            borderRadius: BorderRadius.circular(16),
            // مصغَّرة لا صورة كاملة (قاعدة التصميم 6)، ومفكوكة بضعف عرضها
            // المعروض لا بعرضها الأصلي — يكفي أعلى كثافة نشحن إليها.
            child: RemoteImage(url: vehicle.thumbnailUrl, decodeWidth: 320),
          ),
          // `PositionedDirectional` لا `Positioned`: `end` هي يسارُ الشاشة في
          // العربية ويمينُها في الإنجليزية، والقلب يبقى في الزاوية نفسها من
          // الصورة في الاتجاهين.
          PositionedDirectional(
            top: 6,
            end: 6,
            child: _FavouriteButton(
              isFavourite: isFavourite,
              busy: busy,
              onTap: onToggleFavourite,
              palette: palette,
            ),
          ),
          PositionedDirectional(
            bottom: 6,
            start: 6,
            end: 6,
            // مزادٌ قاله الخادم منتهياً لا عدّاد له: العدّ إلى لحظةٍ مضت يعطي
            // نصّاً عن ساعة الجهاز، والخبر عن المزاد أصدق منه. وطورٌ لا نعرفه
            // يُعامَل معاملة القائم لا المنتهي — الجهل ليس نفياً (المادة ٢-٣).
            child: _TimeBadge(
              palette: palette,
              ended: ended,
              child: ended
                  ? Text(
                      l10n.vehicleAuctionEnded,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: _badgeTextStyle,
                    )
                  : CountdownText(
                      at: vehicle.auctionEndsAt,
                      target: CountdownTarget.end,
                      style: _badgeTextStyle,
                    ),
            ),
          ),
        ],
      ),
    );
  }

  static const TextStyle _badgeTextStyle = TextStyle(
    color: Colors.white,
    fontSize: 10,
    fontWeight: FontWeight.w700,
    height: 1.1,
    fontFamily: HarajTheme.fontFamily,
  );
}

/// حوضُ الوقت الباقي أسفل الصورة.
class _TimeBadge extends StatelessWidget {
  const _TimeBadge({
    required this.palette,
    required this.ended,
    required this.child,
  });

  final HarajPalette palette;
  final bool ended;
  final Widget child;

  @override
  Widget build(BuildContext context) => DecoratedBox(
    decoration: BoxDecoration(
      // المنتهي رماديٌّ بنّيّ لا أخضر: الأخضر يقول «يجري الآن»، وقولُه على
      // مزادٍ أُغلق يدفع العميل ليفتح ما لا يستطيع المزايدة فيه.
      color: (ended ? palette.pillBottom : palette.timerBadge).withValues(
        alpha: 0.92,
      ),
      borderRadius: BorderRadius.circular(9),
    ),
    child: Padding(
      padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 5),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.center,
        mainAxisSize: MainAxisSize.min,
        children: <Widget>[
          Icon(
            ended ? Icons.lock_clock : Icons.access_time_rounded,
            size: 12,
            color: palette.goldOnDark,
          ),
          const SizedBox(width: 4),
          Flexible(child: child),
        ],
      ),
    ),
  );
}

class _FavouriteButton extends StatelessWidget {
  const _FavouriteButton({
    required this.isFavourite,
    required this.busy,
    required this.onTap,
    required this.palette,
  });

  final bool isFavourite;
  final bool busy;
  final VoidCallback onTap;
  final HarajPalette palette;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    // القارئ الصوتيّ يقول الفعل لا الحال: «أضف إلى المفضلة» يقول ما سيحدث عند
    // الضغط، و«مفضلة» تترك السامع لا يدري أهي زرٌّ أم خبر.
    final label = isFavourite ? l10n.favouriteRemove : l10n.favouriteAdd;

    return Semantics(
      button: true,
      label: label,
      child: Material(
        color: Colors.white.withValues(alpha: 0.94),
        shape: const CircleBorder(),
        child: InkWell(
          onTap: busy ? null : onTap,
          customBorder: const CircleBorder(),
          child: Padding(
            padding: const EdgeInsets.all(6),
            child: busy
                // نفس القياس بالضبط: مؤشّرٌ أصغر من الأيقونة يجعل الزرّ ينكمش
                // تحت الإصبع عند كل ضغطة.
                ? SizedBox(
                    width: 18,
                    height: 18,
                    child: Padding(
                      padding: const EdgeInsets.all(2),
                      child: CircularProgressIndicator(
                        strokeWidth: 2,
                        color: palette.gold,
                      ),
                    ),
                  )
                : Icon(
                    isFavourite
                        ? Icons.favorite_rounded
                        : Icons.favorite_border_rounded,
                    size: 18,
                    color: isFavourite ? palette.gold : palette.brown,
                  ),
          ),
        ),
      ),
    );
  }
}

class _TitleRow extends StatelessWidget {
  const _TitleRow({
    required this.title,
    required this.palette,
    required this.theme,
  });

  final String title;
  final HarajPalette palette;
  final ThemeData theme;

  @override
  Widget build(BuildContext context) => Row(
    children: <Widget>[
      // **قرصٌ بأيقونة، لا شعارُ الماركة.** التصميم يضع شعار BMW وتويوتا،
      // ولا ملفّات لها في الحزمة — وجلبُها من الشبكة يعني شعاراً لا يظهر بلا
      // اتصال (قاعدة العرض 7)، وحقوقَ استعمالٍ لكل علامة على حدة.
      Container(
        width: 30,
        height: 30,
        decoration: BoxDecoration(
          color: palette.goldMuted,
          shape: BoxShape.circle,
        ),
        child: Icon(
          Icons.directions_car_rounded,
          size: 17,
          color: palette.gold,
        ),
      ),
      const SizedBox(width: 8),
      Expanded(
        child: Text(
          title,
          maxLines: 1,
          // القصّ لا الالتفاف: سطرٌ ثانٍ للاسم يدفع السعر والزرّ خارج الكرت.
          overflow: TextOverflow.ellipsis,
          style: theme.textTheme.titleSmall?.copyWith(
            color: palette.brown,
            fontWeight: FontWeight.w700,
          ),
        ),
      ),
    ],
  );
}

/// سنةُ الصنع والحالةُ واللونُ والممشى — أربعتُها من الخادم.
///
/// **`Wrap` لا `Row`:** أربع خانات بنصوصها العربية أعرض من عمود الكرت على
/// أضيق جوّال، و`Row` تقصّ الرابعة بلا أن يعرف أحد أنها كانت هناك.
class _Specifications extends StatelessWidget {
  const _Specifications({
    required this.vehicle,
    required this.palette,
    required this.l10n,
    required this.theme,
  });

  final VehicleSummary vehicle;
  final HarajPalette palette;
  final AppLocalizations l10n;
  final ThemeData theme;

  @override
  Widget build(BuildContext context) {
    final odometer = vehicle.odometerKm;

    return Wrap(
      spacing: 12,
      runSpacing: 6,
      children: <Widget>[
        _Chip(
          icon: Icons.calendar_today_rounded,
          text: '${vehicle.year}',
          palette: palette,
          theme: theme,
        ),
        _Chip(
          icon: Icons.fact_check_outlined,
          text: vehicle.conditionLabel,
          palette: palette,
          theme: theme,
        ),
        _Chip(
          icon: Icons.palette_outlined,
          text: vehicle.colourLabel,
          palette: palette,
          theme: theme,
        ),
        // الممشى قد يغيب، والغياب لا يُعرض صفراً ولا خانةً فارغة.
        if (odometer != null)
          _Chip(
            icon: Icons.speed_rounded,
            text: l10n.vehicleOdometerShort(odometer),
            palette: palette,
            theme: theme,
          ),
      ],
    );
  }
}

class _Chip extends StatelessWidget {
  const _Chip({
    required this.icon,
    required this.text,
    required this.palette,
    required this.theme,
  });

  final IconData icon;
  final String text;
  final HarajPalette palette;
  final ThemeData theme;

  @override
  Widget build(BuildContext context) => Row(
    mainAxisSize: MainAxisSize.min,
    children: <Widget>[
      Icon(icon, size: 13, color: palette.inkMuted),
      const SizedBox(width: 4),
      Text(
        text,
        style: theme.textTheme.labelSmall?.copyWith(
          color: palette.inkMuted,
          fontWeight: FontWeight.w500,
        ),
      ),
    ],
  );
}

class _Price extends StatelessWidget {
  const _Price({
    required this.vehicle,
    required this.palette,
    required this.l10n,
    required this.theme,
  });

  final VehicleSummary vehicle;
  final HarajPalette palette;
  final AppLocalizations l10n;
  final ThemeData theme;

  @override
  Widget build(BuildContext context) => Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    mainAxisSize: MainAxisSize.min,
    children: <Widget>[
      Text(
        l10n.vehicleAdminFeeWithVat,
        maxLines: 1,
        overflow: TextOverflow.ellipsis,
        style: theme.textTheme.labelSmall?.copyWith(color: palette.inkMuted),
      ),
      const SizedBox(height: 1),
      // نصّاً كما وصل، بلا فواصل ولا تقريب (المادة ١-٦): الرقم الذي يراه
      // العميل هو الرقم الذي يقابله قيدٌ في الدفتر.
      MoneyText(
        vehicle.adminFeeWithVat,
        style: theme.textTheme.titleMedium?.copyWith(
          color: palette.brown,
          fontWeight: FontWeight.w700,
        ),
      ),
    ],
  );
}

class _DetailsButton extends StatelessWidget {
  const _DetailsButton({
    required this.palette,
    required this.label,
    required this.onTap,
  });

  final HarajPalette palette;
  final String label;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) => DecoratedBox(
    decoration: BoxDecoration(
      gradient: LinearGradient(
        begin: Alignment.topRight,
        end: Alignment.bottomLeft,
        colors: <Color>[palette.pillTop, palette.pillBottom],
      ),
      borderRadius: BorderRadius.circular(20),
    ),
    child: Material(
      color: Colors.transparent,
      child: InkWell(
        // **الزرّ يفتح ما يفتحه الكرت كلّه** ولا مقصدَ ثانياً له: مقصدان
        // لفعلٍ واحد يفترقان عند أول تغييرٍ في المسار (المادة ٤-٥). وهو هنا
        // لأن الكرتَ المضغوطَ كلَّه لا يُرى أنه قابلٌ للضغط.
        onTap: onTap,
        borderRadius: BorderRadius.circular(20),
        splashColor: palette.goldMuted,
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 11, vertical: 8),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: <Widget>[
              Icon(Icons.gavel_rounded, size: 13, color: palette.goldOnDark),
              const SizedBox(width: 5),
              Text(
                label,
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 11,
                  fontWeight: FontWeight.w700,
                  fontFamily: HarajTheme.fontFamily,
                ),
              ),
              const SizedBox(width: 2),
              // يسارٌ لا يمين: «إلى الأمام» في العربية هو اليسار، وسهمٌ يشير
              // إلى اليمين يُقرأ «رجوع».
              Icon(
                Icons.chevron_left_rounded,
                size: 16,
                color: Colors.white.withValues(alpha: 0.75),
              ),
            ],
          ),
        ),
      ),
    ),
  );
}
