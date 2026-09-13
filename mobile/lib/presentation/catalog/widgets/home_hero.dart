import 'package:flutter/material.dart';

import '../../../app/theme.dart';
import '../../../l10n/generated/app_localizations.dart';

/// هيدر التطبيق.
///
/// **نسختان**: الرئيسيةُ تحمل اللوحةَ الغنيّة — صورةُ سيّارةٍ ومدينةٍ خلفيّةً
/// كاملةً، والنصُّ في الجزء الفاضي منها — بطلب المالك في ١٣ سبتمبر ٢٠٢٦.
/// وبقيّةُ الأقسام تُبقي الشريطَ المدمج: العلامةُ وحدها أو اسمُ القسم.
class HomeHero extends StatelessWidget {
  const HomeHero({
    required this.onOpenNotifications,
    required this.onOpenAccount,
    this.showActions = true,
    this.title,
    super.key,
  });

  final VoidCallback onOpenNotifications;
  final VoidCallback onOpenAccount;

  /// اللوحةُ الغنيّة في الرئيسية وحدها — نفسُ شرط الأزرار.
  final bool showActions;

  /// عنوانُ اللوحة في الأقسام الأخرى (`null` = العلامة).
  final String? title;

  static const String _carAsset = 'assets/images/hero_car.png';
  static const double _radius = 24;

  @override
  Widget build(BuildContext context) {
    final palette = HarajPalette.of(context);
    return ClipRRect(
      borderRadius: const BorderRadius.vertical(
        bottom: Radius.circular(_radius),
      ),
      child: showActions
          ? _RichHero(
              palette: palette,
              carAsset: _carAsset,
              onOpenNotifications: onOpenNotifications,
              onOpenAccount: onOpenAccount,
            )
          : _CompactHero(palette: palette, title: title),
    );
  }
}

/// اللوحةُ الغنيّة للرئيسية — صورةُ السيّارة والمدينة خلفيّةً كاملة، والنصُّ في
/// جزئها الفاضي (يمينَ السماء)، بسِتارٍ يجعله مقروءاً.
class _RichHero extends StatelessWidget {
  const _RichHero({
    required this.palette,
    required this.carAsset,
    required this.onOpenNotifications,
    required this.onOpenAccount,
  });

  final HarajPalette palette;
  final String carAsset;
  final VoidCallback onOpenNotifications;
  final VoidCallback onOpenAccount;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final theme = Theme.of(context);

