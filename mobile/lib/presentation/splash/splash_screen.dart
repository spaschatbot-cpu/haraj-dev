import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../app/providers.dart';
import '../../app/routes.dart';
import '../../app/theme.dart';
import '../../core/environment.dart';
import '../../l10n/generated/app_localizations.dart';
import '../auth/session_controller.dart';
import 'onboarding_parts.dart';

/// شاشة البدء — الشعارُ، وما يجري فعلاً قبل أن تُفتح الصالة.
///
/// **والشريطُ يقيس عملاً، لا يعدّ ثوانيَ.** شاشةُ بدءٍ نسبتُها مؤقّتٌ تكذب
/// مرّتين: تقول ٦٠٪ وقد انتهى كلُّ شيء، وتقول ١٠٠٪ والشبكةُ لم تردّ. وهنا
/// ثلاثُ خطواتٍ لكلٍّ منها جوابٌ يُنتظر:
///
/// 1. **تهيئة الواجهة** — تنتهي بأوّل إطارٍ مرسوم.
/// 2. **التحقّق من الجلسة** — `SessionState.unknown` تعني «لم يُقرأ التخزين
///    الآمن بعد»، وهي اللحظةُ التي يمتنع فيها `redirect` عن كلّ قرار: «قرارٌ
///    هنا يعني وميض شاشة دخول أمام مستخدم مسجَّل أصلاً». فهذه الشاشة تملأ
///    تلك اللحظة نفسَها ولا تخترع انتظاراً بجانبها.
/// 3. **مزامنة لوحة المزايدات** — `LoadHomeAuctions` مرّةً واحدة. وليست
///    زينةً في الشريط: الرئيسيةُ تطلبها بعد لحظات، وطلبُها هنا يجعلها تفتح
///    على بياناتٍ لا على دوّامة.
///
/// **والخطوة الثالثة لا تحبس أحداً.** `Snapshot` لا ترمي، والفشلُ يُكتب
/// سطراً («تعذّرت المزامنة») ويُفتح البابُ على أي حال — التصفّح لا يحتاج
/// جلسةً ولا يحتاج أن تكون المزامنةُ نجحت.
///
/// **ولا تُغادَر الشاشةُ من نفسها.** بأمر المالك (١٩ سبتمبر ٢٠٢٦): «خلى
/// فيها زر التالي اما اضغط عليه يدخلني، مش تظهر وتختفي بعد ثواني». فلا
/// مؤقّتَ خروجٍ ولا حدَّ أدنى للبقاء — الخروجُ ضغطةٌ واحدة على «التالي»،
/// ولا غير.
///
/// وثمنُ ذلك مذكور: فتحةٌ إضافيّةٌ في كلّ إقلاع. وهو مقصودٌ — الشاشةُ صارت
/// لوحةَ ترحيبٍ تُقرأ، لا ومضةً تمرّ.
///
/// **والسقفُ باقٍ ومعناه تغيّر** ([_hardCeiling]): كان يُخرج المستخدم بعد
/// سبع ثوانٍ، وصار **يُمكّن الزرَّ** بعدها. تخزينٌ آمنٌ لا يجيب — يقع على
/// أجهزةٍ فيها عطبٌ في `Keystore` — أو شبكةٌ معلَّقة، كانا سيتركان الزرَّ
/// معطَّلاً إلى الأبد، أي بابٌ مرسومٌ لا يُفتح.
///
/// **والرسمُ لا يعتمد على الحركة:** من أطفأها في جهازه يرى المشهدَ كاملاً
/// ثابتاً لا نصفَه — `MediaQuery.disableAnimationsOf` تُقرأ ويُقفز إلى
/// النهاية.
class SplashScreen extends ConsumerStatefulWidget {
  const SplashScreen({super.key});

  @override
  ConsumerState<SplashScreen> createState() => _SplashScreenState();
}

