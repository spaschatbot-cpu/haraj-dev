import 'package:flutter/material.dart';

import '../../app/theme.dart';

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

  /// ارتفاع الهيدر: القياسيّ، ويزيد بالسطر الثاني وبما تحته.
  static const double _base = kToolbarHeight;
  static const double _subtitleHeight = 18;

  @override
  Size get preferredSize => Size.fromHeight(
    _base +
        (subtitle == null ? 0 : _subtitleHeight) +
        (bottom?.preferredSize.height ?? 0),
  );

  @override
  Widget build(BuildContext context) {
    final palette = HarajPalette.of(context);
    final theme = Theme.of(context);

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
            colors: <Color>[palette.headerTop, palette.headerBottom],
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
            title,
            style: theme.textTheme.titleLarge?.copyWith(
              color: Colors.white,
              fontWeight: FontWeight.w700,
              // تباعدٌ سالبٌ خفيف: العربية بوزن ٧٠٠ تتراصّ، وحرفٌ يلمس حرفاً
              // يُقرأ ككلمةٍ واحدة.
              letterSpacing: 0.2,
            ),
          ),
          if (subtitle case final String line)
            Text(
              line,
              style: theme.textTheme.bodySmall?.copyWith(
                // ذهبيٌّ فاتح على الخضرة العميقة: نسبته تكفي نصّاً صغيراً،
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
