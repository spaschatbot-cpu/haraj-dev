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
    required this.ink,
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
    required this.sky,
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

  /// الكحليُّ الغامق: لونُ العناوين على الكروت البيضاء.
  ///
  /// **كان بنّيّاً** (`#2E2118`) حتى ٩ سبتمبر ٢٠٢٦، فبُدِّلت عائلةُ البنّيّ
  /// كلُّها بالكحليّ بقرار المالك. والاسمُ `ink` لا `brown`: حقلٌ اسمُه لونٌ
  /// بعينه يصير كذبةً في أول تبديل، و«الحبر» يقول وظيفتَه لا صبغتَه.
  final Color ink;

  /// كحليٌّ باهت: سطرُ المواصفات على الكرت، وتسميةُ المبلغ فوقه.
  ///
  /// **لا رماديّ محايد**: الفرق بين الأساسيّ والثانويّ يُحمل على الشدّة لا على
  /// تبديل العائلة — ورماديٌّ بين كحليّاتٍ يُقرأ «معطَّلاً».
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

  /// وهجٌ أزرقُ لامعٌ في وسط الهيدر: هو ما يمنع الأرضيّةَ الداكنة من أن تكون
  /// مستطيلاً أسود. شعاعيٌّ لا خطّيّ — الضوء يأتي من نقطة لا من حافّة.
  ///
  /// **أزرقُ فاتحٌ على كحليٍّ غامق**: كان ذهبيّاً حين كانت العائلة بنّيّة،
  /// وبُدِّل مع اللون المميِّز كلِّه في ٩ سبتمبر ٢٠٢٦ — ذهبٌ واحدٌ بقي وسط
  /// أزرقَ كان يُقرأ بقيّةً من ثيمٍ قديم.
  final Color heroGlow;

  /// لونُ أيقونةِ ما ليس مختاراً ونصِّه: أزرقٌ فاتح على الأرضيّة الداكنة.
  ///
  /// **لا ذهبيٌّ باهت**: الذهبيُّ الباهت يُقرأ «معطَّل» لا «غير مختار»،
  /// والفرق بينهما هو كل معنى الشريط.
  final Color navInactive;

  /// أخضرُ حوض العدّاد على الصورة.
  ///
  /// أخضرُ لا ذهبيّ: الوقت الباقي خبرٌ عاجل لا زينة، ولونٌ من خارج عائلة
  /// العلامة هو ما يجعله يُلحَظ فوق صورةٍ ملوّنة.
  final Color timerBadge;

  /// طرفا تدرّج الزرّ الكحليّ — «تفاصيل المزاد» وما شابهه.
  final Color pillTop;
  final Color pillBottom;

  /// أرضيّةُ رأس الرئيسية الفاتحة («البيبي بلو») — من اللون الأساسيّ المختار،
  /// وفي الداكن كحليٌّ عميقٌ لا سماءٌ ساطعةٌ فوق صفحةٍ سوداء. كانت ثابتاً في
  /// [HarajSky] فبقيت زرقاءَ حين يختار العميلُ لوناً آخر.
  final Color sky;

  @override
  HarajPalette copyWith({
    Color? gold,
    Color? goldDeep,
    Color? goldMuted,
    Color? goldOnDark,
    Color? ink,
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
    Color? sky,
  }) => HarajPalette(
    gold: gold ?? this.gold,
    goldDeep: goldDeep ?? this.goldDeep,
    goldMuted: goldMuted ?? this.goldMuted,
    goldOnDark: goldOnDark ?? this.goldOnDark,
    ink: ink ?? this.ink,
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
    sky: sky ?? this.sky,
  );

  @override
  HarajPalette lerp(HarajPalette? other, double t) {
    if (other == null) return this;
    return HarajPalette(
      gold: Color.lerp(gold, other.gold, t)!,
      goldDeep: Color.lerp(goldDeep, other.goldDeep, t)!,
      goldMuted: Color.lerp(goldMuted, other.goldMuted, t)!,
      goldOnDark: Color.lerp(goldOnDark, other.goldOnDark, t)!,
      ink: Color.lerp(ink, other.ink, t)!,
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
      sky: Color.lerp(sky, other.sky, t)!,
    );
  }

  /// اللونُ من الثيم، أو الافتراضيّ إن لم يُسجَّل.
  ///
  /// لا `!` على الامتداد: ودجت تُبنى في اختبارٍ بثيمٍ عارٍ كانت ستنهار،
  /// وانهيارُ شاشةٍ بسبب لونٍ غير مسجَّل ثمنٌ لا يوازي شيئاً.
  static HarajPalette of(BuildContext context) =>
      Theme.of(context).extension<HarajPalette>() ?? _light;

  /// **الباليت «ج — بحريٌّ هادئ»** — نفسُ قيم الويب واللوحة (٧ أكتوبر ٢٠٢٦:
  /// «كل الصفح بنفس باليت الألوان»؛ `docs/palette.md`). كان الأزرقُ هنا
  /// صريحاً (`#1C6FD6`) والكحليُّ يكاد يكون أسود (`#050D17`)، فكان التطبيقُ
  /// يقول لوناً غيرَ الموقع. والأسماءُ لم تتغيّر — `gold` اسمٌ تاريخيّ
  /// لـ«اللون المميِّز» — فلا ودجت يحتاج تعديلاً.
  static const HarajPalette _light = HarajPalette(
    gold: Color(0xFF1E3A5F),
    goldDeep: Color(0xFF13233F),
    goldMuted: Color(0x241E3A5F),
    goldOnDark: Color(0xFFB9CDE4),
    ink: Color(0xFF1A2B40),
    inkMuted: Color(0xFF4A5B70),
    pageBackground: Color(0xFFF5F8FB),
    // **أبيضُ زجاجيّ لا أبيضُ مصمت** (طلبُ المالك، ٣ أكتوبر ٢٠٢٦): ٧٨٪ بياضاً
    // فوق أرضيّة `GlassBackdrop` يعبره لونُها فيُقرأ زجاجاً مصنفراً.
    cardSurface: Color(0xC7FFFFFF),
    heroTop: Color(0xFF1E3A5F),
    heroBottom: Color(0xFF13233F),
    heroGlow: Color(0xFF4F74A0),
    navInactive: Color(0xFFC9D6E5),
    timerBadge: Color(0xFF11624F),
    pillTop: Color(0xFF1E3A5F),
    pillBottom: Color(0xFF13233F),
    sky: HarajSky.top,
  );

  /// في الوضع الداكن تنقلب الأرضيّة ويُرفع الذهبيّ: نفس النسبة على خلفيّةٍ
  /// أعتم تبدو أضعف، فتُعوَّض بالسطوع لا بالحجم. والنصّ يصير بيجاً فاتحاً —
  /// بنّيٌّ غامق على أسود لا يُقرأ. والشريط السفليّ **لا يتغيّر كثيراً**:
  /// كان داكناً أصلاً، وتغميقُه أكثر يُذيبه في أرضيّةٍ صارت داكنة، فرُفع
  /// قليلاً ليبقى له حدٌّ يُرى.
  static const HarajPalette _dark = HarajPalette(
    gold: Color(0xFF6FB0F5),
    goldDeep: Color(0xFF3E8BD8),
    goldMuted: Color(0x2E6FB0F5),
    goldOnDark: Color(0xFFA9D0F9),
    ink: Color(0xFFDDE8F3),
    inkMuted: Color(0xFF8FA5BC),
    pageBackground: Color(0xFF0A121B),
    cardSurface: Color(0xFF13202D),
    heroTop: Color(0xFF0B1826),
    heroBottom: Color(0xFF040A11),
    heroGlow: Color(0xFF2E86E0),
    navInactive: Color(0xFFB7CADD),
    timerBadge: Color(0xFF1B5540),
    pillTop: Color(0xFF27466B),
    pillBottom: Color(0xFF15293D),
    sky: Color(0xFF0B1826),
  );
}

