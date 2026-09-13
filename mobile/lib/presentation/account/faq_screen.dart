import 'package:flutter/material.dart';

import '../../app/theme.dart';
import '../../l10n/generated/app_localizations.dart';
import 'account_page_scaffold.dart';

/// عنصرُ سؤالٍ شائع — سؤالٌ وجوابٌ وأيقونةٌ ولونُ لهجة.
class _Faq {
  const _Faq(this.icon, this.accent, this.question, this.answer);
  final IconData icon;
  final Color accent;
  final String question;
  final String answer;
}

/// صفحة «الأسئلة الشائعة» — أكورديون: يُفتح سؤالٌ واحدٌ فيُظهر جوابَه، وتُطوى
/// البقيّة. النصوصُ عربيّةٌ في الملف (صفحةُ مساعدةٍ ثابتة، كـ«من نحن»).
///
/// **اقتباساتٌ عربيّةٌ «…» لا `&quot;`**: النصُّ يُعرض حرفيّاً، فرمزُ HTML يظهر
/// كما هو ويُقرأ عطلاً.
class FaqScreen extends StatefulWidget {
  const FaqScreen({super.key});

  @override
  State<FaqScreen> createState() => _FaqScreenState();
}

class _FaqScreenState extends State<FaqScreen> {
  static const _gold = Color(0xFFB8860B);
  static const _blue = Color(0xFF1C6FD6);
  static const _green = Color(0xFF2E7D5B);
  static const _orange = Color(0xFFE07A2F);

  static const List<_Faq> _faqs = <_Faq>[
    _Faq(
      Icons.person_add_alt_1_outlined,
      _gold,
      'كيف يمكنني التسجيل والمشاركة في المزادات؟',
      'سجّل بالنقر على «التسجيل» وأكمل بياناتك، ثم فعّل الحساب عبر البريد أو '
          'الجوال، وبعدها ابدأ المزايدة فورًا.',
    ),
    _Faq(
      Icons.payments_outlined,
      _blue,
      'هل يوجد رسوم للمشاركة في المزادات؟',
      'التسجيل والتصفّح مجانًا. قد تُطبَّق رسوم إدارية عند الفوز حسب السياسة.',
    ),
    _Faq(
      Icons.directions_car_outlined,
      _green,
      'كيف أستلم السيارة بعد الفوز؟',
      'يصل إشعار يوضّح تفاصيل الدفع والاستلام والموقع وخطوات التسليم.',
    ),
    _Faq(
      Icons.warning_amber_rounded,
      _orange,
      'ماذا لو لم أدفع بعد الفوز؟',
      'قد تُفرض غرامات أو يُلغى المزاد ويُعاد إدراجه. راجع سياسة الدفع قبل '
          'المزايدة.',
    ),
    _Faq(
      Icons.swap_horiz_rounded,
      _blue,
      'هل أسترد أموالي إن لم تعجبني السيارة؟',
      'تُعرض المواصفات والصور مسبقًا. لا استرداد بعد الفوز إلا عند عدم مطابقة '
          'المواصفات.',
    ),
  ];

  int? _open = 0;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final palette = HarajPalette.of(context);

    return AccountPageScaffold(
      title: l10n.accountMenuFaq,
      child: ListView(
        padding: EdgeInsets.fromLTRB(
          16,
          16,
          16,
          16 + MediaQuery.paddingOf(context).bottom,
        ),
        children: <Widget>[
          // حُذفت بطاقةُ الرأس «الأسئلة الشائعة حول المزادات» بطلب المالك
          // (١٣ سبتمبر ٢٠٢٦) — يكفي عنوانُ الشاشة في الشريط.
          Text(
            'الأسئلة الشائعة',
            style: TextStyle(
              color: palette.ink,
              fontSize: 18,
              fontWeight: FontWeight.w800,
              fontFamily: HarajTheme.fontFamily,
            ),
          ),
          const SizedBox(height: 12),
          for (var i = 0; i < _faqs.length; i++)
            _FaqTile(
              faq: _faqs[i],
              expanded: _open == i,
              onTap: () => setState(() => _open = _open == i ? null : i),
              palette: palette,
            ),
        ],
      ),
    );
  }
}

