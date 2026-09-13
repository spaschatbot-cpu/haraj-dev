import 'package:flutter/material.dart';

import '../../app/theme.dart';

/// خطوةٌ في دليلٍ مصوّر — عنوانٌ وشرح.
class GuideStep {
  const GuideStep(this.title, this.body);
  final String title;
  final String body;
}

/// عرضُ دليلٍ مشترك (شرح التسجيل، شرح شحن المحفظة…): بطاقةُ عنوان، خطواتٌ
/// مرقّمةٌ على خطٍّ ذهبيٍّ يمينَ الصفحة، فيديو، ثم صندوقُ تنبيه.
///
/// **مكوّنٌ واحدٌ لكل الأدلّة** (المادة ٤-٥): الأرقامُ والخطّ والبطاقات في مكانٍ
/// واحد، فلا يفترق دليلٌ عن دليل عند أول تعديل.
class GuideView extends StatelessWidget {
  const GuideView({
    required this.headerTitle,
    required this.headerSubtitle,
    required this.headerIcon,
    required this.steps,
    required this.videoSoonText,
    required this.hintText,
    super.key,
  });

  final String headerTitle;
  final String headerSubtitle;
  final IconData headerIcon;
  final List<GuideStep> steps;
  final String videoSoonText;
  final String hintText;

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: EdgeInsets.fromLTRB(
        16,
        16,
        16,
        16 + MediaQuery.paddingOf(context).bottom,
      ),
      children: <Widget>[
        _GuideHeader(
          title: headerTitle,
          subtitle: headerSubtitle,
          icon: headerIcon,
        ),
        const SizedBox(height: 20),
        for (var i = 0; i < steps.length; i++)
          _StepRow(
            number: i + 1,
            title: steps[i].title,
            body: steps[i].body,
            isLast: i == steps.length - 1,
          ),
        const SizedBox(height: 12),
        _VideoCard(soonText: videoSoonText),
        const SizedBox(height: 16),
        _HintBox(text: hintText),
      ],
    );
  }
}

class _GuideHeader extends StatelessWidget {
  const _GuideHeader({
    required this.title,
    required this.subtitle,
    required this.icon,
  });

  final String title;
  final String subtitle;
  final IconData icon;

  @override
  Widget build(BuildContext context) {
    final palette = HarajPalette.of(context);
    return Container(
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: palette.heroGlow.withValues(alpha: 0.10),
        borderRadius: BorderRadius.circular(18),
      ),
      child: Row(
        children: <Widget>[
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text(
                  title,
                  style: TextStyle(
                    color: palette.ink,
                    fontSize: 18,
                    fontWeight: FontWeight.w700,
                    height: 1.4,
                    fontFamily: HarajTheme.fontFamily,
                  ),
                ),
                const SizedBox(height: 6),
                Text(
                  subtitle,
                  style: TextStyle(
                    color: palette.inkMuted,
                    fontSize: 13,
                    fontFamily: HarajTheme.fontFamily,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(width: 14),
          Container(
            width: 56,
            height: 56,
            alignment: Alignment.center,
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(16),
              color: palette.cardSurface,
            ),
            child: Icon(icon, size: 30, color: palette.gold),
          ),
        ],
      ),
    );
  }
}

/// خطوةٌ على الخطّ الذهبيّ — الشارةُ المرقّمةُ يمينَ الصفحة، والنصُّ يساراً.
class _StepRow extends StatelessWidget {
  const _StepRow({
    required this.number,
    required this.title,
    required this.body,
    required this.isLast,
  });

  final int number;
  final String title;
  final String body;
  final bool isLast;