/// **اللونُ الأساسيّ** — الثمانيةُ نفسُها التي في درج «المظهر» بلوحة
/// الموظّفين (`theme.js` و`app.css`، كتلُ `data-accent`)، بقيمها: طلبُ المالك
/// (١٢ أكتوبر ٢٠٢٦) «نفس الحتّة اللي في الويب». والافتراضُ `azure`، وقيمُه
/// في اللوحة هي الباليت «ج» نفسُها — فمن لم يختر شيئاً يرى التطبيقَ كما كان.
///
/// خمسُ درجاتٍ لكلّ لون، أسماؤها أسماءُ اللوحة: `a700` نصٌّ وزرٌّ على الأبيض،
/// و`dim` طرفُ التدرّج الداكن، و`a500` حدٌّ ووهج، و`a300` اللونُ على الداكن،
/// و`a050` أرضيّةٌ فاتحة.
enum HarajAccent {
  azure(
    Color(0xFF1E3A5F),
    Color(0xFF13233F),
    Color(0xFF4F74A0),
    Color(0xFFB9CDE4),
    Color(0xFFEEF3F9),
  ),
  sea(
    Color(0xFF0B6F97),
    Color(0xFF0C2836),
    Color(0xFF1F97C4),
    Color(0xFF7ECFE9),
    Color(0xFFE2F3FB),
  ),
  gold(
    Color(0xFF6D5209),
    Color(0xFF2B2308),
    Color(0xFFA88118),
    Color(0xFFD9B45C),
    Color(0xFFFAF2DD),
  ),
  violet(
    Color(0xFF6127C4),
    Color(0xFF221A3D),
    Color(0xFF8B5CF6),
    Color(0xFFBDA6F4),
    Color(0xFFF1ECFD),
  ),
  teal(
    Color(0xFF0C766E),
    Color(0xFF0B2C2A),
    Color(0xFF159E95),
    Color(0xFF6ED2CA),
    Color(0xFFE2F5F3),
  ),
  emerald(
    Color(0xFF077547),
    Color(0xFF0A2C1E),
    Color(0xFF109D5F),
    Color(0xFF74D5A7),
    Color(0xFFE6F6EE),
  ),
  amber(
    Color(0xFF8F5D09),
    Color(0xFF2E2410),
    Color(0xFFBC7A0D),
    Color(0xFFF2C96F),
    Color(0xFFFDF2DA),
  ),
  rose(
    Color(0xFFB0113A),
    Color(0xFF2E1119),
    Color(0xFFEF4463),
    Color(0xFFF5A0AF),
    Color(0xFFFDEAEE),
  );

