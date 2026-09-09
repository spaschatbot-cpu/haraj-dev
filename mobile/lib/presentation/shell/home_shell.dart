import 'dart:ui' show ImageFilter;

import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../app/theme.dart';
import '../../l10n/generated/app_localizations.dart';

/// الأقسام الخمسة في الشريط السفليّ، **بترتيب ظهورها**.
///
/// تعدادٌ لا قائمةُ عناصرٍ مكتوبة في `build`: الترتيب هنا هو ترتيب الفروع في
/// `StatefulShellRoute`، والاثنان يُقرأان بالفهرس. قائمتان تفترقان عند أول
/// إضافةٍ في إحداهما، فيفتح تبويبُ «المفضلة» شاشةَ «محفظتي» — عطلٌ لا يكشفه
/// إلا مستخدم.
enum HomeSection {
  /// السيّارة: ما تحت القسم حرفياً — شبكةُ سيّارات معروضة.
  ///
  /// **ثالثُ اختيارٍ بعد اثنين رديئين:** المطرقة مائلةٌ بزاوية فتنشزّ بين
  /// أيقوناتٍ قائمة، والمعرضُ صندوقٌ صغيرٌ لا يُقرأ في اثنين وعشرين بكسلاً.
  /// والسيّارة عريضةٌ أفقياً فتملأ عرضها، وصورتُها الظليّة معروفةٌ بلا تأمّل.
  home(Icons.directions_car_outlined, Icons.directions_car_rounded),

  /// وصلٌ طويل: «مشاركاتي» فواتيرُ ومشترياتٌ ومزايدات، والوصل يجمعها.
  activity(Icons.receipt_long_outlined, Icons.receipt_long_rounded),

  favourites(Icons.favorite_border_rounded, Icons.favorite_rounded),

  /// محفظةٌ لا بطاقة: المال هنا رصيدٌ ودلاء، لا وسيلةَ دفعٍ واحدة.
  wallet(
    Icons.account_balance_wallet_outlined,
    Icons.account_balance_wallet_rounded,
  ),

  /// دائرةٌ حول الشخص: تُقرأ «حساب» لا «شخصٌ ما» — الفرق يهمّ في شريطٍ
  /// أيقوناتُه بحجم اثنين وعشرين بكسلاً.
  account(Icons.account_circle_outlined, Icons.account_circle_rounded);

  const HomeSection(this.icon, this.selectedIcon);

  /// أيقونتان لا واحدة: الفرق بين المختار وغيره **لا يُحمَّل على اللون وحده**.
  /// عينٌ لا تفرّق الذهبيَّ عن الأبيض الخافت تفرّق الممتلئ عن المفرَّغ.
  final IconData icon;
  final IconData selectedIcon;

  /// النصّ من ملفّ الترجمة، والاختيار هنا لا هناك: التعداد يعرف نفسه، وملفّ
  /// الترجمة لا يعرف الترتيب.
  String label(AppLocalizations l10n) => switch (this) {
    HomeSection.home => l10n.navHome,
    HomeSection.activity => l10n.navActivity,
    HomeSection.favourites => l10n.navFavourites,
    HomeSection.wallet => l10n.navWallet,
    HomeSection.account => l10n.navAccount,
  };
}

/// القشرة التي تحمل الأقسام الخمسة وشريطها السفليّ.
///
/// **لكل قسمٍ مكدّسه** (`StatefulShellRoute.indexedStack`): من فتح مركبةً من
/// المفضلة ثم ذهب إلى المحفظة وعاد، يجد المركبة كما تركها لا رأس القسم. وهذا
/// هو الفرق بين شريطٍ يتنقّل بين خمس شاشات وشريطٍ يتنقّل بين خمسة **أقسام**.
///
/// والشاشات تحتفظ بـ`Scaffold` و`AppBar` الخاصّين بها؛ القشرة تضيف الشريط
/// وحده. جمعُ العنوان هنا كان يعني عنواناً واحداً لكل شاشةٍ داخل القسم.
class HomeShell extends StatelessWidget {
  const HomeShell({required this.navigationShell, super.key});

  final StatefulNavigationShell navigationShell;

  @override
  Widget build(BuildContext context) => Scaffold(
    // **`extendBody`:** بدونه لا شيء يمرّ خلف الزجاج فلا يبدو زجاجاً — يبدو
    // لوحاً فاتحاً. والثمن أن آخر صفٍّ يقع تحته، فيُدفع في `_BarInset`:
    // ارتفاعُ الشريط يُضاف إلى `MediaQuery.padding` فتترك القوائم مكانه.
    extendBody: true,
    body: _BarInset(child: navigationShell),
    bottomNavigationBar: _GoldNavigationBar(shell: navigationShell),
  );
}

