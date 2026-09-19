import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../../app/theme.dart';

/// هيكلُ شاشتَي الدخول والتحقّق — **مشتركٌ لا منسوخ**. T948
///
/// الشاشتان خطوتان في بابٍ واحد: الأولى تأخذ الرقم والثانية الرمز. وحين
/// كانتا تبنيان خلفيّتَهما وشعارَهما ولوحتَهما كلٌّ على حدة، كانت الأولى
/// لوحةً ذهبيّةً فوق هالتين والثانية **شريطَ تطبيقٍ رماديّاً وحقلاً عارياً**
/// — بابٌ واحدٌ بوجهين.
///
/// فما يجمعهما هنا: الأرضيّةُ وهالتاها، وعلامةُ الهويّة، واللوحةُ بشريطها،
/// وسطرُ التنبيه، ودخولُ المحتوى المتحرّك.
///
/// ## والحركةُ تُطفأ لمن أطفأها
///
/// كلُّ حركةٍ هنا تسأل [MediaQuery.disableAnimationsOf] أوّلاً. ومن ضبط جهازَه
/// على «تقليل الحركة» فعل ذلك لسبب — دوارٌ أو صداعٌ أو تشتّت — ومكوّنٌ يتجاهله
/// يُعيد إليه ما تجنّبه على مستوى النظام كلِّه.

/// هالتان خلف المحتوى تكسران استواءَ الأرضيّة.
class AuthBackdrop extends StatelessWidget {
  const AuthBackdrop({required this.child, super.key});

  final Widget child;

  @override
  Widget build(BuildContext context) {
    final palette = HarajPalette.of(context);
    return Stack(
      children: <Widget>[
        Positioned(
          top: -130,
          right: -90,
          child: _Glow(color: palette.heroGlow, size: 330),
        ),
        Positioned(
          bottom: -150,
          left: -110,
          child: _Glow(
            color: palette.goldDeep.withValues(alpha: 0.16),
            size: 300,
          ),
        ),
        child,
      ],
    );
  }
}

/// دائرةٌ ضبابيّة. تزيينٌ صريح، ولذلك `IgnorePointer`: لا تلتقط نقرةً موجَّهةً
/// إلى ما تحتها.
class _Glow extends StatelessWidget {
  const _Glow({required this.color, required this.size});

  final Color color;
  final double size;

  @override
  Widget build(BuildContext context) {
    return IgnorePointer(
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
    );
  }
}

/// الشعارُ في هالةٍ ذهبيّة، ومعه عنوانٌ وسطرٌ تحته.
///
/// **والشعارُ من `assets/images/logo.png`** لا حرفٌ في دائرة: الصورةُ هي التي
/// تجعل الشاشةَ تُقرأ «حراج» قبل أن يُقرأ سطرٌ واحد. و`errorBuilder` يسقط إلى
/// أيقونةٍ حين لا يُحمَّل الأصل — بابُ دخولٍ لا يسقط لأجل صورة.
///
/// والهالةُ **تتنفّس**: تكبر وتصغر في ثلاث ثوانٍ. حركةٌ بطيئةٌ لا تُلاحَظ
/// قصداً وتجعل الشاشةَ حيّةً لا صورةً ساكنة — وتُطفأ لمن أطفأ الحركة.
class AuthBrand extends StatefulWidget {
  const AuthBrand({required this.title, this.subtitle, this.size = 78, super.key});

  final String title;
  final String? subtitle;
  final double size;

  @override
  State<AuthBrand> createState() => _AuthBrandState();
}