  const HarajAccent(this.a700, this.dim, this.a500, this.a300, this.a050);

  final Color a700;
  final Color dim;
  final Color a500;
  final Color a300;
  final Color a050;

  /// قيمةٌ مخزَّنة لا تطابق لوناً تسقط إلى الافتراض — كـ`ALLOWED` في `theme.js`.
  static HarajAccent parse(String? name) => HarajAccent.values.firstWhere(
    (accent) => accent.name == name,
    orElse: () => HarajAccent.azure,
  );

  /// الباليتُ بهذا اللون: يتبدّل **اللونُ المميِّز وحدَه** — الأيقونةُ المختارة
  /// والأزرارُ والهيدرُ والتدرّج. والحبرُ والأرضيّةُ والبطاقاتُ وأخضرُ العدّاد
  /// تبقى، كما في اللوحة: «ألوانُ البطاقات… تصنيفٌ لا زينة».
  HarajPalette palette(Brightness brightness) {
    if (brightness == Brightness.dark) {
      // **الدرجةُ الوسطى لا الفاتحة** على الداكن: `gold` لونُ الأزرار بنصٍّ
      // أبيض كما هو لونُ الأيقونة المختارة، والفاتحةُ تحت الأبيض لا تُقرأ —
      // قِيس في «المظهر» نفسه. والوسطى ما تستعمله اللوحةُ في داكنها. والكحليُّ
      // وسطُه غامقٌ على الأسود، فيأخذ أزرقَ الداكن الأصليّ الأوسط (`#3E8BD8`).
      final mid = this == HarajAccent.azure ? const Color(0xFF3E8BD8) : a500;
      return HarajPalette._dark.copyWith(
        gold: mid,
        goldDeep: a300,
        goldMuted: mid.withValues(alpha: 0.18),
        goldOnDark: Color.lerp(a300, Colors.white, 0.35),
        heroTop: Color.lerp(dim, const Color(0xFF0B1826), 0.4),
        heroBottom: const Color(0xFF040A11),
        heroGlow: a500,
        pillTop: a700,
        pillBottom: dim,
        sky: Color.lerp(dim, const Color(0xFF0B1826), 0.4),
      );
    }
    if (this == HarajAccent.azure) return HarajPalette._light;
    return HarajPalette._light.copyWith(
      gold: a700,
      goldDeep: dim,
      goldMuted: a700.withValues(alpha: 0.14),
      goldOnDark: a300,
      heroTop: a700,
      heroBottom: dim,
      heroGlow: a500,
      pillTop: a700,
      pillBottom: dim,
      sky: a050,
    );
  }
}