  @override
  Widget build(BuildContext context) {
    final palette = HarajPalette.of(context);
    return IntrinsicHeight(
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Column(
            children: <Widget>[
              Container(
                width: 42,
                height: 42,
                alignment: Alignment.center,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  gradient: LinearGradient(
                    begin: Alignment.topRight,
                    end: Alignment.bottomLeft,
                    colors: <Color>[palette.gold, palette.goldDeep],
                  ),
                  border: Border.all(color: palette.cardSurface, width: 3),
                  boxShadow: <BoxShadow>[
                    BoxShadow(
                      color: palette.gold.withValues(alpha: 0.40),
                      blurRadius: 10,
                      offset: const Offset(0, 2),
                    ),
                  ],
                ),
                child: Text(
                  '$number',
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 16,
                    fontWeight: FontWeight.w800,
                    fontFamily: HarajTheme.fontFamily,
                  ),
                ),
              ),
              if (!isLast)
                Expanded(
                  child: Container(
                    width: 3,
                    margin: const EdgeInsets.symmetric(vertical: 2),
                    decoration: BoxDecoration(
                      borderRadius: BorderRadius.circular(2),
                      gradient: LinearGradient(
                        begin: Alignment.topCenter,
                        end: Alignment.bottomCenter,
                        colors: <Color>[
                          palette.gold.withValues(alpha: 0.55),
                          palette.gold.withValues(alpha: 0.15),
                        ],
                      ),
                    ),
                  ),
                ),
            ],
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Padding(
              padding: const EdgeInsets.only(bottom: 16),
              child: Container(
                padding: const EdgeInsets.all(14),
                decoration: BoxDecoration(
                  color: palette.cardSurface,
                  borderRadius: BorderRadius.circular(14),
                  boxShadow: <BoxShadow>[
                    BoxShadow(
                      color: palette.ink.withValues(alpha: 0.05),
                      blurRadius: 10,
                      offset: const Offset(0, 3),
                    ),
                  ],
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Text(
                      title,
                      style: TextStyle(
                        color: palette.ink,
                        fontSize: 15.5,
                        fontWeight: FontWeight.w700,
                        fontFamily: HarajTheme.fontFamily,
                      ),
                    ),
                    const SizedBox(height: 6),
                    Text(
                      body,
                      style: TextStyle(
                        color: palette.inkMuted,
                        fontSize: 13.5,
                        height: 1.6,
                        fontFamily: HarajTheme.fontFamily,
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _VideoCard extends StatelessWidget {
  const _VideoCard({required this.soonText});

  final String soonText;

  @override
  Widget build(BuildContext context) {
    final palette = HarajPalette.of(context);
    return Container(
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(
        color: palette.cardSurface,
        borderRadius: BorderRadius.circular(18),
        boxShadow: <BoxShadow>[
          BoxShadow(
            color: palette.ink.withValues(alpha: 0.06),
            blurRadius: 12,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          borderRadius: BorderRadius.circular(12),
          onTap: () => ScaffoldMessenger.of(context)
            ..hideCurrentSnackBar()
            ..showSnackBar(SnackBar(content: Text(soonText))),
          child: AspectRatio(
            aspectRatio: 16 / 9,
            child: DecoratedBox(
              decoration: BoxDecoration(
                color: Colors.black,
                borderRadius: BorderRadius.circular(12),
              ),
              child: Center(
                child: Container(
                  width: 64,
                  height: 44,
                  alignment: Alignment.center,
                  decoration: BoxDecoration(
                    color: const Color(0xFFFF0000),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: const Icon(
                    Icons.play_arrow_rounded,
                    color: Colors.white,
                    size: 34,
                  ),
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _HintBox extends StatelessWidget {
  const _HintBox({required this.text});

  final String text;

  @override
  Widget build(BuildContext context) {
    final palette = HarajPalette.of(context);
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: palette.heroGlow.withValues(alpha: 0.10),
        borderRadius: BorderRadius.circular(14),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Icon(Icons.info_outline_rounded, size: 20, color: palette.goldDeep),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              text,
              style: TextStyle(
                color: palette.ink,
                fontSize: 13,
                height: 1.6,
                fontFamily: HarajTheme.fontFamily,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
