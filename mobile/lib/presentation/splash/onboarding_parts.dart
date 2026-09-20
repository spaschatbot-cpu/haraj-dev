import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../../app/theme.dart';
import '../../domain/catalog/entities/vehicle_feed.dart';
import '../../domain/catalog/entities/vehicle_summary.dart';
import '../../l10n/generated/app_localizations.dart';
import '../catalog/widgets/remote_image.dart';

/// قطعُ شاشات الترحيب — **مكتوبةٌ مرّةً وتقرؤها الشاشتان**.
///
/// صفحتا الترحيب (`/welcome` و`/explore`) تتشاركان الرأسَ والكرتَ والنقاطَ
/// والزرَّ وسطرَ الترخيص، ويختلفان في النصّ وفي لون الزرّ ومحاذاة الكلام.
/// ونسخُ سبعِ ودجتٍ في ملفٍّ ثانٍ يعني أن تعديلاً في الرأس يقع في واحدةٍ
/// ويُنسى في الأخرى — وهو بالضبط ما تمنعه المادة ٤-٥.
///
/// وأسماؤها بلا شرطةٍ سفليّة لأنها تُقرأ من ملفَّين: الخاصُّ في دارت خاصٌّ
/// بالملفّ لا بالمكتبة.

/// أحمرُ البثّ الحيّ. ليس دوراً في [HarajPalette] فلا رمزَ له فيها، وهو
/// مكتوبٌ هنا مرّةً واحدةً تقرؤها الشاشتان.
const Color kLiveRed = Color(0xFFE5484D);

/// مقاساتُ الشاشة الواحدة، محسوبةً من ارتفاعها المتاح.
///
/// **لأن «لا تمرير» وعدٌ لا يُوفى برقمٍ ثابت.** الشاشاتُ الثلاث محتواها ثابتُ
/// الارتفاع تقريباً (رأسٌ وكرتٌ ونصٌّ وزرّ)، والهواتفُ ليست كذلك: قِيس على
/// ثلاثةٍ بعد خصم الشقّ والشريط — iPhone SE يعطي **٥٨٧**، وأندرويد **٧٥٢**،
/// وiPhone 14 **٧٦٣**. ومقاسٌ واحدٌ يسع الأخيرَين يفيض عن الأوّل.
///
/// فمقاسان: `compact` دون [_compactBelow]، وعاديٌّ فوقها. وكلُّ رقمٍ هنا
/// يُقرأ في موضعٍ واحد، فتغييرُ العتبة يحرّك الشاشات الثلاث معاً.
@immutable
class OnboardingMetrics {
  const OnboardingMetrics._({
    required this.compact,
    required this.available,
  });

  factory OnboardingMetrics.of(double available) => OnboardingMetrics._(
    compact: available < _compactBelow,
    available: available,
  );

  /// العتبة. أُخذت فوق ارتفاع iPhone SE المتاح (٥٨٧) وتحت أندرويد (٧٥٢).
  static const double _compactBelow = 660;

  final bool compact;
  final double available;

  /// سقفُ ارتفاع كرت الصورة.
  double get cardMax => available * (compact ? 0.34 : 0.42);

  /// ضلعُ مربّع الشعار في الرأس.
  double get logo => compact ? 46 : 56;

  /// قطرُ قرص الشعار في شاشة البدء.
  double get mark => compact ? 150 : 236;

  double get ctaHeight => compact ? 56 : 64;

  /// الفجوةُ بين الكتل الكبيرة.
  double get gap => compact ? 10 : 16;

  /// الفجوةُ الصغيرة داخل الكتلة.
  double get tight => compact ? 6 : 12;
}

// ---------------------------------------------------------------------------
// الرأس
// ---------------------------------------------------------------------------

/// اللوجو واسمُ المنصّة، و«تخطّي» في الطرف المقابل.
class OnboardingHeader extends StatelessWidget {
  const OnboardingHeader({
    required this.theme,
    required this.palette,
    required this.strings,
    required this.onSkip,
    required this.metrics,
    super.key,
  });

