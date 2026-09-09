import 'package:flutter/material.dart';

import '../../../app/theme.dart';
import '../../../l10n/generated/app_localizations.dart';

/// هيدر الرئيسية — **لهذه الشاشة وحدها**، لا `HarajAppBar`.
///
/// بقيّة الشاشات تحتفظ بالهيدر الأخضر الموحّد؛ والرئيسية وحدها تحمل هذا.
/// **ولماذا استثناء:** الهيدر الموحّد شريطُ عنوانٍ ارتفاعه ٥٦، ووظيفتُه أن
/// يقول «أنت في المحفظة». وهذا لوحةُ فتحٍ ووظيفتُها أن تقول ما هو التطبيق لمن
/// فتحه أول مرّة. حشرُ الاثنين في مكوّنٍ واحدٍ بشرطٍ `isHome` يجعل كل تعديلٍ
/// على أحدهما يمرّ على الآخر.
///
/// **ولا صورةَ فيه** — جُرِّبت ثم حُذفت بقرار المالك، والسبب الذي ظهر في
/// التجربة يستحقّ أن يُكتب: بانرٌ نسبتُه ٢٫٥:١ يحمل نصَّه مطبوعاً فيه لا يصلح
/// هيدراً لتطبيق. النصُّ فيه لا يُترجَم، ولا يكبر مع خطّ النظام، ولا يقرؤه
/// قارئُ الشاشة؛ ونسبتُه الثابتة تعطي على شاشةٍ عريضة لوحةً ارتفاعها نصفُ
/// الشاشة، وحدُّ الارتفاع يقصّ من كلامه، وحدُّ العرض يتركه جزيرةً في الوسط.
/// ثلاثةُ علاجاتٍ لكلٍّ عيبُه، لأن العلّة في الشكل نفسه لا في ضبطه.
///
/// فالنصُّ نصٌّ: يُترجَم، ويكبر مع الإعدادات، ويُقرأ صوتياً، ويتّسع لأي عرض.
/// وما حوله ضوءٌ ومعدنٌ مرسومان بالتدرّجات وحدها — بلا ملفٍّ يُشحن ولا كثافاتٍ
/// ثلاث.
///
/// **ولا زخرفةَ في خلفيّته.** جُرِّبت مرّتين: خطوطٌ قطريّة متوازية، ثم خطُّ
/// مزايدةٍ يصعد على درجات. وحُذفت الاثنتان بقرار المالك. والدرسُ الذي بقي:
/// شريطٌ ارتفاعُه ٥٨ بكسلاً لا يتّسع لرسمٍ يُقرأ — فإما أن يكون الرسمُ باهتاً
/// فيصير ضجيجاً بلا معنى، أو ظاهراً فينازع الاسمَ على النظر. والتدرّجُ والوهج
/// يعطيان العمقَ نفسه بلا أيٍّ من الثمنين.
///
/// **صفٌّ واحد: شارةٌ واسمٌ وزرّان.** كان تحته سطرا تعريف وفاصلٌ ذهبيّ
/// («سيارتك القادمة…» وما تحتها)، وحُذفت الثلاثة بقرار المالك — الغايةُ
/// هيدرٌ قصير. ونصّا السطرين باقيان في ملفّ الترجمة (`homeTagline`،
/// `homeSubtagline`) ولا يقرؤهما أحد: تُركا ليُعادا بسطرٍ واحد إن رجع القرار،
/// وحذفُهما من `arb` تعديلٌ في ملفَّي ترجمةٍ مقابل لا شيء.
class HomeHero extends StatelessWidget {
  const HomeHero({
    required this.onOpenNotifications,
    required this.onOpenAccount,
    this.showActions = true,
    super.key,
  });

  final VoidCallback onOpenNotifications;
  final VoidCallback onOpenAccount;

  /// هل يظهر الجرسُ وزرُّ الحساب — **في الرئيسية وحدها** بطلب المالك في ٩
  /// سبتمبر ٢٠٢٦.
  ///
  /// وعلّتُه أن الزرّين مقبضان إلى قسمين في الشريط السفليّ: من هو في
  /// «مشاركاتي» يرى جرساً يفتح «مشاركاتي»، ومن هو في «حسابي» يرى زرّ حسابٍ
  /// يفتح حسابه. ومقبضٌ يعيدك إلى مكانك يُقرأ عطلاً.
  ///
  /// **وبدونهما تتوسّط العلامة**: صفٌّ بعنصرٍ واحدٍ متراصٍّ يميناً يترك ثلثي
  /// اللوحة فارغاً.
  final bool showActions;

