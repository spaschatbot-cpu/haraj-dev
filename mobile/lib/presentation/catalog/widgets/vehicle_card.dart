import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../app/theme.dart';
import '../../../domain/catalog/entities/auction_phase.dart';
import '../../../domain/catalog/entities/vehicle_summary.dart';
import '../../../l10n/generated/app_localizations.dart';
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
    final palette = HarajPalette.of(context);

    return Center(
      child: ConstrainedBox(
        // **بعرضٍ محدود لا بعرض الشاشة** — نفس حدّ لوحة الترحيب ومفتاح
        // الأطوار فوقه، فتقف الثلاثةُ على عمودٍ واحد.
        constraints: const BoxConstraints(maxWidth: 440),
        child: Padding(
          // هامشٌ ١٤ لا ٢٠: عرضُ كرت v1 على شاشة ٣١٧ نحو ٢٨٩ — أي أربعةَ
          // عشرَ من كل جهة.
          padding: const EdgeInsets.fromLTRB(14, 5, 14, 5),
          child: Material(
            color: palette.cardSurface,
            borderRadius: BorderRadius.circular(_radius),
            // **`antiAlias` وليس تدويرَ الصورة بيدها**: الصورة تلامس حافّة
            // الكرت من ثلاث جهات، فقصُّها هو ما يدوّر زاويتيها — وتدويرٌ
            // ثانٍ عليها يترك بين القوسين هلالاً أبيض.
            clipBehavior: Clip.antiAlias,
            elevation: 1.5,
            shadowColor: palette.brown.withValues(alpha: 0.18),
            child: InkWell(
              onTap: widget.onTap,
              child: ConstrainedBox(
                // **١٤٠ حدّاً أدنى لا مقاساً مفروضاً** — والقسمة ٤٧:٥٣.
                // مقاسُ كرت v1 مقروءاً من `img.car-photo` في أدوات المتصفّح:
                // `135.5×140` على شاشة ٣١٧، و١٣٥٫٥ من ٢٨٩ = ٤٧٪.
                //
                // وكان `height: 140` مفروضاً، **ففاض العمود ٤٨ بكسلاً**
                // وسقط زرُّ المزايدة من الشاشة: ارتفاعُ النصّ العربيّ لا
                // يُحسب بضرب حجم الخطّ في `height` — للمحرف صعودٌ ونزول
                // يزيدان عليه، والفرق يتراكم على خمسة أسطر.
                //
                // والحدُّ الأدنى يعطي مقاسَ v1 حين يسعه المحتوى، ويكبر حين
                // لا يسعه — وكرتٌ أطول بقليل خيرٌ من زرٍّ لا يُرى.
                constraints: const BoxConstraints(minHeight: _height),
                child: IntrinsicHeight(
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: <Widget>[
                      // **الصورة أوّلاً** — وأوّلُ ابنٍ في الصفّ هو **اليمين**
                      // في العربية. بقرار المالك في ٩ سبتمبر ٢٠٢٦؛ كانت
                      // البيانات أوّلاً فوقعت الصورة يساراً.
                      //
                      // **نصفٌ لكلٍّ**: `flex` واحدٌ لهما، فالقسمة نصفان في كل
                      // عرض.
                      Expanded(
                        flex: 47,
                        child: _Photo(
                          vehicle: vehicle,
                          palette: palette,
                          l10n: l10n,
                          isFavourite: _isFavourite,
                          busy: _busy,
                          onToggleFavourite: _toggle,
                        ),
                      ),
                      Expanded(
                        flex: 53,
                        child: Padding(
                          padding: const EdgeInsets.fromLTRB(9, 7, 10, 7),
                          child: _Details(
                            vehicle: vehicle,
                            palette: palette,
                            l10n: l10n,
                            onBid: widget.onTap,
                          ),
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

const double _radius = 18;

/// ارتفاع الكرت — مقاسُ v1 كما قرأته أدوات المتصفّح.
const double _height = 140;

/// نصفُ البيانات: الاسم ومرجعُه، ثم ثلاثُ خاناتٍ، ثم الحالةُ والموقع، ثم
/// العدّاد، ثم زرّ المزايدة.
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
  final VoidCallback? onBid;

  @override
  Widget build(BuildContext context) {
    final odometer = vehicle.odometerKm;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      // **`spaceBetween` لا فراغاتٌ مكتوبة**: الارتفاع يأتي من الحدّ الأدنى
      // (١٤٠) أو من المحتوى أيّهما أكبر، فتوزيعُ الفضلة عليه يملأه تماماً.
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: <Widget>[
        // ١ — الاسم، وعلى طرفه الرقمُ المرجعيّ في حوضٍ داكن.
        Row(
          children: <Widget>[
            Expanded(
              child: Text(
                vehicle.title,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: TextStyle(
                  fontFamily: HarajTheme.fontFamily,
                  fontSize: 14,
                  fontWeight: FontWeight.w700,
                  color: palette.brown,
                  height: 1.2,
                ),
              ),
            ),
            const SizedBox(width: 6),
            _ReferenceChip(reference: vehicle.reference, palette: palette),
          ],
        ),
        // ٢ — ثلاثُ خاناتٍ، **الأيقونةُ فوق القيمة** كما في v1.
        //
        // فوقها لا بجانبها: بجانبها يصير عرضُ الخانة أيقونةً وكلمةً، وثلاثُ
        // خاناتٍ كذلك لا تسع نصفَ كرتٍ عرضُه ١٥٠ — فتُقصّ الكلمات إلى
        // حرفين. وفوقها يصير عرضُ الخانة عرضَ كلمتها وحدها.
        Row(
          children: <Widget>[
            Flexible(
              child: _Fact(
                icon: Icons.calendar_today_rounded,
                value: '${vehicle.year}',
                palette: palette,
              ),
            ),
            const SizedBox(width: 4),
            Flexible(
              child: _Fact(
                icon: Icons.palette_outlined,
                value: vehicle.colourLabel,
                palette: palette,
              ),
            ),
            // الممشى قد يغيب، والغياب لا يُعرض صفراً: «٠ كم» ادّعاءٌ لم
            // يقله أحد — فتبقى خانتان.
            if (odometer != null) ...<Widget>[
              const SizedBox(width: 4),
              Flexible(
                child: _Fact(
                  icon: Icons.speed_rounded,
                  value: l10n.vehicleOdometerShort(odometer),
                  palette: palette,
                ),
              ),
            ],
          ],
        ),
        // ٣ — الحالة.
        _IconText(
          icon: Icons.report_problem_outlined,
          text: vehicle.conditionLabel,
          palette: palette,
        ),
        // ٤ — الموقع **في سطره وحده**.
        //
        // كان معها في سطرٍ واحد كما في v1، فبقي له نصفُ السطر — و«الرياض /
        // طريق الحائر» لا يُقرأ في نصف سطرٍ عرضُه ١٦٧: يظهر «الرياض / طريق
        // ال…». وسطرٌ كامل يسعه، وهذا ثمنُه ستةَ عشرَ بكسلاً في الارتفاع.
        _IconText(
          icon: Icons.place_outlined,
          text: vehicle.location,
          palette: palette,
          flexible: true,
        ),
        // ٤ — العدّاد.
        _Countdown(vehicle: vehicle, palette: palette, l10n: l10n),
        // ٥ — زرّ المزايدة.
        _BidButton(
          label: l10n.vehicleBidAction,
          palette: palette,
          onTap: onBid,
        ),
      ],
    );
  }
}

/// حوضُ الرقم المرجعيّ — داكنٌ صغير بجانب الاسم.
class _ReferenceChip extends StatelessWidget {
  const _ReferenceChip({required this.reference, required this.palette});

  final String reference;
  final HarajPalette palette;

  @override
  Widget build(BuildContext context) => DecoratedBox(
    decoration: BoxDecoration(
      color: palette.heroTop,
      borderRadius: BorderRadius.circular(6),
    ),
    child: Padding(
      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
      child: Text(
        reference,
        // **`ltr`**: `#13466` رقمٌ بعلامةٍ قبله، وترتيبُه في سياقٍ عربيّ
        // ينقلب فتصير العلامةُ بعده.
        textDirection: TextDirection.ltr,
        maxLines: 1,
        style: TextStyle(
          fontFamily: HarajTheme.fontFamily,
          fontSize: 11,
          fontWeight: FontWeight.w700,
          color: palette.navInactive,
          height: 1.3,
        ),
      ),
    ),
  );
}

/// خانةُ مواصفةٍ واحدة: **الأيقونة فوق القيمة**، بحدٍّ رفيع — هيئةُ v1.
class _Fact extends StatelessWidget {
  const _Fact({required this.icon, required this.value, required this.palette});

  final IconData icon;
  final String value;
  final HarajPalette palette;

  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 4),
    decoration: BoxDecoration(
      borderRadius: BorderRadius.circular(7),
      border: Border.all(color: palette.gold.withValues(alpha: 0.45)),
    ),
    child: Column(
      mainAxisSize: MainAxisSize.min,
      children: <Widget>[
        Icon(icon, size: 12, color: palette.gold),
        const SizedBox(height: 2),
        Text(
          value,
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
          style: TextStyle(
            fontFamily: HarajTheme.fontFamily,
            fontSize: 11,
            fontWeight: FontWeight.w700,
            color: palette.brown,
            height: 1.2,
          ),
        ),
      ],
    ),
  );
}

/// أيقونةٌ ونصٌّ خافتان — تُستعمل مرّتين في سطرٍ واحد: الحالة، ثم الموقع.
class _IconText extends StatelessWidget {
  const _IconText({
    required this.icon,
    required this.text,
    required this.palette,
    this.flexible = false,
  });

  final IconData icon;
  final String text;
  final HarajPalette palette;

  /// هل يُقصّ النصّ عند ضيق السطر.
  ///
  /// **ليس دائماً**: `Expanded` حول نصٍّ قصيرٍ يمدّ عرضه إلى آخر السطر
  /// فيدفع ما بعده، وهو عكسُ المراد في صفٍّ من عنصرين.
  final bool flexible;

  @override
  Widget build(BuildContext context) {
    final label = Text(
      text,
      maxLines: 1,
      overflow: TextOverflow.ellipsis,
      style: TextStyle(
        fontFamily: HarajTheme.fontFamily,
        fontSize: 11.5,
        fontWeight: FontWeight.w600,
        // أغمقُ من `inkMuted`: الخافتُ يصلح لسطرٍ طويل يُلمح، لا لكلمتين
        // تحملان الحالةَ والموقع.
        color: palette.brown.withValues(alpha: 0.75),
        height: 1.3,
      ),
    );

    return Row(
      mainAxisSize: MainAxisSize.min,
      children: <Widget>[
        Icon(icon, size: 13, color: palette.gold),
        const SizedBox(width: 4),
        if (flexible) Flexible(child: label) else label,
      ],
    );
  }
}

/// حوضُ العدّاد — أرقامٌ بحدٍّ ذهبيّ، كما في v1.
class _Countdown extends StatelessWidget {
  const _Countdown({
    required this.vehicle,
    required this.palette,
    required this.l10n,
  });

  final VehicleSummary vehicle;
  final HarajPalette palette;
  final AppLocalizations l10n;

  @override
  Widget build(BuildContext context) {
    // **«انتهى» يقولها الخادم** (`phase`)، والعدّاد يقول «كم بقي» فقط. وطورٌ
    // لا نعرفه يُعامَل معاملة القائم لا المنتهي — الجهل ليس نفياً
    // (المادة ٢-٣). هذا بعينه ما فعله v1: عدّادٌ على ساعة العميل كتب
    // «انتهى» على مزادٍ مفتوحٍ لمن ساعته متقدّمة دقيقتين.
    final ended = vehicle.phase == AuctionPhase.ended;
    final style = TextStyle(
      fontFamily: HarajTheme.fontFamily,
      fontSize: 13.5,
      fontWeight: FontWeight.w700,
      color: ended ? palette.inkMuted : palette.goldDeep,
      height: 1.3,
      letterSpacing: 0.6,
    );

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(vertical: 4, horizontal: 8),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(7),
        color: ended
            ? palette.pageBackground
            : Color.alphaBlend(
                palette.gold.withValues(alpha: 0.10),
                palette.cardSurface,
              ),
        border: Border.all(
          color: palette.gold.withValues(alpha: ended ? 0.20 : 0.55),
        ),
      ),
      child: Align(
        alignment: AlignmentDirectional.center,
        child: ended
            ? Text(l10n.vehicleAuctionEnded, maxLines: 1, style: style)
            : CountdownText(
                at: vehicle.auctionEndsAt,
                target: CountdownTarget.end,
                digital: true,
                style: style,
              ),
      ),
    );
  }
}

/// زرّ «مزايدة» — ذهبيٌّ ممتدٌّ بعرض نصف البيانات.
///
/// **يفتح صفحة المركبة** لا صندوقَ مزايدةٍ في الكرت: المزايدة تحتاج الرصيد
/// والحدَّ الأدنى وشروطَ الأهلية، وكلُّها في الصفحة. وزرٌّ في قائمةٍ يفتح
/// حواراً يزايد مباشرةً هو أقصرُ طريقٍ إلى مزايدةٍ بالخطأ.
class _BidButton extends StatelessWidget {
  const _BidButton({
    required this.label,
    required this.palette,
    required this.onTap,
  });

  final String label;
  final HarajPalette palette;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) => Material(
    borderRadius: BorderRadius.circular(9),
    clipBehavior: Clip.antiAlias,
    color: Colors.transparent,
    child: Ink(
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(9),
        gradient: LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: <Color>[palette.gold, palette.goldDeep],
        ),
      ),
      child: InkWell(
        onTap: onTap,
        child: SizedBox(
          width: double.infinity,
          height: 30,
          child: Center(
            child: Text(
              label,
              style: TextStyle(
                fontFamily: HarajTheme.fontFamily,
                fontSize: 13.5,
                fontWeight: FontWeight.w700,
                // **شبه أسود على الذهبيّ لا أبيض**: الأبيض على `#B8860B`
                // نسبتُه ٣٫٣:١ وهي دون الحدّ، وهذا نحو ٧:١.
                color: palette.heroBottom,
                height: 1.2,
              ),
            ),
          ),
        ),
      ),
    ),
  );
}

/// نصفُ الصورة — ممتدٌّ إلى حوافّ الكرت، وعليه شارةُ اللوت والقلب.
class _Photo extends StatelessWidget {
  const _Photo({
    required this.vehicle,
    required this.palette,
    required this.l10n,
    required this.isFavourite,
    required this.busy,
    required this.onToggleFavourite,
  });

  final VehicleSummary vehicle;
  final HarajPalette palette;
  final AppLocalizations l10n;
  final bool isFavourite;
  final bool busy;
  final VoidCallback onToggleFavourite;

  @override
  Widget build(BuildContext context) => Stack(
    fit: StackFit.expand,
    children: <Widget>[
      // مصغَّرة لا صورة كاملة (قاعدة التصميم 6)، ومفكوكة بضعف عرضها المعروض
      // لا بعرضها الأصلي — يكفي أعلى كثافة نشحن إليها.
      RemoteImage(url: vehicle.thumbnailUrl, decodeWidth: 400),
      // `PositionedDirectional` لا `Positioned`: `end` هي يسارُ الشاشة في
      // العربية ويمينُها في الإنجليزية، فتبقى الشارةُ في زاوية الصورة
      // البعيدة عن البيانات في الاتجاهين.
      PositionedDirectional(
        top: 6,
        end: 6,
        child: _LotBadge(
          label: l10n.vehicleLotPosition(vehicle.lotNumber),
          palette: palette,
        ),
      ),
      // القلب في الزاوية الملاصقة للبيانات — **ولا وجود له في v1**: المفضلة
      // ميزةٌ في هذا الإصدار وحده، وحذفُها لتطابق الشكل يحذف ميزةً تعمل.
      PositionedDirectional(
        bottom: 6,
        start: 6,
        child: _FavouriteButton(
          isFavourite: isFavourite,
          busy: busy,
          onTap: onToggleFavourite,
          palette: palette,
        ),
      ),
    ],
  );
}

/// شارةُ «الموقف ٧» على الصورة.
class _LotBadge extends StatelessWidget {
  const _LotBadge({required this.label, required this.palette});

  final String label;
  final HarajPalette palette;

  @override
  Widget build(BuildContext context) => DecoratedBox(
    decoration: BoxDecoration(
      // شبه معتمة لا شفّافة: الشارةُ تقع على صورةٍ لا نعرف لونها، وحوضٌ
      // شفّاف على سيّارةٍ بيضاء يمحو نصَّه.
      color: palette.heroTop.withValues(alpha: 0.88),
      borderRadius: BorderRadius.circular(7),
    ),
    child: Padding(
      padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 3),
      child: Text(
        label,
        maxLines: 1,
        style: TextStyle(
          fontFamily: HarajTheme.fontFamily,
          fontSize: 10,
          fontWeight: FontWeight.w700,
          color: palette.goldOnDark,
          height: 1.3,
        ),
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