  final ThemeData theme;
  final HarajPalette palette;
  final AppLocalizations strings;
  final VoidCallback onSkip;
  final OnboardingMetrics metrics;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: <Widget>[
        Container(
          width: metrics.logo,
          height: metrics.logo,
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(18),
            gradient: LinearGradient(
              begin: Alignment.topRight,
              end: Alignment.bottomLeft,
              colors: <Color>[palette.heroTop, palette.heroBottom],
            ),
          ),
          clipBehavior: Clip.antiAlias,
          padding: const EdgeInsets.all(10),
          child: Image.asset(
            'assets/images/logo.png',
            fit: BoxFit.contain,
            errorBuilder: (_, _, _) =>
                Icon(Icons.gavel_rounded, color: palette.goldOnDark, size: 24),
          ),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: <Widget>[
              Row(
                children: <Widget>[
                  Flexible(
                    child: Text(
                      strings.splashHeadline,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: theme.textTheme.titleMedium?.copyWith(
                        fontWeight: FontWeight.w700,
                        color: palette.ink,
                      ),
                    ),
                  ),
                  const SizedBox(width: 6),
                  Icon(Icons.verified_rounded, size: 16, color: palette.gold),
                ],
              ),
              const SizedBox(height: 2),
              Text(
                strings.welcomeBrandLine,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: theme.textTheme.labelSmall?.copyWith(
                  color: palette.inkMuted,
                ),
              ),
            ],
          ),
        ),
        const SizedBox(width: 10),
        // «تخطّي» زرٌّ هادئ لا رابطٌ مسطور: هو فعلٌ، ولمسُه يحتاج مساحة.
        TextButton(
          onPressed: onSkip,
          style: TextButton.styleFrom(
            foregroundColor: palette.inkMuted,
            backgroundColor: palette.cardSurface,
            padding: EdgeInsets.symmetric(
              horizontal: 18,
              vertical: metrics.compact ? 9 : 12,
            ),
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(999),
              side: BorderSide(color: palette.inkMuted.withValues(alpha: 0.2)),
            ),
          ),
          child: Text(strings.welcomeSkip),
        ),
      ],
    );
  }
}

// ---------------------------------------------------------------------------
// الكرت
// ---------------------------------------------------------------------------

/// كرتُ الصورة: صورةُ مركبةٍ حقيقيّةٍ وشاراتٌ صغيرةٌ عليها.
///
/// **والشاراتُ تأتي من الشاشة لا من هنا**: كلُّ صفحةٍ تقول ما تريد إبرازه،
/// والكرتُ يعرف كيف يضعه — أعلى الصورة وأسفلها — ومتى يُخفيه.
///
/// **ولا شاراتِ بلا مركبةٍ حقيقيّة.** حين لا مزادَ جارياً تبقى صورةُ الأصول
/// وحدها: «مباشر» على صورةٍ من الأصول ادّعاءٌ لا مصدرَ له. وشاراتُ الخدمة
/// (كالشحن والضمان) تُعرض دائماً لأنها وصفُ المنصّة لا وصفُ صفقة.
class OnboardingCard extends StatelessWidget {
  const OnboardingCard({
    required this.palette,
    required this.feed,
    required this.loading,
    this.topStart = const <Widget>[],
    this.topEnd = const <Widget>[],
    this.bottomStart = const <Widget>[],
    this.bottomEnd = const <Widget>[],
    this.vehicleAt = 0,
    required this.maxHeight,
    super.key,
  });

  final HarajPalette palette;
  final VehicleFeed? feed;
  final bool loading;

  final List<Widget> topStart;
  final List<Widget> topEnd;
  final List<Widget> bottomStart;
  final List<Widget> bottomEnd;

  /// **سقفُ ارتفاع الكرت.** تحسبه الشاشةُ من ارتفاعها المتاح، ولا يُكتب
  /// رقماً هنا.
  ///
  /// بدونه كان الكرتُ نسبةً ثابتةً (`9/8`) يأخذ ارتفاعاً بقدر عرض الشاشة،
  /// فيدفع النصَّ والزرَّ خارجها على هاتفٍ قصير. قِيس على ثلاثة مقاسات:
  /// أندرويد ٣٦٠×٧٥٢ يتّسع بسبع بكسلات، وiPhone 14 يتّسع، و**iPhone SE
  /// (٣٧٥×٥٨٧ بعد الشقّ والشريط) يفيض فيلزم التمرير** — والزرُّ الذي يجب أن
  /// يُرى أوّلاً يقع تحت الطيّة.
  ///
  /// والسقفُ يقصّ من **ارتفاع الكرت** لا من عرضه: الصورةُ تبقى بعرض الشاشة
  /// ويُقتطع من أعلاها وأسفلها، وهو أرخصُ من كرتٍ أضيقَ من الصفحة.
  final double maxHeight;

