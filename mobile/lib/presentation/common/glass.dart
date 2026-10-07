import 'dart:ui' show ImageFilter;

import 'package:flutter/material.dart';

import '../../app/theme.dart';

/// **الأبيضُ الزجاجيّ** — هويّةُ التطبيق كلِّه بطلب المالك (٣ أكتوبر ٢٠٢٦):
/// «أبيض زجاجي، مش الأبيض تماماً… شكله أحسن وأحدث».
///
/// الزجاجُ لا يُرى على أرضيّةٍ مصمتة: الأبيضُ الشفّافُ فوق رماديٍّ مستوٍ يُقرأ
/// رماديّاً فاتحاً لا زجاجاً. فوراءَ كلّ شاشةٍ هذه الأرضيّة — تدرّجٌ أزرقُ أبيض
/// وهالتان ناعمتان — والبطاقاتُ فوقها `cardSurface` الشفّاف، فيعبرها لونُ ما
/// تحتها كما يعبر الزجاجُ المصنفر.
///
/// ومكانُها `MaterialApp.builder` لا كلُّ شاشة: أرضيّةٌ واحدة تحت التنقّل كلِّه،
/// فلا وميضَ لونٍ بين شاشتين، والشاشاتُ `Scaffold` شفّافةٌ فوقها.
class GlassBackdrop extends StatelessWidget {
  const GlassBackdrop({required this.child, super.key});

  final Widget child;

  @override
  Widget build(BuildContext context) {
    final palette = HarajPalette.of(context);
    return DecoratedBox(
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topRight,
          end: Alignment.bottomLeft,
          colors: <Color>[
            Color.alphaBlend(
              palette.gold.withValues(alpha: 0.10),
              palette.pageBackground,
            ),
            palette.pageBackground,
            Color.alphaBlend(
              const Color(0xFF35577F).withValues(alpha: 0.06),
              palette.pageBackground,
            ),
          ],
          stops: const <double>[0, 0.55, 1],
        ),
      ),
      child: Stack(
        children: <Widget>[
          // هالتان ثابتتان — زخرفةٌ لا تلتقط لمسة (`IgnorePointer`) ولا تُعاد
          // رسمتُها مع كلّ إطار (`RepaintBoundary`).
          Positioned(
            top: -120,
            right: -100,
            child: _Halo(
              color: palette.gold.withValues(alpha: 0.16),
              size: 360,
            ),
          ),
          Positioned(
            bottom: -140,
            left: -120,
            child: _Halo(
              color: const Color(0xFF8FD1BD).withValues(alpha: 0.14),
              size: 380,
            ),
          ),
          Positioned.fill(child: child),
        ],
      ),
    );
  }
}

class _Halo extends StatelessWidget {
  const _Halo({required this.color, required this.size});

  final Color color;
  final double size;

  @override
  Widget build(BuildContext context) => IgnorePointer(
    child: RepaintBoundary(
      child: Container(
        width: size,
        height: size,
        decoration: BoxDecoration(
          shape: BoxShape.circle,
          gradient: RadialGradient(
            colors: <Color>[color, color.withValues(alpha: 0)],
          ),
        ),
      ),
    ),
  );
}

/// لوحٌ زجاجيٌّ مصنفر حقيقيّ — `BackdropFilter` يطمس ما يمرّ تحته.
///
/// **للشرائط الثابتة وحدها** (الشريط السفليّ، والبحثُ المثبَّت، ورأسُ الشاشة):
/// الطمسُ يُحسب كلَّ إطار، وعلى عشرين كرتاً في قائمةٍ تُمرَّر يُثقل الهاتف.
/// والكروتُ زجاجُها شفافيّةُ `cardSurface` بلا طمس.
class GlassPanel extends StatelessWidget {
  const GlassPanel({
    required this.child,
    this.borderRadius = BorderRadius.zero,
    this.blur = 18,
    this.tint = 0.62,
    this.border,
    super.key,
  });

  final Widget child;
  final BorderRadius borderRadius;
  final double blur;

  /// كم من البياض فوق الطمس — أقلُّ يُظهر ما تحته أكثر.
  final double tint;
  final Border? border;

  @override
  Widget build(BuildContext context) {
    return ClipRRect(
      borderRadius: borderRadius,
      child: BackdropFilter(
        filter: ImageFilter.blur(sigmaX: blur, sigmaY: blur),
        child: DecoratedBox(
          decoration: BoxDecoration(
            color: Colors.white.withValues(alpha: tint),
            borderRadius: borderRadius,
            border: border,
          ),
          child: child,
        ),
      ),
    );
  }
}