/// **البيبي بلو** — أرضيّةُ رأس الرئيسية وشريطِ الأقسام السفليّ.
///
/// بأمر المالك (٢٩ سبتمبر ٢٠٢٦): «في الصفحة الرئيسية الألوان بيبي بلو، مش
/// البلو الغامق». كان الاثنان على `heroTop`/`heroBottom` الكحليّين. وبقي ذلك
/// الزوجُ لما سواهما (هيدرُ الشاشات الداخليّة، وقرصُ الشعار) — لم يُطلب.
///
/// **والنصُّ فوقه كحليٌّ لا أبيض**: الأبيضُ على `#BBDEFB` نسبتُه ١٫٤:١ فلا
/// يُقرأ، و`ink` عليه ١١:١.
abstract final class HarajSky {
  // من سطح الكحليّ في الباليت «ج» — ما زال سماويّاً فاتحاً كما طلب المالك،
  // لكنه من عائلة الويب واللوحة لا أزرقُ Material منفرد.
  static const Color top = Color(0xFFEEF3F9);
  static const Color bottom = Color(0xFFCFDCEC);
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

  static ThemeData light([HarajAccent accent = HarajAccent.azure]) =>
      _build(Brightness.light, accent);

  static ThemeData dark([HarajAccent accent = HarajAccent.azure]) =>
      _build(Brightness.dark, accent);

  static ThemeData _build(Brightness brightness, HarajAccent accent) {
    // **البذرةُ من اللون المختار** لا كحليٌّ ثابت: أزرارُ Material ومؤشّراتُها
    // ومفاتيحُها تُشتقّ منها، فتتبع اللونَ مع بقيّة التطبيق.
    final base = ThemeData(
      brightness: brightness,
      colorScheme: ColorScheme.fromSeed(
        seedColor: accent.a700,
        brightness: brightness,
      ),
      useMaterial3: true,
    );

    final palette = accent.palette(brightness);

    return base.copyWith(
      // أرضيّةُ الصفحة كريميّة في كل شاشة، لا في الرئيسية وحدها: شاشتان
      // بأرضيّتين مختلفتين تُريان وميضاً أبيض عند كل انتقال بينهما.
      // **شفّافةٌ في الفاتح**: الأرضيّةُ `GlassBackdrop` تحت التنقّل كلِّه
      // (`HarajApp.builder`)، والشاشةُ فوقها لا تغطّيها.
      scaffoldBackgroundColor: brightness == Brightness.light
          ? Colors.transparent
          : palette.pageBackground,
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