/// بطاقةُ سؤال — يُفتح فيُظهر الجواب بصندوقٍ ذي استروكٍ ملوّن.
class _FaqTile extends StatelessWidget {
  const _FaqTile({
    required this.faq,
    required this.expanded,
    required this.onTap,
    required this.palette,
  });

  final _Faq faq;
  final bool expanded;
  final VoidCallback onTap;
  final HarajPalette palette;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Container(
        decoration: BoxDecoration(
          color: palette.cardSurface,
          borderRadius: BorderRadius.circular(16),
          boxShadow: <BoxShadow>[
            BoxShadow(
              color: palette.ink.withValues(alpha: 0.05),
              blurRadius: 10,
              offset: const Offset(0, 3),
            ),
          ],
        ),
        child: Material(
          color: Colors.transparent,
          borderRadius: BorderRadius.circular(16),
          clipBehavior: Clip.antiAlias,
          child: Column(
            children: <Widget>[
              InkWell(
                onTap: onTap,
                hoverColor: Colors.transparent,
                splashColor: Colors.transparent,
                highlightColor: Colors.transparent,
                child: Padding(
                  padding: const EdgeInsets.all(14),
                  child: Row(
                    children: <Widget>[
                      // الأيقونةُ يمينًا (بداية RTL).
                      Container(
                        width: 40,
                        height: 40,
                        alignment: Alignment.center,
                        decoration: BoxDecoration(
                          shape: BoxShape.circle,
                          color: faq.accent.withValues(alpha: 0.12),
                        ),
                        child: Icon(faq.icon, color: faq.accent, size: 20),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: Text(
                          faq.question,
                          style: TextStyle(
                            color: palette.ink,
                            fontSize: 15,
                            fontWeight: FontWeight.w700,
                            height: 1.5,
                            fontFamily: HarajTheme.fontFamily,
                          ),
                        ),
                      ),
                      const SizedBox(width: 8),
                      AnimatedRotation(
                        turns: expanded ? 0.5 : 0,
                        duration: const Duration(milliseconds: 200),
                        child: Icon(
                          Icons.keyboard_arrow_down_rounded,
                          color: palette.inkMuted,
                          size: 24,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
              // الجواب — يظهر مع فتح البطاقة.
              AnimatedCrossFade(
                duration: const Duration(milliseconds: 200),
                crossFadeState: expanded
                    ? CrossFadeState.showFirst
                    : CrossFadeState.showSecond,
                firstChild: _Answer(
                  text: faq.answer,
                  accent: faq.accent,
                  palette: palette,
                ),
                secondChild: const SizedBox(width: double.infinity),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _Answer extends StatelessWidget {
  const _Answer({
    required this.text,
    required this.accent,
    required this.palette,
  });

  final String text;
  final Color accent;
  final HarajPalette palette;

  @override
  Widget build(BuildContext context) => IntrinsicHeight(
    child: Row(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: <Widget>[
        Expanded(
          child: Container(
            margin: const EdgeInsets.fromLTRB(0, 0, 14, 14),
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
              color: palette.pageBackground,
              borderRadius: BorderRadius.circular(12),
            ),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Expanded(
                  child: Text(
                    text,
                    style: TextStyle(
                      color: palette.inkMuted,
                      fontSize: 13.5,
                      height: 1.8,
                      fontFamily: HarajTheme.fontFamily,
                    ),
                  ),
                ),
                const SizedBox(width: 10),
                Icon(
                  Icons.chat_bubble_outline_rounded,
                  size: 18,
                  color: palette.inkMuted,
                ),
              ],
            ),
          ),
        ),
        // استروكٌ ملوّنٌ على الحافّة اليسرى للجواب.
        Container(
          width: 4,
          margin: const EdgeInsets.only(bottom: 14),
          decoration: BoxDecoration(
            color: accent,
            borderRadius: BorderRadius.circular(4),
          ),
        ),
      ],
    ),
  );
}
