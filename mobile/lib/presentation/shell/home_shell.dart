import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../app/router.dart';
import '../../app/theme.dart';
import '../../l10n/generated/app_localizations.dart';
import '../catalog/widgets/home_hero.dart';

/// الأقسام الخمسة في الشريط السفليّ، **بترتيب ظهورها**.
///
/// تعدادٌ لا قائمةُ عناصرٍ مكتوبة في `build`: الترتيب هنا هو ترتيب الفروع في
/// `StatefulShellRoute`، والاثنان يُقرأان بالفهرس. قائمتان تفترقان عند أول
/// إضافةٍ في إحداهما، فيفتح قسمُ «المفضلة» شاشةَ «المحفظة» — عطلٌ لا يكشفه
/// إلا مستخدم. **فأي تبديلٍ في ترتيب هذا التعداد يُبدَّل معه ترتيب الفروع في
/// `appRoutes()` في نفس التعديل**، وقد بُدّل معاً هنا.
enum HomeSection {
  /// بيتٌ لا سيّارة: القسم اسمُه «الرئيسية» لا «السيّارات»، والبيتُ هو ما
  /// تقرؤه كل عينٍ «ابدأ من هنا» بلا تأمّل — والسيّارةُ تنازعُ صورَ الكروت
  /// التي تحتها على المعنى نفسه.
  home(Icons.home_outlined, Icons.home_rounded),

  /// فقاعةُ حديث: «مشاركاتي» ما دار بيني وبين المزاد — مزايداتٌ وفواتيرُ
  /// ومشتريات، وكلُّها أثرُ تبادلٍ لا وثيقةٌ ساكنة.
  ///
  /// **وموضعُها الثاني** — بُدِّلت بالمحفظة بطلب المالك في ٩ سبتمبر ٢٠٢٦.
  activity(Icons.chat_bubble_outline_rounded, Icons.chat_bubble_rounded),

  /// نجمةٌ لا قلب: القلبُ على كرت المركبة يعني «احفظها»، ونجمةُ الشريط تعني
  /// «المحفوظات». رمزٌ واحدٌ للفعل وللمكان يجعل من يضغط الشريط يظنّ أنه حفظ
  /// شيئاً.
  favourites(Icons.star_border_rounded, Icons.star_rounded),

  /// محفظةٌ لا بطاقة: المال هنا رصيدٌ ودلاء، لا وسيلةَ دفعٍ واحدة.
  wallet(
    Icons.account_balance_wallet_outlined,
    Icons.account_balance_wallet_rounded,
  ),

  account(Icons.person_outline_rounded, Icons.person_rounded);

  const HomeSection(this.icon, this.selectedIcon);

  /// أيقونتان لا واحدة: الفرق بين المختار وغيره **لا يُحمَّل على اللون وحده**.
  /// عينٌ لا تفرّق الذهبيَّ عن الكريميّ الخافت تفرّق الممتلئ عن المفرَّغ.
  final IconData icon;
  final IconData selectedIcon;

  /// النصّ من ملفّ الترجمة، والاختيار هنا لا هناك: التعداد يعرف نفسه، وملفّ
  /// الترجمة لا يعرف الترتيب.
  String label(AppLocalizations l10n) => switch (this) {
    HomeSection.home => l10n.navHome,
    HomeSection.wallet => l10n.navWallet,
    HomeSection.favourites => l10n.navFavourites,
    HomeSection.activity => l10n.navActivity,
    HomeSection.account => l10n.navAccount,
  };
}

/// القشرة التي تحمل الأقسام الخمسة وشريطها السفليّ.
///
/// **لكل قسمٍ مكدّسه** (`StatefulShellRoute.indexedStack`): من فتح مركبةً من
/// المفضلة ثم ذهب إلى المحفظة وعاد، يجد المركبة كما تركها لا رأس القسم. وهذا
/// هو الفرق بين شريطٍ يتنقّل بين خمس شاشات وشريطٍ يتنقّل بين خمسة **أقسام**.
///
/// **والهيدر هنا لا في الشاشات** — بطلب المالك في ٩ سبتمبر ٢٠٢٦: «نفس الهيدر
/// بالأيقونات في كل الصفحات». كان `HomeHero` في الرئيسية وحدها و`HarajAppBar`
/// باسم الشاشة في البقيّة، فيقرأ من ينتقل بينهما هيدرين لا هيدراً واحداً.
///
/// واسمُ الشاشة لم يسقط: نزل شريطاً تحته يرسمه `HarajAppBar` — والشاشاتُ
/// تحتفظ بـ`Scaffold` الخاصّ بها وبذلك الشريط.
class HomeShell extends StatelessWidget {
  const HomeShell({required this.navigationShell, super.key});

