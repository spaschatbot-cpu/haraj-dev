import 'package:flutter/material.dart';

import '../../../app/router.dart';
import '../../../app/theme.dart';
import '../../../domain/catalog/entities/auction_phase.dart';
import '../../../domain/catalog/entities/vehicle_summary.dart';
import '../../../l10n/generated/app_localizations.dart';
import 'countdown_text.dart';
import 'remote_image.dart';
import 'vehicle_bid_sheet.dart';

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
class VehicleCard extends StatelessWidget {
  const VehicleCard({required this.vehicle, super.key});

  final VehicleSummary vehicle;

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
              // **الكرتُ كلُّه يفتح صندوقَ المزايدة** بطلب المالك في ٩ سبتمبر
              // ٢٠٢٦؛ كان يفتح صفحةَ المركبة، وحُذفت الصفحةُ يومَها.
              onTap: () => showVehicleBidSheet(
                context,
                vehicle: vehicle,
                onEnterAuction: () => Routes.goToBid(context, vehicle.id),
              ),
              child: ConstrainedBox(
                // **حدٌّ أدنى لا مقاسٌ مفروض** — والقسمة ٤٧:٥٣، مقاسُ كرت
                // v1 مقروءاً من `img.car-photo` في أدوات المتصفّح:
                // `135.5×140` على شاشة ٣١٧، و١٣٥٫٥ من ٢٨٩ = ٤٧٪.
                //
                // كانت ٤٢:٥٨ ساعةً واحدة حين كان النصُّ يُقصّ. وردَّها
                // أمران معاً بطلب المالك في ٩ سبتمبر ٢٠٢٦: الصورةُ أوسع،
                // والرقمُ المرجعيّ غادر سطرَ الاسم إلى الصورة — فما خسره
                // العمودُ من عرضٍ ردَّه اتّساعُ سطرِ الاسم.
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
                        ),
                      ),
                      Expanded(
                        flex: 53,
                        child: Padding(
                          padding: const EdgeInsets.fromLTRB(7, 6, 8, 6),
                          child: _Details(
                            vehicle: vehicle,
                            palette: palette,
                            l10n: l10n,
                            // الزرُّ والكرتُ يفتحان الشيءَ نفسه. والزرُّ باقٍ
                            // لأنه هو ما يقول للعميل **ماذا يحدث** عند
                            // الضغط؛ ومساحةٌ قابلةٌ للضغط بلا زرٍّ عليها لا
                            // يجرّبها إلا من خمّن.
                            onBid: () => showVehicleBidSheet(
                              context,
                              vehicle: vehicle,
                              onEnterAuction: () =>
                                  Routes.goToBid(context, vehicle.id),
                            ),
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

/// ارتفاع الكرت — حدٌّ أدنى لا مقاسٌ مفروض.
///
/// كان ١٤٠، مقاسَ كرت v1 كما قرأته أدوات المتصفّح (`135.5×140`). ونزل إلى
/// ١٢٦ بطلب المالك في ٩ سبتمبر ٢٠٢٦ بعد أن جُمع الموقعُ مع الحالة في سطر،
/// ثم إلى ١٤٤ ليسع فاصلَي الاسم والعدّاد وحشوةَ سطر الموقع.
const double _height = 144;

/// نصفُ البيانات: الاسم ومرجعُه، ثم ثلاثُ خاناتٍ، ثم الحالةُ والموقع في
/// سطر، ثم العدّاد، ثم زرّ المزايدة — ترتيبُ v1.
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
      // **توسيطٌ لا تراصٌّ على الجهة** بطلب المالك في ٩ سبتمبر ٢٠٢٦: الاسمُ
      // وحده في سطره، والخاناتُ الثلاث كتلةٌ أضيقُ من العمود، وسطرُ الحالة
      // والموقع كذلك — وثلاثتُها متراصّةً يميناً تترك على اليسار فراغاً
      // مثلَّثاً يُقرأ خللاً في المحاذاة لا فراغاً مقصوداً.
      crossAxisAlignment: CrossAxisAlignment.center,
      // **`spaceBetween` لا فراغاتٌ مكتوبة**: الارتفاع يأتي من الحدّ الأدنى
      // (١٢٦) أو من المحتوى أيّهما أكبر، فتوزيعُ الفضلة عليه يملأه تماماً.
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: <Widget>[
        // ١ — الاسم **وحده بعرض العمود**: الرقمُ المرجعيّ كان على طرفه
        // فيأخذ منه نحو أربعين بكسلاً، وانتقل إلى الصورة.
        Text(
          vehicle.title,
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
          textAlign: TextAlign.center,
          style: TextStyle(
            fontFamily: HarajTheme.fontFamily,
            // ١٢٫٥ لا ١٤ بطلب المالك في ٩ سبتمبر ٢٠٢٦: الاسمُ أطولُ نصٍّ في
            // العمود وأكبرُه، فكان يبتلع سطره ويترك الباقيَ يبدو حاشيةً له.
            fontSize: 12.5,
            fontWeight: FontWeight.w700,
            color: palette.brown,
            height: 1.2,
          ),
        ),
        // فاصلٌ **مكتوب** تحت الاسم: `spaceBetween` يوزّع الفضلة بالسويّة
        // على ستّ فجوات، ولا فضلةَ تُذكر حين يملأ المحتوى الحدَّ الأدنى —
        // فيلتصق الاسمُ بالخانات تحته.
        const SizedBox(height: 5),
        // ٢ — ثلاثُ خاناتٍ مؤطَّرة، **الأيقونةُ فوق القيمة** — هيئةُ v1
        // حرفياً بطلب المالك في ٩ سبتمبر ٢٠٢٦، ولقطةُ v1 الحيّة مرجعُها.
        //
        // **كلُّ خانةٍ بعرض نصّها، لا ثلثاً بالسويّة.** كنّ ثلاثَ `Flexible`
        // في `Row`، و`Row` يقسم الفضلة على عوامل الـ`flex` بالتساوي: ٤٤
        // بكسلاً لكلٍّ من ١٣٢. و«45,000 كم» تحتاج ٥٣ — فتُقصّ، ولا يردّها
        // تصغيرُ الخطّ ولا الحشوة (جُرّبا: ١٠٫٥ أعطت «45,٠ كم» و٩٫٥ أعطت
        // «45,0 كم»). و«2022» تحتاج ٣١ فيضيع تسعةَ عشرَ من نصيبها.
        //
        // و`FittedBox` حارسُ الشاشة الضيّقة: مجموعُ الثلاث الطبيعيّ ١٢٢ في
        // عمودٍ عرضُه ١٣٨، فإن ضاق العمودُ أكثر تصغر الكتلةُ كلُّها بنسبةٍ
        // واحدة — وهو أهونُ من قصّ إحداهنّ.
        FittedBox(
          fit: BoxFit.scaleDown,
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: <Widget>[
              _Fact(
                icon: Icons.calendar_today_rounded,
                value: '${vehicle.year}',
                palette: palette,
              ),
              const SizedBox(width: 4),
              _Fact(
                icon: Icons.palette_outlined,
                value: vehicle.colourLabel,
                palette: palette,
              ),
              // الممشى قد يغيب، والغياب لا يُعرض صفراً: «٠ كم» ادّعاءٌ لم
              // يقله أحد — فتبقى خانتان.
              if (odometer != null) ...<Widget>[
                const SizedBox(width: 4),
                _Fact(
                  icon: Icons.speed_rounded,
                  value: l10n.vehicleOdometerShort(odometer),
                  palette: palette,
                ),
              ],
            ],
          ),
        ),
        // ٣ — الحالةُ والموقعُ **في سطرٍ واحد** كما في v1.
        //
        // كان الموقعُ في سطرٍ وحده لأن «الرياض / طريق الحائر» لم يكن يُقرأ
        // في نصف سطر. وما جعله يُقرأ الآن أمران: القسمةُ ٤٢:٥٨ زادت العمود
        // خمسةَ عشرَ بكسلاً، والحالةُ تأخذ عرضَ كلمتها وحدها
        // (`mainAxisSize.min`) فما بقي كلُّه للموقع.
        // **حشوةٌ رأسيّة مكتوبة** بطلب المالك في ٩ سبتمبر ٢٠٢٦: السطرُ كان
        // ملتصقاً بالخانات فوقه وبحوض العدّاد تحته، لأن `spaceBetween` يوزّع
        // الفضلة بالسويّة على ستّ فجوات — ولا فضلةَ تُذكر حين يملأ المحتوى
        // الحدَّ الأدنى.
        Padding(
          padding: const EdgeInsets.symmetric(vertical: 4),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: <Widget>[
              _IconText(
                icon: Icons.report_problem_outlined,
                text: vehicle.conditionLabel,
                palette: palette,
              ),
              const SizedBox(width: 6),
              Flexible(
                child: _IconText(
                  icon: Icons.place_outlined,
                  text: vehicle.location,
                  palette: palette,
                  flexible: true,
                ),
              ),
            ],
          ),
        ),
        // ٤ — العدّاد.
        _Countdown(vehicle: vehicle, palette: palette, l10n: l10n),
        // فاصلٌ **مكتوب** بين العدّاد والزرّ بطلب المالك في ٩ سبتمبر ٢٠٢٦:
        // `spaceBetween` يوزّع الفضلة على خمس فجواتٍ بالسويّة، فحين تقلّ
        // الفضلة يلتصق الحوضان الذهبيّان فيُقرآن كتلةً واحدة.
        const SizedBox(height: 5),
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

/// حوضُ الرقم المرجعيّ — داكنٌ صغير في زاوية الصورة اليسرى.
class _ReferenceChip extends StatelessWidget {
  const _ReferenceChip({required this.reference, required this.palette});

  final String reference;
  final HarajPalette palette;

  @override
  Widget build(BuildContext context) => DecoratedBox(
    decoration: BoxDecoration(
      // شبه معتمٍ لا معتم: صار على الصورة لا على الورقة الكريميّة، ونفسُ
      // شفافيّة شارة الموقف تُبقي الاثنتين حوضاً واحداً لا حوضين.
      color: palette.heroTop.withValues(alpha: 0.88),
      borderRadius: BorderRadius.circular(7),
    ),
    child: Padding(
      padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 3),
      child: Text(
        reference,
        // **`ltr`**: `#13466` رقمٌ بعلامةٍ قبله، وترتيبُه في سياقٍ عربيّ
        // ينقلب فتصير العلامةُ بعده.
        textDirection: TextDirection.ltr,
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

/// خانةُ مواصفةٍ واحدة: **الأيقونة فوق القيمة**، بحدٍّ ذهبيٍّ رفيع — هيئةُ v1.
///
/// فوقها لا بجانبها: بجانبها يصير عرضُ الخانة أيقونةً وكلمةً، وثلاثُ خاناتٍ
/// كذلك لا تسع عمودَ بياناتٍ عرضُه ١٦٨.
class _Fact extends StatelessWidget {
  const _Fact({required this.icon, required this.value, required this.palette});

  final IconData icon;
  final String value;
  final HarajPalette palette;

  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 3),
    decoration: BoxDecoration(
      borderRadius: BorderRadius.circular(7),
      border: Border.all(color: palette.gold.withValues(alpha: 0.45)),
    ),
    child: Column(
      mainAxisSize: MainAxisSize.min,
      children: <Widget>[
        Icon(icon, size: 11, color: palette.gold),
        const SizedBox(height: 1),
        Text(
          value,
          maxLines: 1,
          // **`clip` لا `ellipsis`**: النقاطُ الثلاث تأكل من العرض ما يكفي
          // لرقمين، فتصير «45,0…» حيث كانت «45,000» تسع. وهي ما جعل v1
          // تعرض «..» وحدها.
          overflow: TextOverflow.clip,
          softWrap: false,
          style: TextStyle(
            fontFamily: HarajTheme.fontFamily,
            fontSize: 10.5,
            fontWeight: FontWeight.w700,
            color: palette.brown,
            height: 1.2,
          ),
        ),
      ],
    ),
  );
}

/// أيقونةٌ ونصٌّ خافتان — تُستعملان مرّتين في سطرٍ واحد: الحالة، ثم الموقع.
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
        fontSize: 9.5,
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
        Icon(icon, size: 11, color: palette.gold),
        const SizedBox(width: 2),
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
      padding: const EdgeInsets.symmetric(vertical: 3, horizontal: 8),
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
/// **يفتح نافذةَ المزايدة** (`showVehicleBidSheet`) بطلب المالك في ٩ سبتمبر
/// ٢٠٢٦ على مثال v1؛ كان يفتح صفحة المركبة. والشرطُ الذي كُتب يومها باقٍ:
/// **لا مزايدةَ تقع من النافذة** — زرٌّ في قائمةٍ يزايد مباشرةً أقصرُ طريقٍ
/// إلى مزايدةٍ بالخطأ، والرصيدُ والحدُّ الأدنى وشروطُ الأهلية في الصفحة.
/// فزرُّ النافذة الوحيد ينقل إليها.
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
          height: 28,
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

/// نصفُ الصورة — ممتدٌّ إلى حوافّ الكرت، وعليه شارتان: الموقفُ والرقم.
///
/// **ولا قلبَ عليه** — مُحي بطلب المالك في ٩ سبتمبر ٢٠٢٦، نقضاً لقرارٍ في
/// نفس اليوم أبقاه لأن المفضّلة ميزةٌ في هذا الإصدار وحده. والميزةُ باقيةٌ:
/// قسمُ المفضّلة في الشريط السفليّ يعمل، و`toggleFavouriteProvider` باقٍ
/// بلا مستعملٍ في الكرت وحده.
class _Photo extends StatelessWidget {
  const _Photo({
    required this.vehicle,
    required this.palette,
    required this.l10n,
  });

  final VehicleSummary vehicle;
  final HarajPalette palette;
  final AppLocalizations l10n;

  @override
  Widget build(BuildContext context) => Stack(
    fit: StackFit.expand,
    children: <Widget>[
      // **`cover` لا `contain`** — والسيّارةُ كاملةٌ رغم ذلك.
      //
      // صورةُ المالك نسبتُها ٢٫٥:١ وهذا الصندوق نحو ١:١، فـ`cover` كان يقصّ
      // مقدّمَها ومؤخّرَها و`contain` يترك شريطين داكنين يبتلعان ثلث الصندوق.
      // ولا يحلُّه أيُّ `BoxFit`: نسبتان مختلفتان لا تجتمعان في صندوقٍ واحد.
      //
      // فحُلَّ في الملفّ: المصغَّرةُ تُولَّد مربّعةً، الصورةُ كاملةً في وسطها
      // وخلفيّتُها هي نفسُها مكبَّرةً ومموَّهة. و`cover` على ملفٍّ بنسبة
      // الصندوق لا يقصّ شيئاً.
      RemoteImage(url: vehicle.thumbnailUrl, decodeWidth: 400),
      // **شارةُ الموقف يميناً، والرقمُ المرجعيّ يساراً** — على الصورة
      // كلاهما، بطلب المالك في ٩ سبتمبر ٢٠٢٦.
      //
      // و`PositionedDirectional` لا `Positioned`: `start` هي يمينُ الشاشة
      // في العربية ويسارُها في الإنجليزية، فتبقى كلُّ شارةٍ في جهتها من
      // الصورة مهما انقلب الاتجاه.
      PositionedDirectional(
        top: 6,
        start: 6,
        child: _LotBadge(
          label: l10n.vehicleLotPosition(vehicle.lotNumber),
          palette: palette,
        ),
      ),
      PositionedDirectional(
        top: 6,
        end: 6,
        child: _ReferenceChip(reference: vehicle.reference, palette: palette),
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
