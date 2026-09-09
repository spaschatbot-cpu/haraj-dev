import 'package:flutter/material.dart';

import '../../app/theme.dart';
import '../../l10n/generated/app_localizations.dart';

/// هيدر الشاشة — **واحدٌ لكل شاشات التطبيق**.
///
/// **لماذا مكوّنٌ لا `AppBar` في كل شاشة:** الهيدر يحمل هويّة العلامة (تدرّج
/// الخضرة، الخيط الذهبيّ، وزن العنوان). وكتابتُه في كل شاشة تعني أربع عشرة
/// نسخةً تفترق عند أول تعديل — وهو بالضبط ما حدث في v1 حتى صار لكل شاشة
/// رأسٌ بلونٍ مختلف (المادة ٤-٥).
///
/// وشكلُه هنا **لا في `ThemeData`**: الخيط الذهبيّ السفليّ والتدرّج لا
/// يُعبَّر عنهما في `AppBarTheme` بلا `flexibleSpace`، فيبقى نصفُ الشكل في
/// الثيم ونصفُه في كل شاشة — وذلك أسوأ من الاثنين.
///
/// **والعلامةُ في سطره الأول، لا اسمُ الشاشة** — بطلب المالك في ٩ سبتمبر
/// ٢٠٢٦: «الهيدر ثابتٌ في كل الصفحات». كانت الرئيسيةُ تحمل `HomeHero` بالعلامة
/// وبقيّةُ الشاشات تحمل هذا باسمها وحده، فيقرأ من ينتقل بينهما هيدرين لا
/// هيدراً واحداً.
///
/// **واسمُ الشاشة لم يسقط** — نزل سطراً: «محفظتي» تحت «مزاد حراج واحد». حذفُه
/// كان سيترك من فتح «شحن المحفظة» بلا ما يقول له أين هو، وزرُّ الرجوع وحده
/// لا يقولها.
class HarajAppBar extends StatelessWidget implements PreferredSizeWidget {
  const HarajAppBar({
    required this.title,
    this.subtitle,
    this.actions,
    this.bottom,
    super.key,
  });

  final String title;

  /// سطرٌ ثانٍ صغير تحت العنوان — عددُ النتائج، أو اسمُ المزاد المفتوح.
  ///
  /// اختياريٌّ لأنه ليس لكل شاشةٍ ما تقوله تحت اسمها، وسطرٌ فارغ يوسّع الهيدر
  /// بلا مقابل.
  final String? subtitle;

  final List<Widget>? actions;

  /// شريط تبويباتٍ أو ما يشبهه، يسكن أسفل الهيدر.
  final PreferredSizeWidget? bottom;

  /// ارتفاع الهيدر: القياسيّ، ومعه سطرُ اسمِ الشاشة وما تحته.
  ///
  /// **والسطرُ الثاني مدفوعُ الثمن دائماً** بعد أن صار اسمُ الشاشة فيه: هيدرٌ
  /// يتغيّر ارتفاعُه بين شاشةٍ وأخرى يُقفز المحتوى تحته عند كل انتقال.
  static const double _base = kToolbarHeight;
  static const double _subtitleHeight = 18;

  @override
  Size get preferredSize => Size.fromHeight(
    _base + _subtitleHeight + (bottom?.preferredSize.height ?? 0),
  );

  @override
  Widget build(BuildContext context) {
    final palette = HarajPalette.of(context);
    final theme = Theme.of(context);
    final l10n = AppLocalizations.of(context);

    return AppBar(
      // اللون في `flexibleSpace` لا هنا: الشفافيّة تترك التدرّج يُرى.
      backgroundColor: Colors.transparent,
      surfaceTintColor: Colors.transparent,
      elevation: 0,
      // الأيقونات والعنوان فوق أرضيّةٍ داكنة، فالمقدّمة فاتحة — ولا تُترك
      // للثيم: ثيمٌ فاتح يجعلها داكنةً على داكن فتختفي.
      foregroundColor: Colors.white,
      centerTitle: false,
      titleSpacing: 20,
      flexibleSpace: DecoratedBox(
        decoration: BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topRight,
            end: Alignment.bottomLeft,
            colors: <Color>[palette.heroTop, palette.heroBottom],
          ),
        ),
        // الخيط الذهبيّ في أسفل الهيدر — نظيرُ الذي في أعلى الشريط السفليّ،
        // فيُقفل التطبيق بين خطّين من لونٍ واحد.
        child: Align(
          alignment: Alignment.bottomCenter,
          child: Container(
            height: 2,
            decoration: BoxDecoration(
              gradient: LinearGradient(
                colors: <Color>[
                  palette.gold.withValues(alpha: 0),
                  palette.gold.withValues(alpha: 0.85),
                  palette.gold.withValues(alpha: 0),
                ],
              ),
            ),
          ),
        ),
      ),
      title: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisAlignment: MainAxisAlignment.center,
        mainAxisSize: MainAxisSize.min,
        children: <Widget>[
          Text(
            l10n.homeBrand,
            style: theme.textTheme.titleLarge?.copyWith(
              color: Colors.white,
              fontWeight: FontWeight.w700,
              // تباعدٌ سالبٌ خفيف: العربية بوزن ٧٠٠ تتراصّ، وحرفٌ يلمس حرفاً
              // يُقرأ ككلمةٍ واحدة.
              letterSpacing: 0.2,
            ),
          ),
          Text(
            // اسمُ الشاشة، ومعه سطرُها الثاني إن كان لها واحد: «محفظتي» أو
            // «سيارات المزاد · مزاد الرياض».
            subtitle == null ? title : '$title · $subtitle',
            style: theme.textTheme.bodySmall?.copyWith(
              // ذهبيٌّ فاتح على الأرضيّة الداكنة: نسبته تكفي نصّاً صغيراً،
              // ويربط السطر بالخيط الذهبيّ تحته.
              color: palette.goldOnDark,
              fontWeight: FontWeight.w500,
            ),
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
          ),
        ],
      ),
      actions: actions,
      bottom: bottom,
    );
  }
}