/// الشريط السفليّ — زجاجٌ أبيض، والأيقونةُ المختارة ذهبيّة والنصّ بنّيّ.
///
/// **مبنيٌّ لا `NavigationBar`:** المطلوب حوضٌ ذهبيّ خلف الأيقونة المختارة
/// وخيطٌ ذهبيّ فوق الشريط وطمسٌ خلفه وحركةٌ عند التبديل، وأربعتها تحتاج نقضَ
/// ثيم `NavigationBar` في أربعة مواضع — فيصير التخصيص أطول من البناء وأهشَّ.
class _GoldNavigationBar extends StatelessWidget {
  const _GoldNavigationBar({required this.shell});

  final StatefulNavigationShell shell;

  /// نصفُ قطر الزوايا — والشريط **عائم** لا ممتدٌّ من حافةٍ لحافة.
  ///
  /// **لماذا عائم:** لوحٌ يمسّ الحوافّ الثلاث يبدو جزءاً من إطار النظام لا
  /// جزءاً من التطبيق، ولا يُرى منه زجاجٌ أصلاً — الزجاج يحتاج حافّةً تُرى
  /// وظلّاً يفصله عمّا خلفه. والعائمُ يُظهر المحتوى من جانبيه وتحته، فيصير
  /// الطمسُ مرئيّاً بدل أن يكون تأثيراً لا أثرَ له.
  static const double radius = 26;

