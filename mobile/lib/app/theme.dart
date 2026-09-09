import 'package:flutter/material.dart';

/// ثيم التطبيق.
///
/// الخط عربي **مبنيّ في الحزمة** لا مجلوب من الشبكة: قاعدة العرض 7 في الفيز
/// 008 تشترط أن تعمل كل شاشة بلا اتصال، وخط يُنزَّل وقت التشغيل يجعل أول فتح
/// بلا شبكة يعرض مربّعات فارغة.
/// ألوانُ العلامة التي لا يعرفها `ColorScheme`.
///
/// **امتدادُ ثيم لا ثوابتُ عامّة:** اللون يُقرأ من `Theme.of(context)` فيتبدّل
/// مع الوضع الفاتح والداكن بلا شرطٍ في كل ودجت، ويُستبدَل في اختبارٍ أو في
/// علامةٍ ثانية بلا تعديل من يستعمله. لونٌ مكتوب رقماً في ودجت هو نسخةٌ ثانية
/// تفترق عن الأولى عند أول تغيير (المادة ٤-٥).
@immutable
class HarajPalette extends ThemeExtension<HarajPalette> {
  const HarajPalette({
    required this.gold,
    required this.goldMuted,
    required this.brown,
    required this.navSurface,
    required this.navSurfaceLow,
    required this.navInactive,
    required this.headerTop,
    required this.headerBottom,
    required this.goldOnDark,
  });

  /// الذهبيّ: لونُ الأيقونة المختارة.
  ///
  /// **`#B8860B` لا `#E3BC57`**: الذهبيّ الفاتح جميلٌ على أرضيّةٍ داكنة
  /// ونسبتُه على البيضاء ٢٫٥:١ — دون حدّ الأيقونات (٣:١). فاختير ذهبيٌّ
  /// غائرٌ يبلغ ٤٫١:١ على الأبيض ويبقى ذهبيّاً لا بنّيّاً.
  final Color gold;

  /// ذهبيٌّ خافت: الحوض تحت الأيقونة المختارة، والخيطُ فوق الشريط.
  final Color goldMuted;

  /// البنّيّ الغامق: لونُ كل نصٍّ في الشريط.
  ///
  /// النصّ **لا يُلوَّن بالذهبيّ** ولو كان قسمُه مختاراً: ذهبيٌّ بحجم ١١ نقطة
  /// على أبيض لا يُقرأ لمن في بصره ضعف، والتمييز يقع على الوزن والحوض
  /// والأيقونة — ثلاث إشارات تكفي بلا أن يدفع النصُّ ثمنها.
  final Color brown;

  /// أعلى تدرّج أرضيّة الشريط — الحافّة التي «تلتقط الضوء».
  final Color navSurface;

  /// أسفل التدرّج، أشفُّ من أعلاه.
  ///
  /// التدرّج هو ما يفرّق الزجاج عن الورق الشفّاف: سطحٌ حقيقيّ يُضيء من جهةٍ
  /// ويعتم من أخرى، ولونٌ واحدٌ مسطّح يبقى مسطّحاً مهما خفّت شفافيّته.
  final Color navSurfaceLow;

  /// طرفا تدرّج الهيدر — خضرةُ العلامة، من الغامق إلى الأغمق.
  ///
  /// التدرّجُ قطريّ لا رأسيّ: رأسيٌّ على شريطٍ ارتفاعه ٥٦ لا يكاد يُرى،
  /// وقطريٌّ يمرّ على عرض الشاشة كلّه فيُلحَظ بلا أن يصرخ.
  final Color headerTop;
  final Color headerBottom;

  /// الذهبيّ **على الداكن**: أفتحُ من ذهبيّ الأبيض.
  ///
  /// لونان لا واحد: `#B8860B` يكفي على الأبيض ونسبتُه على الخضرة العميقة
  /// ٢٫١:١ — لا يُقرأ. ولونٌ واحدٌ «وسط» يكون رديئاً في الموضعين معاً.
  final Color goldOnDark;

  /// لونُ أيقونةِ ما ليس مختاراً: بنّيٌّ دافئ لا ذهبيٌّ باهت.
  ///
  /// **الذهبيّ الباهت يُقرأ «معطَّل»** لا «غير مختار»، والفرق بينهما هو كل
  /// معنى الشريط. والبنّيُّ يجاور الذهبيَّ في العائلة نفسها فلا ينشزّ.
  final Color navInactive;

  @override
  HarajPalette copyWith({
    Color? gold,
    Color? goldMuted,
    Color? brown,
    Color? navSurface,
    Color? navSurfaceLow,
    Color? navInactive,
    Color? headerTop,
    Color? headerBottom,
    Color? goldOnDark,
  }) => HarajPalette(
    gold: gold ?? this.gold,
    goldMuted: goldMuted ?? this.goldMuted,
    brown: brown ?? this.brown,
    navSurface: navSurface ?? this.navSurface,
    navSurfaceLow: navSurfaceLow ?? this.navSurfaceLow,
    navInactive: navInactive ?? this.navInactive,
    headerTop: headerTop ?? this.headerTop,
    headerBottom: headerBottom ?? this.headerBottom,
    goldOnDark: goldOnDark ?? this.goldOnDark,
  );

