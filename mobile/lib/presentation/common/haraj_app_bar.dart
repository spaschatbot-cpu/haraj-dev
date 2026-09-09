import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../app/router.dart';
import '../../app/theme.dart';
import '../../l10n/generated/app_localizations.dart';

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
                    color: palette.ink,
                    tooltip: MaterialLocalizations.of(
                      context,
                    ).backButtonTooltip,
                  )
                else
                  const SizedBox(width: 16),
                // **خيطٌ ذهبيٌّ قائم قبل الاسم**: الشريطُ فاتحٌ على ورقةٍ
                // فاتحة، فبلا علامةٍ في أوّله يُقرأ سطرَ نصٍّ سائباً لا
                // عنوانَ شاشة. وقائمٌ لا أفقيّ: الأفقيُّ يفصل، والقائمُ
                // يُعنون.
                Container(
                  width: 3,
                  height: 18,
                  decoration: BoxDecoration(
                    gradient: LinearGradient(
                      begin: Alignment.topCenter,
                      end: Alignment.bottomCenter,
                      colors: <Color>[palette.gold, palette.goldDeep],
                    ),
                    borderRadius: BorderRadius.circular(2),
                  ),
                ),
                const SizedBox(width: 9),
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
                          color: palette.ink,
                          fontWeight: FontWeight.w700,
                          // تباعدٌ خفيف: العربية بوزن ٧٠٠ تتراصّ، وحرفٌ يلمس
                          // حرفاً يُقرأ ككلمةٍ واحدة.
                          letterSpacing: 0.2,
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
                // **بيتٌ في الطرف الآخر حين لا يوجد ما يُرجَع إليه** — بطلب
                // المالك في ٩ سبتمبر ٢٠٢٦.
                //
                // أقسامُ الشريط السفليّ جذورُ مكدّساتها، فلا `pop` فيها ولا
                // زرَّ رجوع. والشريطُ السفليّ يعرف الطريق إلى الرئيسية،
                // لكنّ من دخل من إشعارٍ أو رابطٍ يفتح قسماً بعينه لا يعرف
                // أنّ تحته شريطاً — وهذه أيقونةٌ تقول ذلك في مكان النظر.
                //
                // **حوضٌ ذهبيٌّ خفيف لا أيقونةٌ عارية**: أيقونةٌ وحدها على
                // ورقةٍ فاتحة تُقرأ زخرفةً لا زرّاً، والحوضُ يقول «هذا
                // يُضغط». وهو نظيرُ حوضِ الجرس والحساب في الهيدر فوقه.
                if (!canPop)
                  Semantics(
                    button: true,
                    label: AppLocalizations.of(context).navHome,
                    child: Material(
                      color: palette.gold.withValues(alpha: 0.14),
                      borderRadius: BorderRadius.circular(10),
                      child: InkWell(
                        onTap: () => GoRouter.of(context).go(Routes.homePath),
                        borderRadius: BorderRadius.circular(10),
                        child: Padding(
                          padding: const EdgeInsets.all(7),
                          child: Icon(
                            Icons.home_rounded,
                            size: 17,
                            color: palette.goldDeep,
                          ),
                        ),
                      ),
                    ),
                  ),
                const SizedBox(width: 16),
              ],
            ),
          ),
          if (bottom case final PreferredSizeWidget widget) widget,
        ],
      ),
    );
  }
}