    return DecoratedBox(
      // خلفٌ كحليٌّ يظهر لو تعذّرت الصورة، وتحت حوافّها الشفّافة.
      decoration: BoxDecoration(color: palette.heroTop),
      child: Stack(
        children: <Widget>[
          // الصورةُ خلفيّةً كاملة.
          Positioned.fill(
            child: Image.asset(
              carAsset,
              fit: BoxFit.cover,
              alignment: Alignment.centerRight,
              // أصلٌ مفقودٌ لا يُسقط اللوحة: يبقى الكحليُّ خلفَه حتى تُضاف.
              errorBuilder: (_, _, _) => const SizedBox.shrink(),
            ),
          ),
          // سِتارٌ مزدوج: أفقيٌّ يُعتم اليمين (حيث النصّ)، ورأسيٌّ يُعتم الأعلى
          // (صفُّ العلامة) — فيُقرأ النصُّ الأبيضُ فوق السماء والغيوم.
          Positioned.fill(
            child: DecoratedBox(
              decoration: BoxDecoration(
                gradient: LinearGradient(
                  begin: Alignment.centerRight,
                  end: Alignment.centerLeft,
                  colors: <Color>[
                    palette.heroBottom.withValues(alpha: 0.88),
                    palette.heroBottom.withValues(alpha: 0.55),
                    palette.heroBottom.withValues(alpha: 0.05),
                  ],
                  stops: const <double>[0, 0.5, 0.95],
                ),
              ),
            ),
          ),
          Positioned.fill(
            child: DecoratedBox(
              decoration: BoxDecoration(
                gradient: LinearGradient(
                  begin: Alignment.topCenter,
                  end: Alignment.bottomCenter,
                  colors: <Color>[
                    palette.heroBottom.withValues(alpha: 0.55),
                    palette.heroBottom.withValues(alpha: 0),
                  ],
                  stops: const <double>[0, 0.4],
                ),
              ),
            ),
          ),
          SafeArea(
            bottom: false,
            child: Padding(
              padding: const EdgeInsets.fromLTRB(18, 12, 18, 18),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  // صفُّ العلامة والأزرار.
                  Row(
                    children: <Widget>[
                      Expanded(
                        child: _Brand(
                          palette: palette,
                          theme: theme,
                          l10n: l10n,
                        ),
                      ),
                      _CircleAction(
                        icon: Icons.notifications_none_rounded,
                        tooltip: l10n.homeNotifications,
                        onTap: onOpenNotifications,
                        palette: palette,
                        badge: true,
                      ),
                      const SizedBox(width: 10),
                      _CircleAction(
                        icon: Icons.person_outline_rounded,
                        tooltip: l10n.homeAccountAction,
                        onTap: onOpenAccount,
                        palette: palette,
                      ),
                    ],
                  ),
                  const SizedBox(height: 22),
                  // العنوانُ القياديّ — في الجزء الفاضي من الصورة.
                  Row(
                    children: <Widget>[
                      Container(
                        width: 22,
                        height: 3,
                        decoration: BoxDecoration(
                          borderRadius: BorderRadius.circular(2),
                          gradient: LinearGradient(
                            colors: <Color>[
                              palette.goldOnDark,
                              palette.heroGlow,
                            ],
                          ),
                        ),
                      ),
                      const SizedBox(width: 8),
                      Flexible(
                        child: Text(
                          l10n.heroHeadlineLead,
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: TextStyle(
                            color: Colors.white.withValues(alpha: 0.9),
                            fontSize: 11.5,
                            fontWeight: FontWeight.w600,
                            fontFamily: HarajTheme.fontFamily,
                            shadows: const <Shadow>[
                              Shadow(color: Colors.black54, blurRadius: 8),
                            ],
                          ),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 6),
                  RichText(
                    text: TextSpan(
                      style: TextStyle(
                        fontSize: 19,
                        fontWeight: FontWeight.w800,
                        height: 1.3,
                        fontFamily: HarajTheme.fontFamily,
                        shadows: const <Shadow>[
                          Shadow(color: Colors.black54, blurRadius: 12),
                        ],
                      ),
                      children: <InlineSpan>[
                        TextSpan(
                          text: '${l10n.heroHeadline} ',
                          style: const TextStyle(color: Colors.white),
                        ),
                        TextSpan(
                          text: l10n.heroHeadlineAccent,
                          style: TextStyle(color: palette.goldOnDark),
                        ),
                      ],
                    ),
                  ),
                  // شاراتُ «سيارات مميزة/مزادات موثوقة/فرص استثنائية» حُذفت
                  // بطلب المالك (١٣ سبتمبر ٢٠٢٦).
                ],
              ),
            ),
          ),
          _goldEdge(palette),
        ],
      ),
    );
  }
}

/// الشريطُ المدمج لبقيّة الأقسام — العلامةُ أو اسمُ القسم في الوسط.
class _CompactHero extends StatelessWidget {
  const _CompactHero({required this.palette, this.title});

  final HarajPalette palette;
  final String? title;

  static const double _minHeight = 58;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final theme = Theme.of(context);
    final topInset = MediaQuery.paddingOf(context).top;

    return ConstrainedBox(
      constraints: BoxConstraints(minHeight: _minHeight + topInset),
      child: Stack(
        alignment: Alignment.center,
        children: <Widget>[
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
          const Positioned.fill(child: _Dots()),
          SafeArea(
            bottom: false,
            child: Padding(
              padding: const EdgeInsets.fromLTRB(20, 7, 20, 7),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: <Widget>[
                  Flexible(
                    child: _Brand(
                      palette: palette,
                      theme: theme,
                      l10n: l10n,
                      title: title,
                    ),
                  ),
                ],
              ),
            ),
          ),
          _goldEdge(palette),
        ],
      ),
    );
  }
}

/// خيطٌ ذهبيّ على الحافّة السفلى.
Widget _goldEdge(HarajPalette palette) => Positioned(
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
);