  @override
  Widget build(BuildContext context) {
    final palette = HarajPalette.of(context);

    return SafeArea(
      top: false,
      child: Padding(
        padding: const EdgeInsets.fromLTRB(14, 0, 14, 12),
        child: DecoratedBox(
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(radius),
            boxShadow: <BoxShadow>[
              // ظلٌّ واسعٌ خافت: يرفع الشريط عن الصفحة بلا حدٍّ أسودَ يقطعه.
              BoxShadow(
                color: Colors.black.withValues(alpha: 0.14),
                blurRadius: 24,
                spreadRadius: -4,
                offset: const Offset(0, 8),
              ),
            ],
          ),
          // ‏`ClipRRect` قبل `BackdropFilter`: بلا قصٍّ يمتدّ الطمس إلى الشاشة
          // كلها — الفلتر يعمل على ما خلفه لا على ما بداخله، وحدُّه هو حدُّ
          // المقصوص. وبنفس نصف القطر، وإلا طُمست زوايا خارج الشريط.
          child: ClipRRect(
            borderRadius: BorderRadius.circular(radius),
            child: BackdropFilter(
              filter: ImageFilter.blur(sigmaX: 30, sigmaY: 30),
              child: _bar(context, palette),
            ),
          ),
        ),
      ),
    );
  }

  Widget _bar(BuildContext context, HarajPalette palette) {
    return DecoratedBox(
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(radius),
        // تدرّجٌ لا لونٌ واحد: الزجاج الحقيقيّ يلتقط ضوءاً من أعلاه، ولونٌ
        // مسطّح يبدو ورقاً شفّافاً لا زجاجاً.
        gradient: LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: <Color>[palette.navSurface, palette.navSurfaceLow],
        ),
        // حدٌّ ذهبيٌّ رفيع: هو ما يجعل الحافّة تُرى على خلفيّةٍ فاتحة —
        // بدونه يذوب الشريط في الصفحة ويختفي معه كل أثر للزجاج.
        border: Border.all(
          color: palette.gold.withValues(alpha: 0.28),
          width: 1,
        ),
      ),
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 8, horizontal: 4),
        child: Row(
          children: <Widget>[
            for (final section in HomeSection.values)
              Expanded(
                child: _NavigationItem(
                  section: section,
                  selected: shell.currentIndex == section.index,
                  onTap: () => shell.goBranch(
                    section.index,
                    // ضغطُ القسم المفتوح يعود إلى رأسه — سلوكٌ يتوقّعه
                    // من اعتاد التطبيقات: «رجّعني لأول الصفحة» بضغطةٍ
                    // على ما هو مفتوح أصلاً.
                    initialLocation: shell.currentIndex == section.index,
                  ),
                ),
              ),
          ],
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
    // الهافر يُقرَّب اللون نحو الذهبيّ ولا يقفز إليه: قفزةٌ كاملة تجعل
    // العنصر المُحوَّم عليه يبدو مختاراً، فيضيع الفرق بين «هنا أنت»
    // و«هنا مؤشّرك».
    final iconColour = selected
        ? palette.gold
        : _hovered
        ? Color.lerp(palette.navInactive, palette.gold, 0.55)!
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
          borderRadius: BorderRadius.circular(18),
          // اللمسة والهافر ذهبيّان: تموّجٌ رماديّ على أرضيّةٍ زجاجيّة فاتحة
          // لا يكاد يظهر.
          splashColor: palette.goldMuted,
          highlightColor: palette.goldMuted,
          hoverColor: palette.gold.withValues(alpha: 0.07),
          child: Padding(
            padding: const EdgeInsets.symmetric(vertical: 7),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: <Widget>[
                // الأيقونة عاريةً، وهالةٌ ذهبيّة خلفها حين تُختار: ضوءٌ لا حدّ،
                // فيبقى الشكل واحداً في الحالتين ويتغيّر إضاءةً لا هيئة.
                AnimatedScale(
                  duration: _duration,
                  curve: Curves.easeOutCubic,
                  // رفعةٌ محسوسةٌ لا مرئيّة: ٤٪ تكفي ليشعر المؤشّر بأن العنصر
                  // حيّ، وأكثرُ منها يزيح جاره في صفٍّ ضيّق.
                  scale: _hovered && !selected ? 1.04 : 1,
                  child: AnimatedContainer(
                    duration: _duration,
                    curve: Curves.easeOutCubic,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      boxShadow: selected
                          ? <BoxShadow>[
                              BoxShadow(
                                color: palette.gold.withValues(alpha: 0.30),
                                blurRadius: 14,
                                spreadRadius: 1,
                              ),
                            ]
                          : const <BoxShadow>[],
                    ),
                    child: Icon(
                      selected ? section.selectedIcon : section.icon,
                      // حجمان لا حجمٌ واحد: المختار أكبر بقدرٍ يُلحَظ ولا يقفز.
                      size: selected ? 25 : 22,
                      color: iconColour,
                    ),
                  ),
                ),
                const SizedBox(height: 6),
                // `AnimatedDefaultTextStyle` لا `Text` بلونٍ متبدّل: اللون
                // والوزن يتحرّكان مع الحوض، فلا يسبق أحدهما الآخر.
                AnimatedDefaultTextStyle(
                  duration: _duration,
                  curve: Curves.easeOutCubic,
                  style: TextStyle(
                    // بنّيٌّ في الحالتين — لونان لنصٍّ واحدٍ يجعلان الشريط
                    // مبقّعاً. والفرقُ في الشدّة لا في اللون.
                    color: selected
                        ? palette.brown
                        : palette.brown.withValues(alpha: 0.62),
                    fontSize: 11,
                    // **عريضٌ في الحالتين.** الخطّ لا يحمل إلا ٤٠٠ و٥٠٠ و٧٠٠،
                    // فوزنٌ بينهما لا وجود له ويُقرَّب صامتاً. والتمييز محمولٌ
                    // على ثلاث إشاراتٍ أخرى: الحوض، والأيقونة الممتلئة،
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
                const SizedBox(height: 5),
                // **نقطةٌ تحت الاسم** لا خطٌّ فوق الأيقونة ولا حوضٌ حولها.
                //
                // الخطّ فوق الأيقونة يرث شكل التبويبات العلويّة فتقرأه العين
                // «تبويبٌ نزل من فوق»، والحوضُ يحبس الأيقونة في كبسولةٍ فتبدو
                // زرّاً داخل زرّ. والنقطةُ علامةٌ لا شكل: تقول «هذا هو» بأقلّ
                // حبرٍ ممكن، ولا تنازع الأيقونةَ ولا النصَّ على مساحتهما.
                AnimatedContainer(
                  duration: _duration,
                  curve: Curves.easeOutCubic,
                  width: selected ? 5 : 0,
                  height: 5,
                  decoration: BoxDecoration(
                    color: palette.gold,
                    shape: BoxShape.circle,
                    boxShadow: selected
                        ? <BoxShadow>[
                            BoxShadow(
                              color: palette.gold.withValues(alpha: 0.55),
                              blurRadius: 6,
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

/// يترك للشريط مكانه في أسفل كل قائمة.
///
/// **لماذا هنا لا في كل شاشة:** الشريط يعلو المحتوى (`extendBody`)، فأيُّ
/// قائمةٍ تنتهي عند حافّة الشاشة ينتهي آخر صفّها تحت الزجاج. وإصلاحُه بحشوةٍ
/// مكتوبة في كل شاشةٍ يعني شاشةً تُنسى — وهي التي سيراها المستخدم مقصوصة.
///
/// والقياس من `_barHeight` لا رقمٌ مكرَّر: ارتفاعٌ مكتوب مرّتين يفترق عند أول
/// تعديلٍ في الشريط، فتظهر فجوةٌ أو يبقى القصّ.
class _BarInset extends StatelessWidget {
  const _BarInset({required this.child});

  final Widget child;

  /// ارتفاع الشريط بهامشه: ١٢ هامشٌ سفليّ + حدّان + ٨ فوق + ٣٤ حوض + ٦ فراغ
  /// + ١٣ نصّ + ٨ تحت ≈ ٨٤. و`SafeArea` تضيف حاشية الجهاز فوقها، وتُقرأ من
  /// `MediaQuery` لا تُخمَّن.
  static const double _barHeight = 80;

  @override
  Widget build(BuildContext context) {
    final media = MediaQuery.of(context);
    return MediaQuery(
      data: media.copyWith(
        padding: media.padding.copyWith(
          bottom: media.padding.bottom + _barHeight,
        ),
      ),
      child: child,
    );
  }
}