  /// أدنى ارتفاع — **حدٌّ لا مقاس**.
  ///
  /// اللوحة تقيس نفسها بمحتواها: ارتفاعٌ ثابت مع `Spacer` بداخله كان يفيض
  /// ٤٦ بكسلاً لأن الخطّ العربيّ بحجم ٢٤ أطولُ من اللاتينيّ. والحدُّ الأدنى
  /// يمنعها من الانكماش على شاشةٍ يصغر فيها خطُّ النظام.
  ///
  /// **٥٨، بعد ثلاث قِصَر متتالية:** كان ١٤٦ حين كان تحت الاسم سطرا التعريف،
  /// فحُذفا بقرار المالك ونزل إلى ١٠٤ ثم ٨٦ ثم هنا. وما بقي في اللوحة صفٌّ
  /// واحد — شارةٌ واسمٌ وزرّان — فأيُّ ارتفاعٍ فوق ما يحتاجه الصفّ فراغٌ داكن
  /// فوق قائمةٍ فاتحة، ويُقرأ عطلاً لا أناقة.
  ///
  /// والرقم لا يحكم: محتوى الصفّ (شارةٌ ٣٠ + حشوةٌ ١٤) يبلغه، فهو حدٌّ يمنع
  /// الانكماش على شاشةٍ يصغر فيها خطُّ النظام لا مقاسٌ يُفرض.
  static const double _minHeight = 58;

  /// تدويرُ الحافّة السفلى وحدها — اللوحة تنتهي بقوسٍ فوق الورقة الكريميّة.
  static const double _bottomRadius = 24;