/// شارةُ المطرقة واسمُ العلامة، وتحته سطرُ التعريف في اللوحة الغنيّة.
class _Brand extends StatelessWidget {
  const _Brand({
    required this.palette,
    required this.theme,
    required this.l10n,
    this.title,
  });

  final HarajPalette palette;
  final ThemeData theme;
  final AppLocalizations l10n;
  final String? title;

  @override
  Widget build(BuildContext context) => Row(
    mainAxisSize: MainAxisSize.min,
    children: <Widget>[
      Container(
        width: 34,
        height: 34,
        decoration: BoxDecoration(
          shape: BoxShape.circle,
          border: Border.all(
            color: palette.goldOnDark.withValues(alpha: 0.55),
            width: 1.4,
          ),
          color: palette.heroBottom.withValues(alpha: 0.45),
          boxShadow: <BoxShadow>[
            BoxShadow(
              color: palette.heroGlow.withValues(alpha: 0.28),
              blurRadius: 16,
              spreadRadius: 1,
            ),
          ],
        ),
        child: Icon(Icons.gavel_rounded, size: 18, color: palette.goldOnDark),
      ),
      const SizedBox(width: 10),
      Flexible(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Text(
              title ?? l10n.homeBrand,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: theme.textTheme.titleMedium?.copyWith(
                color: Colors.white,
                fontWeight: FontWeight.w700,
                letterSpacing: 0.5,
                shadows: const <Shadow>[
                  Shadow(color: Colors.black87, blurRadius: 12),
                ],
              ),
            ),
            // سطرُ «سيارات • مزادات • فرص» حُذف بطلب المالك (١٣ سبتمبر ٢٠٢٦).
          ],
        ),
      ),
    ],
  );
}

/// نقاطٌ ذهبيّة في خلفيّة الشريط المدمج.
class _Dots extends StatelessWidget {
  const _Dots();

  @override
  Widget build(BuildContext context) {
    final palette = HarajPalette.of(context);
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

  static const List<({double x, double y, double r, double alpha})> _dots =
      <({double x, double y, double r, double alpha})>[
        (x: 0.09, y: 0.30, r: 1.6, alpha: 0.30),
        (x: 0.15, y: 0.72, r: 1.0, alpha: 0.18),
        (x: 0.24, y: 0.22, r: 2.2, alpha: 0.22),
        (x: 0.31, y: 0.60, r: 1.2, alpha: 0.34),
        (x: 0.39, y: 0.36, r: 1.0, alpha: 0.16),
        (x: 0.46, y: 0.78, r: 1.8, alpha: 0.26),
        (x: 0.53, y: 0.26, r: 1.1, alpha: 0.20),
      ];

  @override
  void paint(Canvas canvas, Size size) {
    for (final dot in _dots) {
      final centre = Offset(size.width * dot.x, size.height * dot.y);
      canvas
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

/// زرٌّ دائريّ زجاجيّ في أعلى اللوحة، بنقطةِ تنبيهٍ اختياريّة.
class _CircleAction extends StatelessWidget {
  const _CircleAction({
    required this.icon,
    required this.tooltip,
    required this.onTap,
    required this.palette,
    this.badge = false,
  });

  final IconData icon;
  final String tooltip;
  final VoidCallback onTap;
  final HarajPalette palette;
  final bool badge;

  @override
  Widget build(BuildContext context) => Tooltip(
    message: tooltip,
    child: Semantics(
      button: true,
      label: tooltip,
      child: Stack(
        clipBehavior: Clip.none,
        children: <Widget>[
          Material(
            color: palette.heroBottom.withValues(alpha: 0.45),
            shape: CircleBorder(
              side: BorderSide(
                color: palette.goldOnDark.withValues(alpha: 0.30),
              ),
            ),
            child: InkWell(
              onTap: onTap,
              customBorder: const CircleBorder(),
              child: Padding(
                padding: const EdgeInsets.all(8),
                child: Icon(icon, size: 18, color: Colors.white),
              ),
            ),
          ),
          if (badge)
            Positioned(
              top: -1,
              right: -1,
              child: Container(
                width: 10,
                height: 10,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: const Color(0xFFE53935),
                  border: Border.all(color: palette.heroTop, width: 1.5),
                ),
              ),
            ),
        ],
      ),
    ),
  );
}