  /// أيُّ مركبةٍ من الصفحة تُعرض. **الصفحتان تعرضان سيّارتين مختلفتين** حين
  /// تتوفّران: صورةٌ واحدةٌ مكرّرةٌ في شاشتين متتاليتين تُقرأ عطلاً في الرسم.
  final int vehicleAt;

  @override
  Widget build(BuildContext context) {
    final vehicles = feed?.page.vehicles ?? const <VehicleSummary>[];
    final car = vehicles.isEmpty
        ? null
        : vehicles[vehicleAt.clamp(0, vehicles.length - 1)];

    final hasOverlay =
        topStart.isNotEmpty ||
        topEnd.isNotEmpty ||
        bottomStart.isNotEmpty ||
        bottomEnd.isNotEmpty;

    return DecoratedBox(
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(28),
        color: palette.heroBottom,
        // ظلّان لا واحد: قريبٌ ضيّقٌ يرسم الحافّة، وبعيدٌ واسعٌ يرفع الكرت
        // عن الصفحة. وظلٌّ واحدٌ واسعٌ يُقرأ ضبابةً تحت الكرت لا ارتفاعاً.
        boxShadow: <BoxShadow>[
          BoxShadow(
            color: palette.heroBottom.withValues(alpha: 0.16),
            blurRadius: 6,
            offset: const Offset(0, 2),
          ),
          BoxShadow(
            color: palette.heroBottom.withValues(alpha: 0.24),
            blurRadius: 38,
            offset: const Offset(0, 18),
          ),
        ],
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(28),
        // **النسبةُ `9/8` سقفٌ لا فرض.** (`16/10` ← `5/4` ← `1/1` ← `9/8`.)
        // و`LayoutBuilder` لا `AspectRatio`: الأخيرُ تحت سقفِ ارتفاعٍ يضيّق
        // **العرضَ** ليحفظ النسبة، فيصير الكرتُ أضيقَ من الصفحة ويبدو
        // مزاحاً. وهنا العرضُ كاملٌ دائماً والارتفاعُ هو الذي ينزل.
        child: LayoutBuilder(
          builder: (context, box) => SizedBox(
            height: math.min(box.maxWidth * 8 / 9, maxHeight),
            child: Stack(
            fit: StackFit.expand,
            children: <Widget>[
              // **`cover` لا `contain`، ولا طبقةَ تمويهٍ خلفه.**
              //
              // كانت هنا طبقتان — صورةٌ بـ`contain` وخلفها نسخةٌ مموّهةٌ
              // تملأ ما يفضل — وبُنيت على ظنٍّ أن المصغَّرة عريضة (١٦:٩).
              // وهي ليست كذلك: **قِيست فوُجدت ٧٦٠×٨٠٠**، أي أطولَ من عرضها
              // (٠٫٩٥) والإطارُ أعرضُ منها (١٫١٢٥). فـ`contain` يملأ الارتفاع
              // ويترك التمويهَ شريطين على **الجانبين** — وهما «الخطوط
              // السودا» التي رآها المالك.
              //
              // و`cover` يملأ الإطار فلا شريطَ في أي جهة، وثمنُه قصُّ ١٦٪ من
              // الارتفاع — وهو ربحٌ لا خسارة هنا: المصغَّرةُ نفسُها تحمل
              // فراغاً داكناً فوق السيّارة وتحتها، والقصُّ يأكله.
              if (car?.thumbnailUrl != null)
                RemoteImage(url: car!.thumbnailUrl, decodeWidth: 1000)
              else
                Image.asset(
                  'assets/images/hero_car.png',
                  fit: BoxFit.cover,
                  alignment: Alignment.center,
                  errorBuilder: (_, _, _) =>
                      ColoredBox(color: palette.heroBottom),
                ),
              if (hasOverlay) ...<Widget>[
                // **ستارٌ في الحافّتين لا على الصورة كلّها.** الشارةُ على
                // صورةٍ ساطعةٍ لا تُقرأ، والحلُّ المعتاد تعتيمُ الصورة —
                // وهو يُفسدها. فوسطُ الصورة، حيث السيّارة، لا يُمسّ.
                DecoratedBox(
                  decoration: BoxDecoration(
                    gradient: LinearGradient(
                      begin: Alignment.topCenter,
                      end: Alignment.bottomCenter,
                      colors: <Color>[
                        Colors.black.withValues(alpha: 0.45),
                        Colors.transparent,
                        Colors.transparent,
                        Colors.black.withValues(alpha: 0.42),
                      ],
                      stops: const <double>[0, 0.26, 0.7, 1],
                    ),
                  ),
                ),
                if (topStart.isNotEmpty || topEnd.isNotEmpty)
                  Positioned(
                    top: 12,
                    right: 12,
                    left: 12,
                    child: _ChipRow(start: topStart, end: topEnd),
                  ),
                if (bottomStart.isNotEmpty || bottomEnd.isNotEmpty)
                  Positioned(
                    bottom: 12,
                    right: 12,
                    left: 12,
                    child: _ChipRow(start: bottomStart, end: bottomEnd),
                  ),
              ],
              if (loading) const Center(child: CircularProgressIndicator()),
              // حدٌّ شعريٌّ من الداخل: يفصل الكرتَ عن أرضيّةٍ فاتحةٍ بلا
              // إطارٍ يُرى إطاراً، ويُنعّم حافّةَ الصورة المقصوصة.
              IgnorePointer(
                child: DecoratedBox(
                  decoration: BoxDecoration(
                    borderRadius: BorderRadius.circular(28),
                    border: Border.all(
                      color: Colors.white.withValues(alpha: 0.10),
                    ),
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
}

/// صفٌّ من الشارات: مجموعةٌ في طرفٍ ومجموعةٌ في الطرف المقابل.
class _ChipRow extends StatelessWidget {
  const _ChipRow({required this.start, required this.end});

  final List<Widget> start;
  final List<Widget> end;

  @override
  Widget build(BuildContext context) => Row(
    children: <Widget>[
      for (final chip in start) ...<Widget>[chip, const SizedBox(width: 6)],
      const Spacer(),
      for (final chip in end) ...<Widget>[const SizedBox(width: 6), chip],
    ],
  );
}

/// شارةٌ صغيرةٌ على الصورة.
///
/// **زجاجيّةٌ لا مصمتة:** أرضيّةٌ سوداءُ شفّافةٌ وحدٌّ باللون ونقطةٌ أو أيقونةٌ
/// به — فاللونُ يُرى والصورةُ تُرى تحته. وحبّةٌ مصمتةٌ بلونٍ صارخٍ على صورةِ
/// سيّارةٍ تُقرأ ملصقاً أُلصق عليها.
///
/// والنصُّ أبيضُ دائماً لا باللون: لونُ الحدّ يكفي للتمييز، ونصٌّ ملوّنٌ على
/// أرضيّةٍ شفّافةٍ فوق صورةٍ متغيّرةٍ لا يُضمَن تباينُه.
class OnboardingChip extends StatelessWidget {
  const OnboardingChip({
    required this.theme,
    required this.tint,
    required this.label,
    this.icon,
    this.pulse = false,
    super.key,
  });

  final ThemeData theme;
  final Color tint;
  final String label;
  final IconData? icon;

  /// نقطةٌ بهالةٍ بدل الأيقونة — للبثّ الحيّ وحده.
  final bool pulse;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: Colors.black.withValues(alpha: 0.42),
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: tint.withValues(alpha: 0.75), width: 1.2),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: <Widget>[
          if (pulse)
            Container(
              width: 7,
              height: 7,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: tint,
                boxShadow: <BoxShadow>[BoxShadow(color: tint, blurRadius: 6)],
              ),
            )
          else if (icon != null)
            Icon(icon, size: 13, color: tint),
          const SizedBox(width: 6),
          Flexible(
            child: Text(
              label,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: theme.textTheme.labelSmall?.copyWith(
                color: Colors.white,
                fontWeight: FontWeight.w700,
                letterSpacing: 0,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// النصّ والأزرار والذيل
// ---------------------------------------------------------------------------

/// شارةٌ صغيرةٌ فوق العنوان.
class OnboardingEyebrow extends StatelessWidget {
  const OnboardingEyebrow({
    required this.theme,
    required this.palette,
    required this.label,
    super.key,
  });

  final ThemeData theme;
  final HarajPalette palette;
  final String label;

  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.symmetric(horizontal: 11, vertical: 6),
    decoration: BoxDecoration(
      color: palette.goldMuted,
      borderRadius: BorderRadius.circular(999),
    ),
    child: Row(
      mainAxisSize: MainAxisSize.min,
      children: <Widget>[
        Icon(Icons.verified_rounded, size: 13, color: palette.gold),
        const SizedBox(width: 6),
        Text(
          label,
          style: theme.textTheme.labelSmall?.copyWith(
            color: palette.goldDeep,
            fontWeight: FontWeight.w700,
            letterSpacing: 0,
          ),
        ),
      ],
    ),
  );
}

/// نقاطُ الصفحات. الحاليّةُ ممدودةٌ لا ملوّنةٌ وحدَها: الشكلُ يُرى حيث لا
/// يُميَّز اللون.
class OnboardingDots extends StatelessWidget {
  const OnboardingDots({
    required this.palette,
    required this.strings,
    required this.count,
    required this.current,
    super.key,
  });

  final HarajPalette palette;
  final AppLocalizations strings;
  final int count;

  /// رقمُ الصفحة الحاليّة ابتداءً من ١.
  final int current;

  @override
  Widget build(BuildContext context) => Semantics(
    label: strings.welcomeStep('$current', '$count'),
    child: Row(
      mainAxisAlignment: MainAxisAlignment.center,
      children: <Widget>[
        for (var i = 1; i <= count; i++) ...<Widget>[
          if (i != 1) const SizedBox(width: 8),
          AnimatedContainer(
            duration: const Duration(milliseconds: 200),
            width: i == current ? 26 : 8,
            height: 8,
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(999),
              color: i == current
                  ? palette.gold
                  : palette.inkMuted.withValues(alpha: 0.32),
            ),
          ),
        ],
      ],
    ),
  );
}

/// زرُّ الانتقال العريض، وقرصُ السهم في طرفه.
class OnboardingCta extends StatelessWidget {
  const OnboardingCta({
    required this.theme,
    required this.label,
    required this.onPressed,
    required this.fill,
    required this.metrics,
    super.key,
  });

  final ThemeData theme;
  final String label;
  final VoidCallback onPressed;
  final OnboardingMetrics metrics;

  /// لونُ الزرّ. يختلف بالصفحة: الأزرقُ الأساسيُّ في الأولى، والكحليُّ في
  /// الأخيرة — فيُقرأ تدرّجاً نحو الدخول لا زرّاً مكرّراً.
  final Color fill;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: metrics.ctaHeight,
      child: FilledButton(
        onPressed: onPressed,
        style: FilledButton.styleFrom(
          backgroundColor: fill,
          foregroundColor: Colors.white,
          elevation: 10,
          shadowColor: fill.withValues(alpha: 0.45),
          padding: const EdgeInsets.symmetric(horizontal: 12),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(20),
          ),
        ),
        // **بلا سهم.** كان في طرف الزرّ قرصٌ فيه سهم، ومعه فراغٌ مكافئٌ
        // في الطرف الآخر ليبقى النصُّ في الوسط — أي عنصران لأجل زخرفةٍ
        // واحدة. حُذف بأمر المالك، والنصُّ صار وحدَه في وسط الزرّ.
        child: Center(
          child: Text(
            label,
            textAlign: TextAlign.center,
            style: theme.textTheme.titleMedium?.copyWith(
              color: Colors.white,
              fontWeight: FontWeight.w700,
            ),
          ),
        ),
      ),
    );
  }
}