  @override
  Widget build(BuildContext context) {
    final palette = HarajPalette.of(context);
    final l10n = AppLocalizations.of(context);
    final theme = Theme.of(context);
    final topInset = MediaQuery.paddingOf(context).top;

    return ClipRRect(
      borderRadius: const BorderRadius.vertical(
        bottom: Radius.circular(_bottomRadius),
      ),
      child: ConstrainedBox(
        constraints: BoxConstraints(minHeight: _minHeight + topInset),
        child: Stack(
          // **الوسط لا الأعلى.** الصفّ أقصرُ من الحدّ الأدنى للوحة، والفائض
          // كان ينزل كلُّه تحته لأن `Stack` تحاذي أبناءها غير الموضَّعين من
          // أعلاها — فيبدو الاسمُ والزرّان مرفوعَين عن وسط المستطيل. والمحاذاة
          // من الوسط تقسم الفائض عليهما.
          //
          // ولا أثر لها على جوّالٍ ذي نتوء: حاشيةُ النظام تدخل في `SafeArea`
          // فيصير الابن أطولَ من الحدّ الأدنى، ولا فائض يُقسَم.
          alignment: Alignment.center,
          children: <Widget>[
            // الأرضيّة والضوء **موضَّعان**، والمحتوى وحده غيرُ موضَّع: في
            // `Stack` يُقاس الحجم بغير الموضَّع، فلو مُلئت الأرضيّة بابنٍ
            // عاديّ لتمدّدت إلى آخر القيود وابتلعت اللوحةُ الشاشة.
            Positioned.fill(
              child: DecoratedBox(
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    begin: Alignment.topRight,
                    end: Alignment.bottomLeft,
                    colors: <Color>[palette.heroTop, palette.heroBottom],
                  ),
                ),
              ),
            ),
            // وهجٌ شعاعيّ خلف اسم العلامة: الضوء يأتي من نقطة لا من حافّة،
            // وهو ما يفرّق «لوحة» عن «مستطيلٍ بنّيّ».
            Positioned.fill(
              child: DecoratedBox(
                decoration: BoxDecoration(
                  gradient: RadialGradient(
                    center: const Alignment(0.55, -0.35),
                    radius: 1.05,
                    colors: <Color>[
                      palette.heroGlow.withValues(alpha: 0.34),
                      palette.heroGlow.withValues(alpha: 0.10),
                      palette.heroGlow.withValues(alpha: 0),
                    ],
                    stops: const <double>[0, 0.42, 1],
                  ),
                ),
              ),
            ),
            // لمعةٌ قطريّة تمرّ في اللوحة — أثرُ معدنٍ لا شكلٌ يُتعرَّف عليه.
            // شفافيّتُها ٧٪: ما يُلحَظ ولا يُقرأ.
            Positioned.fill(
              child: DecoratedBox(
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                    colors: <Color>[
                      palette.goldOnDark.withValues(alpha: 0),
                      palette.goldOnDark.withValues(alpha: 0.07),
                      palette.goldOnDark.withValues(alpha: 0),
                    ],
                    stops: const <double>[0.30, 0.46, 0.62],
                  ),
                ),
              ),
            ),
            // نقاطٌ ذهبيّة في الخلفيّة — تحت المحتوى وفوق الضوء.
            const Positioned(
              left: 0,
              right: 0,
              top: 0,
              bottom: 0,
              child: _Dots(),
            ),
            SafeArea(
              bottom: false,
              child: Padding(
                padding: const EdgeInsets.fromLTRB(20, 7, 20, 7),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  // في RTL هذه هي اليمين — وكلُّ نصّ اللوحة يبدأ من اليمين.
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Row(
                      mainAxisAlignment: showActions
                          ? MainAxisAlignment.start
                          : MainAxisAlignment.center,
                      children: <Widget>[
                        // **`Expanded` لا `Spacer` بعده:** الاسم صفٌّ يقيس
                        // نفسه، ولو تُرك بلا حدٍّ أخذ عرضه كاملاً ودفع
                        // الزرّين خارج اللوحة. و`Expanded` يعطيه ما بقي بعد
                        // الزرّين لا قبلهما. وبلا زرّين لا حدَّ يلزمه: الصفُّ
                        // يقيس نفسه ويتوسّط.
                        if (showActions)
                          Expanded(
                            child: _Brand(
                              palette: palette,
                              theme: theme,
                              l10n: l10n,
                            ),
                          )
                        else
                          Flexible(
                            child: _Brand(
                              palette: palette,
                              theme: theme,
                              l10n: l10n,
                            ),
                          ),
                        // الأزرار في الطرف الآخر — يسارُ الشاشة في العربية.
                        if (showActions) ...<Widget>[
                          _CircleAction(
                            icon: Icons.notifications_none_rounded,
                            tooltip: l10n.homeNotifications,
                            onTap: onOpenNotifications,
                            palette: palette,
                          ),
                          const SizedBox(width: 10),
                          _CircleAction(
                            icon: Icons.person_outline_rounded,
                            tooltip: l10n.homeAccountAction,
                            onTap: onOpenAccount,
                            palette: palette,
                          ),
                        ],
                      ],
                    ),
                  ],
                ),
              ),
            ),
            // ظلٌّ داخليّ على الحافّة السفلى: يعطي اللوحةَ سُمكاً فتبدو الورقةُ
            // الكريميّة منزلقةً تحتها لا ملصوقةً بها. تدرّجٌ إلى الشفافيّة لا
            // خطٌّ — الخطّ يقطع، والتدرّجُ يُعمِّق.
            Positioned(
              bottom: 0,
              left: 0,
              right: 0,
              child: SizedBox(
                height: 16,
                child: DecoratedBox(
                  decoration: BoxDecoration(
                    gradient: LinearGradient(
                      begin: Alignment.bottomCenter,
                      end: Alignment.topCenter,
                      colors: <Color>[
                        Colors.black.withValues(alpha: 0.32),
                        Colors.black.withValues(alpha: 0),
                      ],
                    ),
                  ),
                ),
              ),
            ),
            // خيطٌ ذهبيّ على الحافّة السفلى — نظيرُ الذي أعلى الشريط السفليّ،
            // فيُقفل التطبيق بين خطّين من لونٍ واحد.
            //
            // **`Positioned` لا `Align`:** الثاني يتمدّد إلى آخر القيود
            // الواردة، وقيدُ اللوحة رخوٌ حتى ارتفاع الشاشة — فيبتلع الخيطُ
            // الشاشة ويُقاس به الهيدر. حدث حرفياً في الشريط السفليّ.
            Positioned(
              bottom: 0,
              left: 0,
              right: 0,
              child: Container(
                height: 2,
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    colors: <Color>[
                      palette.goldOnDark.withValues(alpha: 0),
                      palette.goldOnDark.withValues(alpha: 0.75),
                      palette.goldOnDark.withValues(alpha: 0),
                    ],
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// نقاطٌ ذهبيّة متناثرة في خلفيّة اللوحة.
///
/// **نقاطٌ لا خطوط.** جُرِّب في هذا الموضع رسمان — خطوطٌ قطريّة وخطُّ مزايدة —
/// وحُذف كلاهما: شريطٌ ارتفاعُه ٥٨ بكسلاً لا يتّسع لشكلٍ يُقرأ، فإما يخفت
/// فيصير ضجيجاً أو يظهر فينازع الاسم. والنقطة وحدها لا تدّعي معنًى: هي غبارُ
/// ضوءٍ يعطي العمقَ ولا يطلب أن يُفهَم.
class _Dots extends StatelessWidget {
  const _Dots();

  @override
  Widget build(BuildContext context) {
    final palette = HarajPalette.of(context);
    // **`ClipRect` و`RepaintBoundary`:** الأول يحبس الرسم داخل اللوحة؛ والثاني
    // يمنع إعادة رسمه مع كل إطارٍ من تمرير القائمة فوقه — وهو ثابتٌ لا يتغيّر
    // (H2).
    return RepaintBoundary(
      child: ClipRect(
        child: CustomPaint(painter: _DotsPainter(palette.goldOnDark)),
      ),
    );
  }
}

class _DotsPainter extends CustomPainter {
  const _DotsPainter(this.gold);

  final Color gold;

  /// موضعُ كل نقطة ككسرٍ من المساحة، ونصفُ قطرها، وشدّتُها.
  ///
  /// **كسورٌ لا بكسلات:** أرقامٌ ثابتة تتكوّم في طرفٍ على شاشةٍ عريضة. والمواضع
  /// والأحجام والشدّات غيرُ منتظمة عمداً — نقاطٌ متساوية على شبكةٍ تُقرأ نسيجاً
  /// مطبوعاً لا غبارَ ضوء.
  ///
  /// ولا نقطةَ يمينَ ٠٫٧٥: هناك يسكن اسمُ العلامة، ونقطةٌ خلف حرفٍ ذهبيّ تُقرأ
  /// شائبةً في الخطّ.
  static const List<({double x, double y, double r, double alpha})> _dots =
      <({double x, double y, double r, double alpha})>[
        (x: 0.09, y: 0.30, r: 1.6, alpha: 0.30),
        (x: 0.15, y: 0.72, r: 1.0, alpha: 0.18),
        (x: 0.24, y: 0.22, r: 2.2, alpha: 0.22),
        (x: 0.31, y: 0.60, r: 1.2, alpha: 0.34),
        (x: 0.39, y: 0.36, r: 1.0, alpha: 0.16),
        (x: 0.46, y: 0.78, r: 1.8, alpha: 0.26),
        (x: 0.53, y: 0.26, r: 1.1, alpha: 0.20),
        (x: 0.61, y: 0.66, r: 2.4, alpha: 0.14),
        (x: 0.68, y: 0.40, r: 1.3, alpha: 0.28),
      ];

  @override
  void paint(Canvas canvas, Size size) {
    for (final dot in _dots) {
      final centre = Offset(size.width * dot.x, size.height * dot.y);
      canvas
        // هالةٌ خافتة حول كل نقطة: قرصٌ صلبٌ بقطر بكسلين يظهر حبّةَ غبارٍ على
        // الشاشة، والهالةُ تجعله ضوءاً.
        ..drawCircle(
          centre,
          dot.r * 3,
          Paint()..color = gold.withValues(alpha: dot.alpha * 0.22),
        )
        ..drawCircle(
          centre,
          dot.r,
          Paint()..color = gold.withValues(alpha: dot.alpha),
        );
    }
  }

  @override
  bool shouldRepaint(_DotsPainter old) => old.gold != gold;
}

/// شارةُ المطرقة واسمُ العلامة بجوارها./// شارةُ المطرقة واسمُ العلامة بجوارها.
///
/// **صفٌّ لا عمود:** الاسم في عمودٍ تحت أيقونته يطيل اللوحة بلا أن يضيف
/// شيئاً، والصفُّ يترك ما تحته للسطرين — وهما ما يقول للعميل ما هذا التطبيق.
class _Brand extends StatelessWidget {
  const _Brand({
    required this.palette,
    required this.theme,
    required this.l10n,
  });

  final HarajPalette palette;
  final ThemeData theme;
  final AppLocalizations l10n;

  @override
  Widget build(BuildContext context) => Row(
    mainAxisSize: MainAxisSize.min,
    children: <Widget>[
      Container(
        width: 30,
        height: 30,
        decoration: BoxDecoration(
          shape: BoxShape.circle,
          // حلقةٌ ذهبيّة وقلبٌ شفّاف: قرصٌ مصمت يصير بقعةً ثقيلة في زاوية
          // اللوحة، والحلقةُ تحدّ الأيقونة بلا أن تنازعها.
          border: Border.all(
            color: palette.goldOnDark.withValues(alpha: 0.55),
            width: 1.4,
          ),
          color: palette.goldOnDark.withValues(alpha: 0.10),
          // هالةٌ خارجيّة خافتة: تفصل الشارة عن التدرّج خلفها فلا تبدو
          // ملصقةً عليه، بلا حدٍّ ثانٍ ينافس الحلقة.
          boxShadow: <BoxShadow>[
            BoxShadow(
              color: palette.heroGlow.withValues(alpha: 0.28),
              blurRadius: 16,
              spreadRadius: 1,
            ),
          ],
        ),
        child: Icon(Icons.gavel_rounded, size: 16, color: palette.goldOnDark),
      ),
      const SizedBox(width: 10),
      // **`Flexible` وقصٌّ:** الاسم صار ثلاث كلمات بدل واحدة، وصفٌّ يحمله
      // بحجم العنوان مع زرّين على جوّالٍ ضيّق يفيض. والقصُّ آخرُ ما يقع —
      // بعد أن يأخذ الاسم كل ما تركه الزرّان.
      Flexible(
        child: Text(
          l10n.homeBrand,
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
          style: theme.textTheme.titleMedium?.copyWith(
            color: palette.goldOnDark,
            fontWeight: FontWeight.w700,
            // تباعدٌ موجبٌ خفيف: تباعدُ الحروف يعطي الاسمَ وقارَ العلامة بدل
            // أن يُقرأ عنوانَ شاشة.
            letterSpacing: 0.5,
            // ظلٌّ ذهبيّ: الاسم يقع على الوهج نفسه، وبلا فصلٍ عنه يذوب حرفُه
            // في ضوئه.
            shadows: <Shadow>[
              Shadow(
                color: palette.heroGlow.withValues(alpha: 0.60),
                blurRadius: 20,
              ),
            ],
          ),
        ),
      ),
    ],
  );
}

/// زرٌّ دائريّ زجاجيّ في أعلى اللوحة.
class _CircleAction extends StatelessWidget {
  const _CircleAction({
    required this.icon,
    required this.tooltip,
    required this.onTap,
    required this.palette,
  });

  final IconData icon;
  final String tooltip;
  final VoidCallback onTap;
  final HarajPalette palette;

  @override
  Widget build(BuildContext context) => Tooltip(
    message: tooltip,
    child: Semantics(
      button: true,
      label: tooltip,
      child: Material(
        // أبيضُ شفّاف لا لونٌ صُلب: الزرّ يقع على تدرّجٍ يتغيّر تحته، ولونٌ
        // صُلب يظهر مربّعاً في طرفٍ ويختفي في آخر.
        color: Colors.white.withValues(alpha: 0.12),
        shape: CircleBorder(
          side: BorderSide(color: palette.goldOnDark.withValues(alpha: 0.30)),
        ),
        child: InkWell(
          onTap: onTap,
          customBorder: const CircleBorder(),
          child: Padding(
            padding: const EdgeInsets.all(7),
            child: Icon(icon, size: 18, color: Colors.white),
          ),
        ),
      ),
    ),
  );
}