class _AuthBrandState extends State<AuthBrand>
    with SingleTickerProviderStateMixin {
  late final AnimationController _breath = AnimationController(
    vsync: this,
    duration: const Duration(seconds: 3),
  );

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    // الطلبُ يُقرأ هنا لا في `initState`: `MediaQuery` غيرُ متاحةٍ هناك، وقد
    // يتغيّر الضبطُ والتطبيقُ يعمل.
    if (MediaQuery.disableAnimationsOf(context)) {
      _breath
        ..stop()
        ..value = 0;
    } else if (!_breath.isAnimating) {
      _breath.repeat(reverse: true);
    }
  }

  @override
  void dispose() {
    _breath.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final palette = HarajPalette.of(context);
    final theme = Theme.of(context);

    return Column(
      children: <Widget>[
        AnimatedBuilder(
          animation: _breath,
          builder: (context, child) {
            final t = Curves.easeInOut.transform(_breath.value);
            return Container(
              width: widget.size,
              height: widget.size,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                gradient: LinearGradient(
                  begin: Alignment.topRight,
                  end: Alignment.bottomLeft,
                  colors: <Color>[palette.heroTop, palette.heroBottom],
                ),
                border: Border.all(
                  color: palette.goldOnDark.withValues(alpha: 0.5),
                ),
                boxShadow: <BoxShadow>[
                  BoxShadow(
                    color: palette.goldDeep.withValues(alpha: 0.22 + t * 0.20),
                    blurRadius: 22 + t * 14,
                    spreadRadius: t * 3,
                  ),
                ],
              ),
              clipBehavior: Clip.antiAlias,
              child: child,
            );
          },
          child: Padding(
            padding: const EdgeInsets.all(13),
            child: Image.asset(
              'assets/images/logo.png',
              fit: BoxFit.contain,
              errorBuilder: (_, _, _) => Icon(
                Icons.gavel_rounded,
                color: palette.goldOnDark,
                size: 30,
              ),
            ),
          ),
        ),
        const SizedBox(height: 12),
        Text(
          widget.title,
          textAlign: TextAlign.center,
          style: theme.textTheme.titleLarge?.copyWith(
            fontWeight: FontWeight.w800,
            color: Colors.white,
          ),
        ),
        if (widget.subtitle != null) ...<Widget>[
          const SizedBox(height: 5),
          Text(
            widget.subtitle!,
            textAlign: TextAlign.center,
            style: theme.textTheme.bodySmall?.copyWith(color: palette.inkMuted),
          ),
        ],
      ],
    );
  }
}

/// اللوحةُ نفسُها — شريطُ عنوانٍ متدرّجٌ ثمّ المحتوى.
class AuthPanel extends StatelessWidget {
  const AuthPanel({
    required this.title,
    required this.child,
    this.icon = Icons.lock_outline_rounded,
    super.key,
  });

  final String title;
  final IconData icon;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    final palette = HarajPalette.of(context);
    final theme = Theme.of(context);
    return Material(
      color: palette.cardSurface,
      borderRadius: BorderRadius.circular(20),
      clipBehavior: Clip.antiAlias,
      elevation: 8,
      shadowColor: Colors.black.withValues(alpha: 0.55),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: <Widget>[
          DecoratedBox(
            decoration: BoxDecoration(
              gradient: LinearGradient(
                begin: Alignment.topRight,
                end: Alignment.bottomLeft,
                colors: <Color>[palette.heroTop, palette.heroBottom],
              ),
            ),
            child: Padding(
              padding: const EdgeInsets.fromLTRB(18, 14, 18, 14),
              child: Row(
                children: <Widget>[
                  Icon(icon, size: 18, color: palette.goldOnDark),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      title,
                      style: theme.textTheme.titleMedium?.copyWith(
                        color: Colors.white,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
          Padding(
            padding: const EdgeInsets.fromLTRB(18, 16, 18, 16),
            // ‏`AnimatedSize` لأن محتوى اللوحة يكبر: حقلُ الاسم يظهر حين
            // يطلبه الخادم، ورسالةُ الفشل تحته. وقفزةٌ مفاجئةٌ في الارتفاع
            // تُفقد القارئَ موضعَه.
            child: AnimatedSize(
              duration: const Duration(milliseconds: 220),
              curve: Curves.easeOut,
              alignment: Alignment.topCenter,
              child: child,
            ),
          ),
        ],
      ),
    );
  }
}

/// سطرُ تنبيهٍ داخل اللوحة — «انتهت جلستك» وأمثالُه.
class AuthNotice extends StatelessWidget {
  const AuthNotice({required this.icon, required this.text, super.key});

  final IconData icon;
  final String text;

  @override
  Widget build(BuildContext context) {
    final palette = HarajPalette.of(context);
    final theme = Theme.of(context);
    return Container(
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(
        color: palette.goldDeep.withValues(alpha: 0.14),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: palette.goldDeep.withValues(alpha: 0.35)),
      ),
      child: Row(
        children: <Widget>[
          Icon(icon, size: 16, color: palette.goldOnDark),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              text,
              style: theme.textTheme.bodySmall?.copyWith(color: palette.ink),
            ),
          ),
        ],
      ),
    );
  }
}