/// بعدها يُمكَّن الزرُّ ولو لم تنتهِ الخطوات: جلسةٌ أو شبكةٌ لا تجيب كانت
/// ستترك البابَ مرسوماً لا يُفتح.
const Duration _hardCeiling = Duration(seconds: 7);

/// خطواتُ الإقلاع بالترتيب. النسبةُ = المنتهي ÷ الكلّ، لا رقمٌ يُختار.
enum _Step { boot, session, auctions, ready }

class _SplashScreenState extends ConsumerState<SplashScreen>
    with SingleTickerProviderStateMixin {
  late final AnimationController _motion = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: 1200),
  );

  _Step _step = _Step.boot;

  /// يُفتح البابُ وإن لم تنتهِ الخطوات — انظر [_hardCeiling].
  bool _timedOut = false;
  bool _syncFailed = false;
  bool _sessionDone = false;
  bool _auctionsDone = false;
  bool _left = false;
  Timer? _ceiling;

  @override
  void initState() {
    super.initState();
    _motion.forward();
    _ceiling = Timer(_hardCeiling, () {
      if (mounted) setState(() => _timedOut = true);
    });
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _advance(_Step.session);
      unawaited(_syncAuctions());
    });
  }

  @override
  void dispose() {
    _ceiling?.cancel();
    _motion.dispose();
    super.dispose();
  }

  void _advance(_Step to) {
    if (!mounted || _step.index >= to.index) return;
    setState(() => _step = to);
  }

  /// يجلب لوحة المزايدات مرّةً. لا يرمي ولا يمنع الدخول.
  Future<void> _syncAuctions() async {
    final snapshot = await ref.read(loadHomeAuctionsProvider)();
    if (!mounted) return;
    setState(() {
      _auctionsDone = true;
      _syncFailed = snapshot.value == null;
    });
    _maybeReady();
  }

  /// يُعلن الجاهزيّة حين تنتهي الخطوتان اللتان تُنتظران — **ولا يخرج**.
  void _maybeReady() {
    if (!_sessionDone || !_auctionsDone) return;
    _advance(_Step.ready);
    _ceiling?.cancel();
  }

  /// ينتقل إلى صفحة الترحيب مرّةً واحدة — **بضغطة «التالي» وحدها**.
  ///
  /// و`go` لا `push`: شاشةُ البدء ليست محطّةً يُرجَع إليها، ولا يصحّ أن
  /// يعيد زرُّ الرجوع عرضَ الشعار بعد أن انتهت خطواتُه.
  void _leave() {
    if (_left || !mounted) return;
    _left = true;
    _ceiling?.cancel();
    context.go(Routes.welcomePath);
  }

  @override
  Widget build(BuildContext context) {
    // الاستماع في `build`: الحالةُ قد تُعرف قبل أوّل إطارٍ أصلاً، و`listen`
    // وحدَه لا يرى ما وقع قبله.
    ref.listen<SessionState>(sessionControllerProvider, (_, next) {
      if (next != SessionState.unknown) _onSessionKnown();
    });
    if (ref.watch(sessionControllerProvider) != SessionState.unknown) {
      WidgetsBinding.instance.addPostFrameCallback((_) => _onSessionKnown());
    }

    final theme = Theme.of(context);
    final palette = theme.extension<HarajPalette>()!;
    final strings = AppLocalizations.of(context);
    final still = MediaQuery.disableAnimationsOf(context);

    return Scaffold(
      backgroundColor: palette.heroBottom,
      body: DecoratedBox(
        // التدرّجُ نفسُه الذي في لافتة الرئيسية وشاشة الدخول: شاشةُ البدء
        // وعدٌ بما يليها، وأرضيّةٌ ثالثةٌ تجعل الانتقال يُقرأ قفزة.
        decoration: BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            colors: <Color>[palette.heroTop, palette.heroBottom],
          ),
        ),
        child: Stack(
          fit: StackFit.expand,
          children: <Widget>[
            // الشبكةُ والنقاط: عمقٌ بلا صورةٍ تُحمَّل. `RepaintBoundary` لأن
            // الشريطَ يُعاد رسمُه عشراتِ المرّات ولا شأن للخلفيّة به.
            RepaintBoundary(
              child: CustomPaint(
                painter: _Backdrop(
                  line: palette.goldOnDark.withValues(alpha: 0.05),
                  dot: palette.heroGlow,
                ),
              ),
            ),
            // وهجٌ خلف الشعار — يرفعه عن الأرضيّة بلا حدٍّ يرسمه.
            DecoratedBox(
              decoration: BoxDecoration(
                gradient: RadialGradient(
                  center: const Alignment(0, -0.22),
                  radius: 0.85,
                  colors: <Color>[
                    palette.heroGlow.withValues(alpha: 0.20),
                    palette.heroGlow.withValues(alpha: 0),
                  ],
                ),
              ),
            ),
            SafeArea(
              child: LayoutBuilder(
                builder: (context, box) => SingleChildScrollView(
                  // الشاشةُ طويلةُ المحتوى: على هاتفٍ قصيرٍ تفيض بالبكسلات
                  // الصفراء. فتُمرَّر، وتبقى موزَّعةً حين يتّسع المكان.
                  //
                  // **و`IntrinsicHeight` ليست زينة.** `Spacer` يقتسم ما
                  // **بقي** من ارتفاع، وداخل غلافٍ قابلٍ للتمرير لا حدَّ
                  // للارتفاع — فيحسب الباقي صفراً وينكمش، فيتكوّم المحتوى
                  // في الأعلى ويبقى الثلثُ السفليُّ فارغاً. رُئي في اللقطة
                  // قبل أن يُصلَح. و`ConstrainedBox` وحدَها لا تكفي: هي
                  // تعطي حدّاً أدنى للطفل، لا ارتفاعاً يقتسمه.
                  padding: const EdgeInsets.symmetric(horizontal: 24),
                  child: ConstrainedBox(
                    // **ارتفاعٌ فقط، ولا `maxWidth` هنا.** الغلافُ خصم
                    // حشوتَه (٢٤×٢) من العرض أصلاً، وإعطاءُ الطفل عرضَ
                    // الشاشة كاملاً يجعله أوسعَ من مكانه بثمانيةٍ وأربعين
                    // بكسلاً — فيخرج الزرُّ من الحافّة ويُقصّ آخرُ كل سطر.
                    // رُئي في اللقطة.
                    constraints: BoxConstraints(minHeight: box.maxHeight),
                    child: IntrinsicHeight(
                      child: _Layout(
                      metrics: OnboardingMetrics.of(box.maxHeight),
                        theme: theme,
                        palette: palette,
                        strings: strings,
                        motion: _motion,
                        still: still,
                        step: _step,
                        syncFailed: _syncFailed,
                        timedOut: _timedOut,
                        onEnter: _leave,
                      ),
                    ),
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  void _onSessionKnown() {
    if (_sessionDone) return;
    _sessionDone = true;
    _advance(_Step.auctions);
    _maybeReady();
  }
}

// ---------------------------------------------------------------------------
// التخطيط
// ---------------------------------------------------------------------------

class _Layout extends StatelessWidget {
  const _Layout({
    required this.theme,
    required this.palette,
    required this.strings,
    required this.motion,
    required this.still,
    required this.step,
    required this.syncFailed,
    required this.timedOut,
    required this.onEnter,
    required this.metrics,
  });

  final ThemeData theme;
  final HarajPalette palette;
  final AppLocalizations strings;
  final AnimationController motion;
  final bool still;
  final _Step step;
  final bool syncFailed;
  final bool timedOut;
  final VoidCallback onEnter;
  final OnboardingMetrics metrics;

  @override
  Widget build(BuildContext context) {
    final ready = step == _Step.ready || timedOut;

    return Column(
      children: <Widget>[
        // **حُذفت الشارةُ العليا وصفُّ الميزات** بأمر المالك: «قلل المحتوى
        // فى الصفحه دى شويه». وكلاهما كان يقول ما يُقال مرّتين:
        //
        // * «بوابة المزادات الرقمية المعتمدة» فوق الشعار، وتحته مباشرةً
        //   «مزاد حي ومعتمد» — كلمةُ «معتمد» مرّتين في أربعة سنتيمترات.
        // * و«فحص معتمد · مزايدة حية · ضمان النقل» هي بعينها وعودُ الصفحة
        //   الثالثة، وتُقرأ هناك في سياقها لا في شاشةِ إقلاع.
        //
        // فبقي ما تُفتح الشاشةُ لأجله: الشعارُ والاسمُ وسطرٌ يقول ما هي،
        // وأثرُ الانتظار، والباب.
        const Spacer(flex: 3),
        _Mark(
          palette: palette,
          motion: motion,
          still: still,
          strings: strings,
          size: metrics.mark,
        ),
        SizedBox(height: metrics.gap),
        _Rise(
          motion: motion,
          still: still,
          from: 0.4,
          child: Column(
            children: <Widget>[
              Text(
                strings.splashHeadline,
                textAlign: TextAlign.center,
                style: theme.textTheme.headlineMedium?.copyWith(
                  fontWeight: FontWeight.w700,
                  color: Colors.white,
                  letterSpacing: -0.4,
                ),
              ),
              const SizedBox(height: 10),
              Text(
                strings.splashTagline,
                textAlign: TextAlign.center,
                style: theme.textTheme.bodyMedium?.copyWith(
                  color: palette.goldOnDark,
                  height: 1.6,
                ),
              ),
            ],
          ),
        ),
        const Spacer(flex: 4),
        _Progress(
          palette: palette,
          theme: theme,
          strings: strings,
          step: step,
          syncFailed: syncFailed,
          still: still,
        ),
        SizedBox(height: metrics.tight),
        _EnterButton(
          palette: palette,
          theme: theme,
          label: strings.splashEnter,
          // **الزرُّ لا يُخفى قبل الجاهزيّة، يُعطَّل.** زرٌّ يظهر فجأةً
          // يُفوَّت، وزرٌّ معطَّلٌ يقول «هذا هو الباب، وهو يُفتح الآن».
          // وهو **المخرجُ الوحيد**: الشاشةُ لا تُغادَر من نفسها.
          onPressed: ready ? onEnter : null,
        ),
        SizedBox(height: metrics.gap),
        _Footer(palette: palette, theme: theme, strings: strings),
        const SizedBox(height: 16),
      ],
    );
  }
}

// ---------------------------------------------------------------------------
// القطع
// ---------------------------------------------------------------------------

/// الشعارُ في حلقته، وشارةُ «مزادٌ حيّ» على حافّته.
class _Mark extends StatelessWidget {
  const _Mark({
    required this.palette,
    required this.motion,
    required this.still,
    required this.strings,
    required this.size,
  });

  final HarajPalette palette;
  final AnimationController motion;
  final bool still;
  final AppLocalizations strings;

  /// قطرُ الحلقة الخارجيّة. **يتقلّص على الشاشة القصيرة** — قرصٌ ٢٣٦ بكسلاً
  /// على هاتفٍ متاحُه ٥٨٧ يدفع الشريطَ والزرَّ خارج الشاشة.
  final double size;

  @override
  Widget build(BuildContext context) {
    final grow = CurvedAnimation(
      parent: motion,
      curve: const Interval(0, 0.65, curve: Curves.easeOutBack),
    );

    // الحلقاتُ والقرصُ نِسَبٌ من [size] لا أرقامٌ ثابتة، فيتقلّص المشهدُ
    // كلُّه معاً لا الإطارُ وحدَه.
    final inner = size * 188 / 236;
    final disc = size * 168 / 236;

    final mark = SizedBox(
      width: size,
      height: size,
      child: Stack(
        alignment: Alignment.center,
        clipBehavior: Clip.none,
        children: <Widget>[
          // حلقتان خافتتان: عمقٌ حول الشعار بلا إطارٍ يحبسه.
          _Ring(color: palette.goldOnDark.withValues(alpha: 0.10), size: size),
          _Ring(color: palette.goldOnDark.withValues(alpha: 0.16), size: inner),
          Container(
            width: disc,
            height: disc,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              gradient: RadialGradient(
                colors: <Color>[
                  palette.heroGlow.withValues(alpha: 0.22),
                  palette.heroGlow.withValues(alpha: 0),
                ],
              ),
            ),
            // **الشعارُ هو `assets/images/logo.png`** لا حرفٌ في دائرة —
            // الصورةُ هي التي تجعل الشاشةَ تُقرأ «حراج» قبل أن يُقرأ سطر.
            // و`errorBuilder` لأن شاشةَ بدءٍ لا تسقط لأجل صورة: بدونه يبقى
            // المستخدم أمام أرضيّةٍ كحليّةٍ بلا خبر.
            child: Padding(
              padding: EdgeInsets.all(disc * 0.085),
              child: Image.asset(
                'assets/images/logo.png',
                fit: BoxFit.contain,
                errorBuilder: (_, _, _) => Icon(
                  Icons.gavel_rounded,
                  color: palette.goldOnDark,
                  size: 64,
                ),
              ),
            ),
          ),
          Positioned(
            bottom: size * 0.07,
            child: _LiveBadge(
              palette: palette,
              label: strings.splashLiveBadge,
            ),
          ),
        ],
      ),
    );

    if (still) return mark;

    return ScaleTransition(
      scale: Tween<double>(begin: 0.88, end: 1).animate(grow),
      child: FadeTransition(opacity: grow, child: mark),
    );
  }
}

class _Ring extends StatelessWidget {
  const _Ring({required this.color, required this.size});

  final Color color;
  final double size;

  @override
  Widget build(BuildContext context) => Container(
    width: size,
    height: size,
    decoration: BoxDecoration(
      shape: BoxShape.circle,
      border: Border.all(color: color),
    ),
  );
}

class _LiveBadge extends StatelessWidget {
  const _LiveBadge({required this.palette, required this.label});

  final HarajPalette palette;
  final String label;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 7),
      decoration: BoxDecoration(
        color: palette.gold,
        borderRadius: BorderRadius.circular(999),
        boxShadow: <BoxShadow>[
          BoxShadow(
            color: palette.gold.withValues(alpha: 0.45),
            blurRadius: 18,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: <Widget>[
          Text(
            label,
            style: const TextStyle(
              color: Colors.white,
              fontSize: 12,
              fontWeight: FontWeight.w700,
            ),
          ),
          const SizedBox(width: 6),
          const Icon(Icons.verified_rounded, size: 14, color: Colors.white),
        ],
      ),
    );
  }
}

/// سطرُ الخطوة والنسبة، وتحته الشريط.
///
/// **النسبةُ كسرٌ من خطواتٍ منتهية**، لا رقمٌ يتحرّك مع الزمن: ثلاثُ خطواتٍ،
/// فالقيمُ ٠ و⅓ و⅔ و١ — ولا تقول ٩٩٪ وهي تنتظر.
class _Progress extends StatelessWidget {
  const _Progress({
    required this.palette,
    required this.theme,
    required this.strings,
    required this.step,
    required this.syncFailed,
    required this.still,
  });

  final HarajPalette palette;
  final ThemeData theme;
  final AppLocalizations strings;
  final _Step step;
  final bool syncFailed;
  final bool still;

  @override
  Widget build(BuildContext context) {
    final value = step.index / (_Step.values.length - 1);
    final label = switch (step) {
      _Step.boot => strings.splashStepBoot,
      _Step.session => strings.splashStepSession,
      _Step.auctions => strings.splashStepAuctions,
      _Step.ready =>
        syncFailed ? strings.splashStepOffline : strings.splashStepReady,
    };

    return Semantics(
      label: strings.splashLoadingLabel,
      value: label,
      liveRegion: true,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: <Widget>[
          Row(
            children: <Widget>[
              Container(
                width: 7,
                height: 7,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: syncFailed ? palette.gold : palette.goldOnDark,
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  label,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: theme.textTheme.labelMedium?.copyWith(
                    color: Colors.white.withValues(alpha: 0.82),
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ),
              Text(
                '${(value * 100).round()}%',
                // الأرقامُ لاتينيّةٌ مستقيمة: نسبةٌ تتغيّر في مكانها تقفز
                // يميناً ويساراً إن اختلفت عروضُ الخانات.
                textDirection: TextDirection.ltr,
                style: theme.textTheme.titleMedium?.copyWith(
                  color: Colors.white,
                  fontWeight: FontWeight.w700,
                  fontFeatures: const <FontFeature>[
                    FontFeature.tabularFigures(),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 10),
          ClipRRect(
            borderRadius: BorderRadius.circular(999),
            child: TweenAnimationBuilder<double>(
              tween: Tween<double>(begin: 0, end: value),
              duration: still
                  ? Duration.zero
                  : const Duration(milliseconds: 420),
              curve: Curves.easeOut,
              builder: (context, shown, _) => LinearProgressIndicator(
                value: shown,
                minHeight: 6,
                backgroundColor: Colors.white.withValues(alpha: 0.10),
                valueColor: AlwaysStoppedAnimation<Color>(palette.gold),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _EnterButton extends StatelessWidget {
  const _EnterButton({
    required this.palette,
    required this.theme,
    required this.label,
    required this.onPressed,
  });

  final HarajPalette palette;
  final ThemeData theme;
  final String label;
  final VoidCallback? onPressed;

  @override
  Widget build(BuildContext context) {
    final on = onPressed != null;
    return SizedBox(
      // **`double.infinity` صراحةً.** الزرُّ في عمودٍ محاذاتُه العرضيّة
      // `center`، فيأخذ عرضَ محتواه لا عرضَ الشاشة. وكان يملؤها قبلُ
      // بالصدفة: الصفُّ الذي بداخله كان يتمدّد. فلمّا حُذف الصفُّ انكمش
      // الزرُّ إلى كلمةٍ واحدة — رُئي في لقطة المالك.
      width: double.infinity,
      height: 56,
      child: FilledButton(
        onPressed: onPressed,
        style: FilledButton.styleFrom(
          backgroundColor: palette.gold,
          disabledBackgroundColor: palette.gold.withValues(alpha: 0.35),
          foregroundColor: Colors.white,
          disabledForegroundColor: Colors.white.withValues(alpha: 0.7),
          elevation: on ? 8 : 0,
          shadowColor: palette.gold.withValues(alpha: 0.5),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(16),
          ),
          textStyle: theme.textTheme.titleMedium?.copyWith(
            fontWeight: FontWeight.w700,
          ),
        ),
        // **السهمُ هنا وحدَه.** حُذف من الأزرار الثلاثة، ثمّ أُعيد إلى هذا
        // بأمر المالك: «خلى السهم ف الصفحه دى بس». وله معنى هنا أكثرَ من
        // أختيه — زرُّ شاشة البدء **يُفتح بعد انتظار**، والسهمُ يقول إن
        // الانتظار انتهى وإن ما بعده بابٌ لا مجرّد صفحةٍ تالية.
        //
        // و`arrow_forward` لا `arrow_back`: Flutter يمرئي السهمَ مع
        // الاتّجاه، فـ`back` في صفحةٍ عربيّةٍ يشير يميناً — أي إلى الوراء.
        child: Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: <Widget>[
            Text(label),
            const SizedBox(width: 10),
            const Icon(Icons.arrow_forward_rounded, size: 20),
          ],
        ),
      ),
    );
  }
}

class _Footer extends StatelessWidget {
  const _Footer({
    required this.palette,
    required this.theme,
    required this.strings,
  });

  final HarajPalette palette;
  final ThemeData theme;
  final AppLocalizations strings;

  @override
  Widget build(BuildContext context) {
    final style = theme.textTheme.labelSmall?.copyWith(
      color: palette.goldOnDark.withValues(alpha: 0.65),
    );
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: <Widget>[
        Flexible(
          child: Text(strings.splashPlace, style: style, maxLines: 1),
        ),
        const SizedBox(width: 12),
        Text(
          strings.splashVersion(kAppVersion),
          style: style?.copyWith(letterSpacing: 1.2),
        ),
      ],
    );
  }
}

// ---------------------------------------------------------------------------
// الخلفيّة والحركة
// ---------------------------------------------------------------------------

/// شبكةٌ خافتةٌ ونقاطٌ على الحافّة العليا.
///
/// **رسمٌ لا صورة**: صورةُ خلفيّةٍ تزن مئاتِ الكيلوبايتات وتُحمَّل قبل أوّل
/// إطارٍ — في شاشةٍ وجودُها كلُّه أن تسدّ فراغ الانتظار. والخطوط تُرسم في
/// أجزاءٍ من الملّي ثانية.
class _Backdrop extends CustomPainter {
  const _Backdrop({required this.line, required this.dot});

  final Color line;
  final Color dot;

  static const double _cell = 34;

  @override
  void paint(Canvas canvas, Size size) {
    final pen = Paint()
      ..color = line
      ..strokeWidth = 1;
    for (double x = 0; x < size.width; x += _cell) {
      canvas.drawLine(Offset(x, 0), Offset(x, size.height), pen);
    }
    for (double y = 0; y < size.height; y += _cell) {
      canvas.drawLine(Offset(0, y), Offset(size.width, y), pen);
    }

    // نقاطٌ على الحافّة العليا بأنصبةٍ ثابتةٍ لا عشوائيّة: عشوائيٌّ يعني
    // نقاطاً تقفز مع كل إعادة رسم.
    const spots = <(double, double, double)>[
      (0.08, 3.0, 0.9),
      (0.21, 2.0, 0.5),
      (0.34, 2.5, 0.7),
      (0.47, 1.8, 0.4),
      (0.62, 3.0, 0.85),
      (0.76, 2.2, 0.55),
      (0.89, 2.6, 0.75),
    ];
    for (final (at, radius, alpha) in spots) {
      canvas.drawCircle(
        Offset(size.width * at, 6),
        radius,
        Paint()..color = dot.withValues(alpha: alpha),
      );
    }
  }

  @override
  bool shouldRepaint(_Backdrop old) => old.line != line || old.dot != dot;
}

/// يظهر صاعداً بعد تأخيرٍ نسبيّ — أو كاملاً ثابتاً حين تُطفأ الحركة.
class _Rise extends StatelessWidget {
  const _Rise({
    required this.motion,
    required this.still,
    required this.from,
    required this.child,
  });

  final AnimationController motion;
  final bool still;

  /// بدايةُ المقطع على مدى المشهد، بين ٠ و١.
  final double from;

  final Widget child;

  @override
  Widget build(BuildContext context) {
    if (still) return child;
    final curve = CurvedAnimation(
      parent: motion,
      curve: Interval(from, 1, curve: Curves.easeOut),
    );
    return FadeTransition(
      opacity: curve,
      child: SlideTransition(
        position: Tween<Offset>(
          begin: const Offset(0, 0.3),
          end: Offset.zero,
        ).animate(curve),
        child: child,
      ),
    );
  }
}