  final StatefulNavigationShell navigationShell;

  @override
  Widget build(BuildContext context) => Scaffold(
    // **`extendBody` عاد** لأن الشريط صار شفّافاً قليلاً بطلب المالك: بدونه
    // لا يمرّ خلفه إلا أرضيّةُ الـ`Scaffold`، فالشفافيّة تخلط البنّيَّ
    // بالكريميّ وتعطي بنّيّاً أفتحَ ثابتاً — لونٌ آخرُ لا شفافيّة.
    //
    // وثمنُه أن آخر صفٍّ يقع تحت الشريط، فيُدفع في `_BarInset`.
    extendBody: true,
    body: Column(
      children: <Widget>[
        // **خارج `_BarInset`**: الحاشيةُ التي يضيفها إنما تدفع المحتوى من
        // تحت الشريط السفليّ، والهيدرُ في الأعلى لا يمسّه.
        HomeHero(
          // الأزرارُ في الرئيسية وحدها — الشرحُ عند `showActions`.
          showActions: navigationShell.currentIndex == HomeSection.home.index,
          // لا شاشةَ إشعاراتٍ في التطبيق بعد، وأقربُ ما يجيب عن «ما الذي
          // حدث لي؟» هو مشاركاتي. والجرسُ يذهب إليها ولا يبقى زرّاً لا يفعل
          // شيئاً — زرٌّ لا يستجيب يُقرأ عطلاً.
          onOpenNotifications: () => context.go(Routes.myActivityPath),
          onOpenAccount: () => context.go(Routes.profilePath),
        ),
        Expanded(child: _BarInset(child: navigationShell)),
      ],
    ),
    bottomNavigationBar: _GoldNavigationBar(shell: navigationShell),
  );
}

/// يدفع محتوى الأقسام من تحت الشريط بارتفاعه.
///
/// **الارتفاع ثابتٌ مفروضٌ لا مقيسٌ ولا مخمَّن**: `_GoldNavigationBar` تفرضه
/// على صفّها بـ`SizedBox`، وهذه تقرأ نفس الثابت — فلا يمكن أن يتغيّر أحدهما
/// دون الآخر. كان في نسخةٍ سابقة رقماً مخمَّناً («١٢ + حدّان + ٨ + ٣٤ …
/// ≈ ٨٤») يفترق عن الشريط عند أول تعديل في حشوةٍ أو حجم أيقونة.
///
/// وحاشيةُ الجهاز تُضاف فوقه من `MediaQuery` لا تُخمَّن.
class _BarInset extends StatelessWidget {
  const _BarInset({required this.child});

  final Widget child;

  @override
  Widget build(BuildContext context) {
    final media = MediaQuery.of(context);
    return MediaQuery(
      data: media.copyWith(
        padding: media.padding.copyWith(
          bottom: media.padding.bottom + _GoldNavigationBar.barHeight,
        ),
      ),
      child: child,
    );
  }
}

/// الشريط السفليّ — بنّيٌّ داكن، والمختارُ ذهبيٌّ تحته خطّ.
///
/// **مبنيٌّ لا `NavigationBar`:** المطلوب تدرّجٌ داكن وزاويتان علويّتان
/// مدوّرتان وخطٌّ ذهبيّ تحت الاسم المختار وحركةٌ عند التبديل، وأربعتها تحتاج
/// نقضَ ثيم `NavigationBar` في أربعة مواضع — فيصير التخصيص أطول من البناء
/// وأهشَّ.
class _GoldNavigationBar extends StatelessWidget {
  const _GoldNavigationBar({required this.shell});

  final StatefulNavigationShell shell;

