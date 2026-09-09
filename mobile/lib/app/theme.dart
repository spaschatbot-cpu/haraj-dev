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
    required this.goldDeep,
    required this.goldMuted,
    required this.goldOnDark,
    required this.brown,
    required this.inkMuted,
    required this.pageBackground,
    required this.cardSurface,
    required this.heroTop,
    required this.heroBottom,
    required this.heroGlow,
    required this.navInactive,
    required this.timerBadge,
    required this.pillTop,
    required this.pillBottom,
  });

  /// الذهبيّ: لونُ الأيقونة المختارة، والحدُّ حول ما هو تفاعليّ.
  ///
  /// **`#B8860B` لا `#E3BC57`**: الذهبيّ الفاتح جميلٌ على أرضيّةٍ داكنة
  /// ونسبتُه على البيضاء ٢٫٥:١ — دون حدّ الأيقونات (٣:١). فاختير ذهبيٌّ
  /// غائرٌ يبلغ ٤٫١:١ على الأبيض ويبقى ذهبيّاً لا بنّيّاً.
  final Color gold;

  /// ذهبيٌّ **غائرٌ** — طرفا تدرّج العنوان الذهبيّ في لوحة الترحيب.
  ///
  /// ثالثُ ذهبيّ، ولكلٍّ أرضيّتُه: `gold` للأيقونات على الأبيض، و`goldOnDark`
  /// على البنّيّ العميق، وهذا **أغمقُ من الاثنين** ليكون طرفَ التدرّج الذي
  /// منه يلمع الوسط. تدرّجٌ من `gold` إلى ذهبيٍّ أفتح كان أجملَ وأسقطَ
  /// النسبة تحت ٣:١ في نصف الحروف.
  ///
  /// وفي الوضع الداكن ينقلب المعنى: الطرفُ الغائر يصير **أفتحَ** من `gold`
  /// لأن الأرضيّة سوداء، والغائرُ عليها يختفي.
  final Color goldDeep;

  /// ذهبيٌّ خافت: أثرُ اللمسة، وحدُّ حقل البحث.
  final Color goldMuted;

  /// الذهبيّ **على الداكن**: أفتحُ من ذهبيّ الأبيض.
  ///
  /// لونان لا واحد: `#B8860B` يكفي على الأبيض ونسبتُه على البنّيّ العميق
  /// ٢٫١:١ — لا يُقرأ. ولونٌ واحدٌ «وسط» يكون رديئاً في الموضعين معاً.
  /// وهو لونُ اسم العلامة في الهيدر، ولونُ القسم المختار في الشريط السفليّ.
  final Color goldOnDark;

  /// البنّيّ الغامق: لونُ العناوين على الكروت البيضاء.
  final Color brown;

  /// بنّيٌّ باهت: سطرُ المواصفات على الكرت، وتسميةُ المبلغ فوقه.
  ///
  /// **لا رماديّ**: رماديٌّ محايد بين بنّيّاتٍ دافئة يُقرأ «ميّتاً»، والفرق
  /// بين الأساسيّ والثانويّ يُحمل على الشدّة لا على تبديل العائلة.
  final Color inkMuted;

  /// أرضيّة الصفحة — كريميٌّ لا أبيض.
  ///
  /// الكرت أبيض، فأرضيّةٌ بيضاء تحته تمحو حدَّه وتحوّل القائمة إلى كتلةٍ
  /// واحدة يفصلها الظلُّ وحده — وظلٌّ خفيفٌ على أبيض لا يكاد يُرى.
  final Color pageBackground;

  final Color cardSurface;

  /// طرفا **التدرّج الداكن الواحد** في التطبيق — من البنّيّ العميق إلى
  /// الأسود، قطريّاً من أعلى اليمين إلى أسفل اليسار.
  ///
  /// **زوجٌ واحدٌ يقرؤه ثلاثة**: لوحةُ الرئيسية (`HomeHero`)، وهيدرُ بقيّة
  /// الشاشات (`HarajAppBar`)، والشريطُ السفليّ. كانت لكلٍّ منها قيمتاه —
  /// `heroTop/heroBottom` و`headerTop/headerBottom` و`navSurface/navSurfaceLow`
  /// — بستّة ألوانٍ قريبةٍ لا متطابقة، فبدا الفوتر أعتم من الهيدر على نفس
  /// الشاشة. ووُحّدت مرّتين بنسخ القيم، وافترقت مرّتين لأن النسخ يفترق.
  /// فحُذفت الأربعة وبقي الزوج: **لا مكان يُعدَّل فيه أحدهما دون الآخر**.
  /// بقرار المالك في ٩ سبتمبر ٢٠٢٦.
  final Color heroTop;
  final Color heroBottom;

  /// وهجٌ ذهبيّ في وسط الهيدر: هو ما يمنع الأرضيّةَ الداكنة من أن تكون
  /// مستطيلاً أسود. شعاعيٌّ لا خطّيّ — الضوء يأتي من نقطة لا من حافّة.
  final Color heroGlow;

  /// لونُ أيقونةِ ما ليس مختاراً ونصِّه: كريميٌّ دافئ على الأرضيّة الداكنة.
  ///
  /// **لا ذهبيٌّ باهت**: الذهبيُّ الباهت يُقرأ «معطَّل» لا «غير مختار»،
  /// والفرق بينهما هو كل معنى الشريط.
  final Color navInactive;

  /// أخضرُ حوض العدّاد على الصورة.
  ///
  /// أخضرُ لا ذهبيّ: الوقت الباقي خبرٌ عاجل لا زينة، ولونٌ من خارج عائلة
  /// العلامة هو ما يجعله يُلحَظ فوق صورةٍ ملوّنة.
  final Color timerBadge;

  /// طرفا تدرّج الزرّ البنّيّ — «تفاصيل المزاد» و«الفرز والتصفية».
  final Color pillTop;
  final Color pillBottom;

  @override
  HarajPalette copyWith({
    Color? gold,
    Color? goldDeep,
    Color? goldMuted,
    Color? goldOnDark,
    Color? brown,
    Color? inkMuted,
    Color? pageBackground,
    Color? cardSurface,
    Color? heroTop,
    Color? heroBottom,
    Color? heroGlow,
    Color? navInactive,
    Color? timerBadge,
    Color? pillTop,
    Color? pillBottom,
  }) => HarajPalette(
    gold: gold ?? this.gold,
    goldDeep: goldDeep ?? this.goldDeep,
    goldMuted: goldMuted ?? this.goldMuted,
    goldOnDark: goldOnDark ?? this.goldOnDark,
    brown: brown ?? this.brown,
    inkMuted: inkMuted ?? this.inkMuted,
    pageBackground: pageBackground ?? this.pageBackground,
    cardSurface: cardSurface ?? this.cardSurface,
    heroTop: heroTop ?? this.heroTop,
    heroBottom: heroBottom ?? this.heroBottom,
    heroGlow: heroGlow ?? this.heroGlow,
    navInactive: navInactive ?? this.navInactive,
    timerBadge: timerBadge ?? this.timerBadge,
    pillTop: pillTop ?? this.pillTop,
    pillBottom: pillBottom ?? this.pillBottom,
  );

  @override
  HarajPalette lerp(HarajPalette? other, double t) {
    if (other == null) return this;
    return HarajPalette(
      gold: Color.lerp(gold, other.gold, t)!,
      goldDeep: Color.lerp(goldDeep, other.goldDeep, t)!,
      goldMuted: Color.lerp(goldMuted, other.goldMuted, t)!,
      goldOnDark: Color.lerp(goldOnDark, other.goldOnDark, t)!,
      brown: Color.lerp(brown, other.brown, t)!,
      inkMuted: Color.lerp(inkMuted, other.inkMuted, t)!,
      pageBackground: Color.lerp(pageBackground, other.pageBackground, t)!,
      cardSurface: Color.lerp(cardSurface, other.cardSurface, t)!,
      heroTop: Color.lerp(heroTop, other.heroTop, t)!,
      heroBottom: Color.lerp(heroBottom, other.heroBottom, t)!,
      heroGlow: Color.lerp(heroGlow, other.heroGlow, t)!,
      navInactive: Color.lerp(navInactive, other.navInactive, t)!,
      timerBadge: Color.lerp(timerBadge, other.timerBadge, t)!,
      pillTop: Color.lerp(pillTop, other.pillTop, t)!,
      pillBottom: Color.lerp(pillBottom, other.pillBottom, t)!,
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
    goldDeep: Color(0xFF8A6508),
    goldMuted: Color(0x24B8860B),
    goldOnDark: Color(0xFFE9C46A),
    brown: Color(0xFF2E2118),
    inkMuted: Color(0xFF8A7663),
    pageBackground: Color(0xFFF4F0E6),
    cardSurface: Color(0xFFFFFFFF),
    heroTop: Color(0xFF241A0C),
    heroBottom: Color(0xFF0B0805),
    heroGlow: Color(0xFFCE9B34),
    navInactive: Color(0xFFE4D9C6),
    timerBadge: Color(0xFF1F5F46),
    pillTop: Color(0xFF4A3624),
    pillBottom: Color(0xFF2A1D12),
  );

  /// في الوضع الداكن تنقلب الأرضيّة ويُرفع الذهبيّ: نفس النسبة على خلفيّةٍ
  /// أعتم تبدو أضعف، فتُعوَّض بالسطوع لا بالحجم. والنصّ يصير بيجاً فاتحاً —
  /// بنّيٌّ غامق على أسود لا يُقرأ. والشريط السفليّ **لا يتغيّر كثيراً**:
  /// كان داكناً أصلاً، وتغميقُه أكثر يُذيبه في أرضيّةٍ صارت داكنة، فرُفع
  /// قليلاً ليبقى له حدٌّ يُرى.
  static const HarajPalette _dark = HarajPalette(
    gold: Color(0xFFE9C46A),
    goldDeep: Color(0xFFC9A24A),
    goldMuted: Color(0x2EE9C46A),
    goldOnDark: Color(0xFFF0D28A),
    brown: Color(0xFFEDE0D0),
    inkMuted: Color(0xFFA89478),
    pageBackground: Color(0xFF15110B),
    cardSurface: Color(0xFF221B12),
    heroTop: Color(0xFF1A1209),
    heroBottom: Color(0xFF070504),
    heroGlow: Color(0xFFB8860B),
    navInactive: Color(0xFFCBBBA3),
    timerBadge: Color(0xFF1B5540),
    pillTop: Color(0xFF5A4430),
    pillBottom: Color(0xFF33231A),
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
        seedColor: const Color(0xFFB8860B),
        brightness: brightness,
      ),
      useMaterial3: true,
    );

    final palette = brightness == Brightness.dark
        ? HarajPalette._dark
        : HarajPalette._light;

    return base.copyWith(
      // أرضيّةُ الصفحة كريميّة في كل شاشة، لا في الرئيسية وحدها: شاشتان
      // بأرضيّتين مختلفتين تُريان وميضاً أبيض عند كل انتقال بينهما.
      scaffoldBackgroundColor: palette.pageBackground,
      textTheme: base.textTheme.apply(
        fontFamily: fontFamily,
        fontFamilyFallback: _fallbacks,
      ),
      primaryTextTheme: base.primaryTextTheme.apply(
        fontFamily: fontFamily,
        fontFamilyFallback: _fallbacks,
      ),
      extensions: <ThemeExtension<dynamic>>[palette],
    );
  }
}