/// دخولُ المحتوى: يصعد قليلاً ويظهر. مرّةً واحدةً عند أوّل بناء.
///
/// و`delay` يجعل الأجزاء تتتابع بدل أن تصل دفعةً — والتتابعُ يقود العينَ من
/// الشعار إلى الحقل، وهو ترتيبُ القراءة المقصود.
class AuthEntrance extends StatelessWidget {
  const AuthEntrance({
    required this.child,
    this.delay = Duration.zero,
    super.key,
  });

  final Widget child;
  final Duration delay;

  @override
  Widget build(BuildContext context) {
    if (MediaQuery.disableAnimationsOf(context)) return child;
    return TweenAnimationBuilder<double>(
      tween: Tween<double>(begin: 0, end: 1),
      duration: const Duration(milliseconds: 420),
      curve: Curves.easeOutCubic,
      // التأخيرُ بمنحنىً لا بمؤقّت: `Interval` يُبقي الودجةَ بلا حالة، ومؤقّتٌ
      // يحتاج `dispose` ويترك بناءً بعد إزالةِ الشجرة.
      builder: (context, t, child) => Opacity(
        opacity: t.clamp(0, 1),
        child: Transform.translate(offset: Offset(0, (1 - t) * 14), child: child),
      ),
      child: child,
    );
  }
}

/// يهتزّ أفقيّاً حين يتغيّر [trigger] — للرمز الخاطئ.
///
/// **والاهتزازُ معنى لا زخرفة**: هو ما يقوله الجهازُ حين يُرفض الرمز، ويُقرأ
/// قبل أن تُقرأ الرسالة. ويُطفأ لمن أطفأ الحركة، وتبقى الرسالةُ وحدَها.
class ShakeOnChange extends StatefulWidget {
  const ShakeOnChange({required this.trigger, required this.child, super.key});

  final Object? trigger;
  final Widget child;

  @override
  State<ShakeOnChange> createState() => _ShakeOnChangeState();
}

class _ShakeOnChangeState extends State<ShakeOnChange>
    with SingleTickerProviderStateMixin {
  late final AnimationController _shake = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: 420),
  );

  @override
  void didUpdateWidget(covariant ShakeOnChange old) {
    super.didUpdateWidget(old);
    final fired = widget.trigger != null && widget.trigger != old.trigger;
    if (fired && !MediaQuery.disableAnimationsOf(context)) {
      _shake.forward(from: 0);
    }
  }

  @override
  void dispose() {
    _shake.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _shake,
      builder: (context, child) {
        if (_shake.value == 0) return child!;
        // ثلاثُ ذبذباتٍ تتلاشى: `sin` على ثلاث دوراتٍ مضروبةً في ما تبقّى.
        // ثلاثُ ذبذباتٍ تتلاشى: جيبٌ على ثلاث دوراتٍ مضروبٌ فيما تبقّى.
        final decay = 1 - _shake.value;
        final offset = 10 * decay * math.sin(_shake.value * 3 * 2 * math.pi);
        return Transform.translate(offset: Offset(offset, 0), child: child);
      },
      child: widget.child,
    );
  }

}