  /// الزاويتان العلويّتان وحدهما.
  ///
  /// **ممتدٌّ من حافةٍ لحافة لا عائم.** كان عائماً بهامشٍ من الجوانب، وذلك
  /// يصلح للزجاج — يُظهر المحتوى من تحته فيبدو الطمس. والداكنُ الصُّلب العائم
  /// يترك شريطاً كريميّاً تحته يُقرأ فراغاً منسيّاً، والممتدُّ يقفل الصفحة من
  /// أسفلها كما يقفلها الهيدر من أعلاها.
  static const double _radius = 22;

  /// حشوةُ الشريط حول صفّه.
  static const double _padTop = 8;
  static const double _padBottom = 6;

  /// ارتفاع الصفّ **مفروضاً**: أيقونة ٢٤ + ٤ + نصٌّ نحو ١٣ + ٤ + خطٌّ ٢،
  /// وحشوةُ العنصر ٣ فوق و٣ تحت = ٥٣، وثلاثة احتياطاً لخطِّ نظامٍ أكبر.
  ///
  /// **قُصّ الشريط من ٨٤ إلى ٧٠** بطلب المالك في ٩ سبتمبر ٢٠٢٦: أربعةَ عشرَ
  /// بكسلاً تعود إلى القائمة في كل شاشة. والقصُّ من الفراغات والحشوات لا من
  /// الأيقونة ولا من النصّ — أيقونةٌ أصغر من ٢٤ أو نصٌّ أصغر من ١٠٫٥ يُقرأان
  /// بجهدٍ على شاشةٍ صغيرة، والشريطُ هو ما يُضغط عليه بالإبهام.
  static const double _rowHeight = 56;

  /// ما يقرؤه `_BarInset` ليدفع المحتوى — **نفس الأرقام التي يُبنى بها
  /// الشريط**، فلا ينفصل الرقمان.
  static const double barHeight = _padTop + _rowHeight + _padBottom;

  /// شفافيّةُ الأرضيّة — بطلب المالك في ٩ سبتمبر ٢٠٢٦.
  ///
  /// **٠٫٩٢ لا أقلّ**: النصُّ الكريميُّ والأيقوناتُ فوقها، ونسبةُ تباينها
  /// محسوبةٌ على البنّيّ الصُّلب. وكلُّ نقطةِ شفافيّةٍ تُدخل لونَ ما يمرّ
  /// تحت الشريط في الأرضيّة — وما يمرّ كروتٌ بيضاء، فتفتحُ الأرضيّةَ وتُنقص
  /// التباين. عند هذا الحدّ يُرى المرورُ ويبقى النصُّ مقروءاً.
  static const double _opacity = 0.92;