  @override
  HarajPalette lerp(HarajPalette? other, double t) {
    if (other == null) return this;
    return HarajPalette(
      gold: Color.lerp(gold, other.gold, t)!,
      goldMuted: Color.lerp(goldMuted, other.goldMuted, t)!,
      brown: Color.lerp(brown, other.brown, t)!,
      navSurface: Color.lerp(navSurface, other.navSurface, t)!,
      navSurfaceLow: Color.lerp(navSurfaceLow, other.navSurfaceLow, t)!,
      navInactive: Color.lerp(navInactive, other.navInactive, t)!,
      headerTop: Color.lerp(headerTop, other.headerTop, t)!,
      headerBottom: Color.lerp(headerBottom, other.headerBottom, t)!,
      goldOnDark: Color.lerp(goldOnDark, other.goldOnDark, t)!,
    );
  }

  /// اللونُ من الثيم، أو الافتراضيّ إن لم يُسجَّل.
  ///
  /// لا `!` على الامتداد: ودجت تُبنى في اختبارٍ بثيمٍ عارٍ كانت ستنهار،
  /// وانهيارُ شاشةٍ بسبب لونٍ غير مسجَّل ثمنٌ لا يوازي شيئاً.
  static HarajPalette of(BuildContext context) =>
      Theme.of(context).extension<HarajPalette>() ?? _light;

  static const HarajPalette _light = HarajPalette(
    gold: Color(0xFFB8860B),
    goldMuted: Color(0x24B8860B),
    brown: Color(0xFF3E2A1E),
    // ‏0xA6 ≈ ٦٥٪ في الأعلى و0x8C ≈ ٥٥٪ في الأسفل: يمرّ من تحته ما يُمرَّر
    // فيبدو زجاجاً لا ورقاً. ولا ينزل أكثر — النصّ البنّيّ يجب أن يُقرأ على
    // ما يمرّ خلفه أيّاً كان لونه، والطمسُ ٣٠ هو ما يمزج ذلك اللون فيثبت.
    navSurface: Color(0xA6FFFFFF),
    navSurfaceLow: Color(0x8CFFFFFF),
    navInactive: Color(0xFF8D7A63),
    headerTop: Color(0xFF0F5C4A),
    headerBottom: Color(0xFF083A2E),
    goldOnDark: Color(0xFFE3BC57),
  );

  /// في الوضع الداكن تنقلب الأرضيّة ويُرفع الذهبيّ: نفس النسبة على خلفيّةٍ
  /// أعتم تبدو أضعف، فتُعوَّض بالسطوع لا بالحجم. والنصّ يصير بيجاً فاتحاً —
  /// بنّيٌّ غامق على أسود لا يُقرأ.
  static const HarajPalette _dark = HarajPalette(
    gold: Color(0xFFE3BC57),
    goldMuted: Color(0x2EE3BC57),
    brown: Color(0xFFEDE0D0),
    navSurface: Color(0xA6141009),
    navSurfaceLow: Color(0x8C0E0B06),
    navInactive: Color(0xFFA89478),
    headerTop: Color(0xFF0A3B30),
    headerBottom: Color(0xFF04211A),
    goldOnDark: Color(0xFFEFCB72),
  );
}

abstract final class HarajTheme {
  /// عائلة الخط معرَّفة في `pubspec.yaml` تحت `fonts:`.
  static const String fontFamily = 'IBMPlexSansArabic';

  /// خطوط النظام العربية كاحتياط — لو سقط تحميل الأصل لأي سبب، يبقى النصّ
  /// مقروءاً بدل أن يتحوّل إلى مربّعات.
  static const List<String> _fallbacks = <String>[
    'Noto Naskh Arabic',
    'Geeza Pro',
    'Arial',
  ];

  static ThemeData light() => _build(Brightness.light);

  static ThemeData dark() => _build(Brightness.dark);

  static ThemeData _build(Brightness brightness) {
    final base = ThemeData(
      brightness: brightness,
      colorScheme: ColorScheme.fromSeed(
        seedColor: const Color(0xFF0F5C4A),
        brightness: brightness,
      ),
      useMaterial3: true,
    );

    return base.copyWith(
      textTheme: base.textTheme.apply(
        fontFamily: fontFamily,
        fontFamilyFallback: _fallbacks,
      ),
      primaryTextTheme: base.primaryTextTheme.apply(
        fontFamily: fontFamily,
        fontFamilyFallback: _fallbacks,
      ),
      extensions: <ThemeExtension<dynamic>>[
        brightness == Brightness.dark
            ? HarajPalette._dark
            : HarajPalette._light,
      ],
    );
  }
}
