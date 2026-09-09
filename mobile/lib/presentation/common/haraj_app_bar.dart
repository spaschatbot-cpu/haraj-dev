import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../app/theme.dart';

/// شريطُ عنوان الشاشة — **تحت الهيدر لا بدلاً منه**.
///
/// كان هو الهيدر: تدرّجٌ داكن يحمل اسمَ الشاشة، بينما تحمل الرئيسيةُ `HomeHero`
/// بالعلامة والجرس والحساب. ونُقل الهيدرُ إلى القشرة في ٩ سبتمبر ٢٠٢٦ ليظهر
/// في كل الصفحات، فبقي لهذا ما لا يعرفه الهيدر: **أين أنت الآن**.
///
/// **شريطٌ فاتحٌ لا داكن**: داكنان متتاليان يُقرآن هيدراً واحداً ارتفاعُه
/// تسعون بكسلاً، ويبتلعان ثلثَ الشاشة القصيرة. وهذا شريطٌ على ورقة الصفحة،
/// يفصله عن الهيدر خطٌّ ذهبيٌّ رفيع.
///
/// **وزرُّ الرجوع فيه** حين يكون في المكدّس ما يُرجَع إليه: الهيدرُ في القشرة
/// لا يعرف مكدّسَ القسم، وشاشةُ «شحن المحفظة» بلا رجوعٍ تحبس من فتحها.
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

  /// ارتفاعُ صفّ العنوان — **٤٦ لا `kToolbarHeight` (٥٦)**: هذا شريطُ عنوانٍ
  /// تحت هيدرٍ قائم، لا هيدرٌ بنفسه، وعشرةُ بكسلاتٍ فوقه فراغٌ مكرَّر.
  static const double _base = 46;

  /// الخيطُ الذهبيّ الفاصل عن الهيدر.
  static const double _rule = 2;

  @override
  Size get preferredSize =>
      Size.fromHeight(_base + _rule + (bottom?.preferredSize.height ?? 0));

  @override
  Widget build(BuildContext context) {
    final palette = HarajPalette.of(context);
    final theme = Theme.of(context);
    final canPop = GoRouter.of(context).canPop();

    return Material(
      color: palette.pageBackground,
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: <Widget>[
          // الخيط الذهبيّ يفصل الشريط عن الهيدر فوقه — نظيرُ الذي في أعلى
          // الشريط السفليّ، فيُقفل التطبيق بين خطّين من لونٍ واحد.
          Container(
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
          SizedBox(
            height: _base,
            child: Row(
              children: <Widget>[
                if (canPop)
                  IconButton(
                    onPressed: () => GoRouter.of(context).pop(),
                    icon: const Icon(Icons.arrow_forward_rounded, size: 20),
                    color: palette.brown,
                    tooltip: MaterialLocalizations.of(
                      context,
                    ).backButtonTooltip,
                  )
                else
                  const SizedBox(width: 20),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    mainAxisAlignment: MainAxisAlignment.center,
                    mainAxisSize: MainAxisSize.min,
                    children: <Widget>[
                      Text(
                        title,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: theme.textTheme.titleMedium?.copyWith(
                          color: palette.brown,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                      if (subtitle case final String line)
                        Text(
                          line,
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: theme.textTheme.bodySmall?.copyWith(
                            color: palette.inkMuted,
                            fontWeight: FontWeight.w500,
                          ),
                        ),
                    ],
                  ),
                ),
                if (actions case final List<Widget> widgets) ...widgets,
                const SizedBox(width: 8),
              ],
            ),
          ),
          if (bottom case final PreferredSizeWidget widget) widget,
        ],
      ),
    );
  }
}