  @override
  Widget build(BuildContext context) {
    final palette = HarajPalette.of(context);

    return DecoratedBox(
      decoration: BoxDecoration(
        borderRadius: const BorderRadius.vertical(
          top: Radius.circular(_radius),
        ),
        boxShadow: <BoxShadow>[
          // ظلٌّ صاعدٌ خافت: يرفع الشريط عن الورقة الكريميّة بلا خطٍّ يقطعها.
          //
          // وأضيقُ بعد القصّ: ظلٌّ بعشرين تحت شريطٍ بسبعين يصعد ثلثَ ارتفاعه
          // فيُقرأ الشريط أطولَ ممّا هو، وهو عكسُ المطلوب.
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.16),
            blurRadius: 14,
            offset: const Offset(0, -3),
          ),
        ],
      ),
      child: ClipRRect(
        borderRadius: const BorderRadius.vertical(
          top: Radius.circular(_radius),
        ),
        child: DecoratedBox(
          decoration: BoxDecoration(
            // **نفس تدرّج الهيدر بعينه** — `heroTop`/`heroBottom` وقطريّاً
            // من أعلى اليمين إلى أسفل اليسار، لا زوجاً خاصّاً بالشريط ولا
            // اتّجاهاً رأسيّاً. لونان قريبان لا متطابقان جعلا الفوتر يُقرأ
            // أعتم من الهيدر على الشاشة نفسها، واتّجاهان مختلفان يجعلان
            // الحافّتين المتقابلتين تفترقان في الإضاءة.
            gradient: LinearGradient(
              begin: Alignment.topRight,
              end: Alignment.bottomLeft,
              colors: <Color>[
                palette.heroTop.withValues(alpha: _opacity),
                palette.heroBottom.withValues(alpha: _opacity),
              ],
            ),
          ),
          child: Stack(
            children: <Widget>[
              // خيطٌ ذهبيّ على الحافّة العليا — نظيرُ الذي أسفل الهيدر، فيُقفل
              // التطبيق بين خطّين من لونٍ واحد.
              //
              // **`Positioned` لا `Align`:** ابنٌ غيرُ موضَّع في `Stack` هو ما
              // يُقاس به الشريط، و`Align` بلا `heightFactor` يتمدّد إلى آخر
              // القيود الواردة — وقيدُ `bottomNavigationBar` رخوٌ حتى ارتفاع
              // الشاشة. فبلع الشريطُ الشاشة كلها وطلع محتواه في أعلاها.
              Positioned(
                top: 0,
                // `left`/`right` لا `start`/`end`: الخيط متماثل، والاتجاه لا
                // يعني له شيئاً.
                left: 0,
                right: 0,
                child: Container(
                  height: 1.5,
                  decoration: BoxDecoration(
                    gradient: LinearGradient(
                      colors: <Color>[
                        palette.goldOnDark.withValues(alpha: 0),
                        palette.goldOnDark.withValues(alpha: 0.65),
                        palette.goldOnDark.withValues(alpha: 0),
                      ],
                    ),
                  ),
                ),
              ),
              SafeArea(
                top: false,
                child: Padding(
                  padding: const EdgeInsets.fromLTRB(4, _padTop, 4, _padBottom),
                  child: SizedBox(
                    height: _rowHeight,
                    child: Row(
                      children: <Widget>[
                        for (final section in HomeSection.values)
                          Expanded(
                            child: _NavigationItem(
                              section: section,
                              selected: shell.currentIndex == section.index,
                              onTap: () => shell.goBranch(
                                section.index,
                                // ضغطُ القسم المفتوح يعود إلى رأسه — سلوكٌ
                                // يتوقّعه من اعتاد التطبيقات: «رجّعني لأول
                                // الصفحة» بضغطةٍ على ما هو مفتوح أصلاً.
                                initialLocation:
                                    shell.currentIndex == section.index,
                              ),
                            ),
                          ),
                      ],
                    ),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _NavigationItem extends StatefulWidget {
  const _NavigationItem({
    required this.section,
    required this.selected,
    required this.onTap,
  });

  final HomeSection section;
  final bool selected;
  final VoidCallback onTap;

  @override
  State<_NavigationItem> createState() => _NavigationItemState();
}

class _NavigationItemState extends State<_NavigationItem> {
  /// هل المؤشّر فوق العنصر — على الويب وسطح المكتب وحدهما.
  ///
  /// **لا أثر له على الجوّال**: لا مؤشّر هناك، فلا يدخل `MouseRegion` في
  /// شيء ولا يُبنى شيءٌ لأجله. وتركُه يعمل في المنصّتين أهونُ من شرطٍ على
  /// المنصّة يُنسى تحديثُه.
  bool _hovered = false;

  /// زمنٌ قصير: الحركة هنا تؤكّد ما فعله المستخدم، ولا تجعله ينتظرها.
  static const Duration _duration = Duration(milliseconds: 220);

  HomeSection get section => widget.section;
  bool get selected => widget.selected;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final palette = HarajPalette.of(context);
    final label = section.label(l10n);
    // الهافر يُقرّب اللون نحو الذهبيّ ولا يقفز إليه: قفزةٌ كاملة تجعل العنصر
    // المُحوَّم عليه يبدو مختاراً، فيضيع الفرق بين «هنا أنت» و«هنا مؤشّرك».
    final colour = selected
        ? palette.goldOnDark
        : _hovered
        ? Color.lerp(palette.navInactive, palette.goldOnDark, 0.55)!
        : palette.navInactive;

    return Semantics(
      // القارئ الصوتيّ يقول «مختار» ولا يترك الفرق للّون: اللون لا يُقرأ.
      selected: selected,
      button: true,
      label: label,
      child: MouseRegion(
        onEnter: (_) => setState(() => _hovered = true),
        onExit: (_) => setState(() => _hovered = false),
        child: InkWell(
          onTap: widget.onTap,
          borderRadius: BorderRadius.circular(16),
          // اللمسة والهافر ذهبيّان: تموّجٌ رماديّ على أرضيّةٍ بنّيّةٍ داكنة لا
          // يكاد يظهر.
          splashColor: palette.goldMuted,
          highlightColor: palette.goldMuted,
          hoverColor: palette.goldOnDark.withValues(alpha: 0.08),
          child: Padding(
            padding: const EdgeInsets.symmetric(vertical: 3),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: <Widget>[
                AnimatedScale(
                  duration: _duration,
                  curve: Curves.easeOutCubic,
                  // رفعةٌ محسوسةٌ لا مرئيّة: ٤٪ تكفي ليشعر المؤشّر بأن العنصر
                  // حيّ، وأكثرُ منها يزيح جاره في صفٍّ ضيّق.
                  scale: _hovered && !selected ? 1.04 : 1,
                  child: Icon(
                    selected ? section.selectedIcon : section.icon,
                    // حجمان لا حجمٌ واحد: المختار أكبر بقدرٍ يُلحَظ ولا يقفز.
                    size: selected ? 24 : 21,
                    color: colour,
                    // هالةٌ ذهبيّة خلف المختار: ضوءٌ لا حدّ، فيبقى الشكل
                    // واحداً في الحالتين ويتغيّر إضاءةً لا هيئة.
                    shadows: selected
                        ? <Shadow>[
                            // هالةٌ أضيق بعد قصّ الشريط: نفس الوهج على
                            // أيقونةٍ أصغر يفيض عليها فيُقرأ ضباباً لا ضوءاً.
                            Shadow(
                              color: palette.goldOnDark.withValues(alpha: 0.45),
                              blurRadius: 9,
                            ),
                          ]
                        : const <Shadow>[],
                  ),
                ),
                const SizedBox(height: 4),
                // `AnimatedDefaultTextStyle` لا `Text` بلونٍ متبدّل: اللون
                // والوزن يتحرّكان مع الخطّ، فلا يسبق أحدهما الآخر.
                AnimatedDefaultTextStyle(
                  duration: _duration,
                  curve: Curves.easeOutCubic,
                  style: TextStyle(
                    color: colour,
                    fontSize: 10.5,
                    // تباعدٌ موجبٌ خفيف: خمسةُ أسماءٍ عربيّةٍ قصيرة متجاورة
                    // بوزن ٧٠٠ تتراصّ حروفُها، فيُقرأ الاسمُ كتلةً.
                    letterSpacing: 0.15,
                    // **عريضٌ في الحالتين.** الخطّ لا يحمل إلا ٤٠٠ و٥٠٠ و٧٠٠،
                    // فوزنٌ بينهما لا وجود له ويُقرَّب صامتاً. والتمييز محمولٌ
                    // على ثلاث إشاراتٍ أخرى: الخطّ، والأيقونة الممتلئة،
                    // والذهبيّ — تكفي بلا أن يخفت النصّ.
                    fontWeight: FontWeight.w700,
                    fontFamily: HarajTheme.fontFamily,
                    height: 1.2,
                  ),
                  child: Text(
                    label,
                    maxLines: 1,
                    // القصّ لا الالتفاف: سطرٌ ثانٍ يطيل الشريط ويزيح المحتوى.
                    overflow: TextOverflow.ellipsis,
                    textAlign: TextAlign.center,
                  ),
                ),
                const SizedBox(height: 4),
                // **خطٌّ تحت الاسم** لا حوضٌ حول الأيقونة.
                //
                // الحوضُ يحبس الأيقونة في كبسولةٍ فتبدو زرّاً داخل زرّ، والخطُّ
                // علامةٌ لا شكل: يقول «هذا هو» بأقلّ حبرٍ ممكن، ولا ينازع
                // الأيقونةَ ولا النصَّ على مساحتهما.
                AnimatedContainer(
                  duration: _duration,
                  curve: Curves.easeOutCubic,
                  width: selected ? 18 : 0,
                  height: 2,
                  decoration: BoxDecoration(
                    color: palette.goldOnDark,
                    borderRadius: BorderRadius.circular(2),
                    boxShadow: selected
                        ? <BoxShadow>[
                            BoxShadow(
                              color: palette.goldOnDark.withValues(alpha: 0.5),
                              blurRadius: 5,
                            ),
                          ]
                        : const <BoxShadow>[],
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
