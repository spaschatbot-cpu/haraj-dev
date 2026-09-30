import 'dart:async';
import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../app/providers.dart';
import '../../app/routes.dart';
import '../../app/theme.dart';
import '../../core/environment.dart';
import '../../data/local/onboarding_store.dart';
import '../../domain/common/snapshot.dart';
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
/// **وتُغادَر الشاشةُ من نفسها حين تجهز** — بأمر المالك (٢٩ سبتمبر ٢٠٢٦):
/// «شيل البروجريس بار وزرار التالي». وكان قد طلب الزرَّ في ١٩ سبتمبر («مش
/// تظهر وتختفي بعد ثواني»)؛ والأمرُ الأحدث يعلو. فلا شريطَ ولا نسبةَ ولا
/// زرّ: حبّةُ الحالة تقول ما يجري، ثمّ يُفتح الباب.
///
/// **والسقفُ باقٍ** ([_hardCeiling]): بعده يُفتح البابُ ولو لم تنتهِ
/// الخطوات. تخزينٌ آمنٌ لا يجيب — يقع على أجهزةٍ فيها عطبٌ في `Keystore` —
/// أو شبكةٌ معلَّقة، كانا سيتركان الشاشةَ قائمةً إلى الأبد.
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

  bool _syncFailed = false;
  bool _sessionDone = false;
  bool _auctionsDone = false;
  bool _left = false;
  Timer? _ceiling;

  @override
  void initState() {
    super.initState();
    _motion.forward();
    _ceiling = Timer(_hardCeiling, _leave);
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
  ///
  /// **و«غير متصل» تُقرأ من `origin` لا من `value`.** T956.
  ///
  /// كان الشرطُ `snapshot.value == null`، و`Snapshot.value` غيرُ قابلٍ للعدم
  /// أصلاً — فالعلمُ لا يصير صحيحاً أبداً، وسطرُ `splashStepOffline` ميّتٌ
  /// والشاشةُ تقول «جاهز» ولو لم يصل الخادمُ إطلاقاً. والمحلّلُ يقولها:
  /// «the operand can't be null, so the condition is always false».
  ///
  /// و`DataOrigin.cache` هو المعنى المقصود بنصّه في `snapshot.dart`: «نسخة
  /// قديمة من الكاش **بعد تعذّر الوصول للخادم**».
  ///
  /// **والرميُ يُمسَك**: بلا كاشٍ أصلاً (أوّلُ إقلاعٍ بلا شبكة) يرمي المستودع،
  /// وهذه الدالّة تُنادى بـ`unawaited` فيضيع الرميُ في الفراغ — و`_auctionsDone`
  /// يبقى `false`، فلا يصل `_maybeReady` إلى `ready` أبداً وتتعلّق الشاشةُ
  /// على «جارٍ التحميل» حتى يقطعها السقفُ الزمنيّ. توثيقُها يقول «لا يرمي»،
  /// فصار الكودُ يقول ما يقوله التوثيق.
  Future<void> _syncAuctions() async {
    var offline = false;
    try {
      final snapshot = await ref.read(loadHomeAuctionsProvider)();
      offline = snapshot.origin == DataOrigin.cache;
    } on Object {
      // لا كاشَ ولا شبكة. الدخولُ لا يُمنَع — والشريطُ يقول «غير متصل».
      offline = true;
    }
    if (!mounted) return;
    setState(() {
      _auctionsDone = true;
      _syncFailed = offline;
    });
    _maybeReady();
  }

  /// يُعلن الجاهزيّة حين تنتهي الخطوتان اللتان تُنتظران — **ولا يخرج**.
  void _maybeReady() {
    if (!_sessionDone || !_auctionsDone) return;
    _advance(_Step.ready);
    _ceiling?.cancel();
    // لحظةٌ تُقرأ فيها «جاهز» ثمّ يُفتح الباب — لا قفزةٌ في الإطار نفسه.
    Timer(const Duration(milliseconds: 700), _leave);
  }

  /// يغادر مرّةً واحدة — حين تجهز الخطوات، أو عند السقف.
  ///
  /// **إلى الترحيب في أوّل مرّةٍ وحدها** (أمر المالك، ٣٠ سبتمبر ٢٠٢٦)، وإلى
  /// الرئيسية بعدها — وكذلك من دخل بحسابه: من سجّل دخوله رأى التطبيقَ قبلُ
  /// ولو كان هذا جهازاً جديداً.
  ///
  /// و`go` لا `push`: شاشةُ البدء ليست محطّةً يُرجَع إليها.
  Future<void> _leave() async {
    if (_left || !mounted) return;
    _left = true;
    _ceiling?.cancel();
    final signedIn =
        ref.read(sessionControllerProvider) == SessionState.signedIn;
    final seen = signedIn || await ref.read(onboardingStoreProvider).seen();
    if (!mounted) return;
    context.go(seen ? Routes.homePath : Routes.welcomePath);
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

    // **أرضيّةٌ فاتحة لا كحليّة** — تصميمُ المالك (٢٨ سبتمبر ٢٠٢٦): قرصُ الشعار
    // الداكن وحدَه على صفحةٍ فاتحة، فيصير هو مركزَ الشاشة لا جزءاً من ظلامها.
    // والأرضيّةُ `pageBackground` نفسُها التي تحت كلّ شاشةٍ بعدها، فلا قفزةَ
    // لونٍ عند «التالي».
    return Theme(
      data: theme,
      child: Scaffold(
        backgroundColor: palette.pageBackground,
        body: DecoratedBox(
          decoration: BoxDecoration(
            gradient: LinearGradient(
              begin: Alignment.topCenter,
              end: Alignment.bottomCenter,
              colors: <Color>[
                Color.alphaBlend(
                  palette.gold.withValues(alpha: 0.04),
                  palette.pageBackground,
                ),
                palette.pageBackground,
                Color.alphaBlend(
                  palette.gold.withValues(alpha: 0.07),
                  palette.pageBackground,
                ),
              ],
            ),
          ),
          child: SafeArea(
            child: LayoutBuilder(
              builder: (context, box) => SingleChildScrollView(
                // الشاشةُ تُمرَّر على الهاتف القصير ولا تفيض، وتبقى موزَّعةً حين
                // يتّسع المكان. و`IntrinsicHeight` لأن `Spacer` داخل غلافٍ قابلٍ
                // للتمرير يحسب الباقي صفراً فيتكوّم المحتوى في الأعلى.
                padding: const EdgeInsets.symmetric(horizontal: 24),
                child: ConstrainedBox(
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
                    ),
                  ),
                ),
              ),
            ),
          ),
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
    required this.metrics,
  });

  final ThemeData theme;
  final HarajPalette palette;
  final AppLocalizations strings;
  final AnimationController motion;
  final bool still;
  final _Step step;
  final bool syncFailed;
  final OnboardingMetrics metrics;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: <Widget>[
        const Spacer(flex: 3),
        _Mark(
          palette: palette,
          motion: motion,
          still: still,
          strings: strings,
          size: metrics.mark * 1.1,
        ),
        SizedBox(height: metrics.gap * 1.5),
        _Rise(
          motion: motion,
          still: still,
          from: 0.4,
          child: Column(
            children: <Widget>[
              Text(
                strings.splashHeadline,
                textAlign: TextAlign.center,
                // الحجمُ صريح: `headlineMedium` في هذا الثيم يُرسم أصغرَ من
                // سطر الوصف تحته، والتصميمُ عنوانُه أكبرُ ما في الشاشة.
                style: theme.textTheme.headlineMedium?.copyWith(
                  fontSize: 30,
                  fontWeight: FontWeight.w700,
                  color: palette.ink,
                  letterSpacing: -0.4,
                ),
              ),
              const SizedBox(height: 10),
              Text(
                strings.splashTagline,
                textAlign: TextAlign.center,
                style: theme.textTheme.bodyLarge?.copyWith(
                  color: palette.inkMuted,
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
        ),
        SizedBox(height: metrics.gap),
        if (step != _Step.ready)
          _Waiting(
            palette: palette,
            theme: theme,
            label: strings.splashLoadingLabel,
          )
        else
          const SizedBox(height: 40),
        SizedBox(height: metrics.gap * 1.5),
        _Footer(palette: palette, theme: theme, strings: strings),
        const SizedBox(height: 12),
      ],
    );
  }
}

// ---------------------------------------------------------------------------
// القطع
// ---------------------------------------------------------------------------

/// نجاحٌ تمّ — حبّةُ «جاهز». قيمُ `--color-ok` في الموقع نفسُها.
const Color _okInk = Color(0xFF047857);
const Color _okSurface = Color(0xFFECFDF5);
const Color _okLine = Color(0xFFA7F3D0);

/// الشعارُ في قرصٍ داكنٍ بإطارٍ أبيض، وحلقتان حوله — الداخليّةُ متقطّعة.
///
/// **وسقطت شارةُ «مزاد حي ومعتمد»** عن حافّة القرص بأمر المالك (٢٩ سبتمبر).
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

  /// قطرُ الحلقة الخارجيّة. **يتقلّص على الشاشة القصيرة** ويتقلّص المشهدُ
  /// كلُّه معه، لأن كلَّ ما فيه نسبةٌ منه.
  final double size;

  @override
  Widget build(BuildContext context) {
    final grow = CurvedAnimation(
      parent: motion,
      curve: const Interval(0, 0.65, curve: Curves.easeOutBack),
    );

    final dashed = size * 0.81;
    final disc = size * 0.54;

    final mark = SizedBox(
      width: size,
      height: size,
      child: Stack(
        alignment: Alignment.center,
        clipBehavior: Clip.none,
        children: <Widget>[
          // الحلقةُ الخارجيّة ووهجٌ فاتحٌ داخلها يرفع القرصَ عن الصفحة.
          Container(
            width: size,
            height: size,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              border: Border.all(color: palette.gold.withValues(alpha: 0.12)),
              gradient: RadialGradient(
                colors: <Color>[
                  palette.gold.withValues(alpha: 0.10),
                  palette.gold.withValues(alpha: 0),
                ],
              ),
            ),
          ),
          CustomPaint(
            size: Size.square(dashed),
            painter: _DashedRing(color: palette.gold.withValues(alpha: 0.30)),
          ),
          Container(
            width: disc,
            height: disc,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              gradient: LinearGradient(
                begin: Alignment.topRight,
                end: Alignment.bottomLeft,
                colors: <Color>[
                  Color.alphaBlend(
                    palette.gold.withValues(alpha: 0.35),
                    palette.heroTop,
                  ),
                  palette.heroBottom,
                ],
              ),
              border: Border.all(color: Colors.white, width: disc * 0.035),
              boxShadow: <BoxShadow>[
                BoxShadow(
                  color: palette.gold.withValues(alpha: 0.28),
                  blurRadius: 36,
                  offset: const Offset(0, 12),
                ),
              ],
            ),
            // **الشعارُ هو `assets/images/logo.png`** لا حرفٌ في دائرة.
            // و`errorBuilder` لأن شاشةَ بدءٍ لا تسقط لأجل صورة.
            child: Padding(
              padding: EdgeInsets.all(disc * 0.2),
              child: Image.asset(
                'assets/images/logo.png',
                fit: BoxFit.contain,
                errorBuilder: (_, _, _) => const Icon(
                  Icons.gavel_rounded,
                  color: Colors.white,
                  size: 56,
                ),
              ),
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

/// حلقةٌ متقطّعة — `Border` في Flutter لا يعرف التقطيع، فتُرسم أقواساً.
class _DashedRing extends CustomPainter {
  const _DashedRing({required this.color});

  final Color color;

  @override
  void paint(Canvas canvas, Size size) {
    final pen = Paint()
      ..color = color
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1.2;
    final rect = Offset.zero & size;
    const dashes = 72;
    const sweep = 2 * math.pi / dashes;
    for (var index = 0; index < dashes; index += 1) {
      canvas.drawArc(rect, index * sweep, sweep * 0.55, false, pen);
    }
  }

  @override
  bool shouldRepaint(_DashedRing old) => old.color != color;
}

/// حبّةُ الحالة — الخطوةُ الجارية باسمها. **بلا نسبةٍ ولا شريط** بأمر المالك
/// (٢٩ سبتمبر). خضراءُ حين تمّ كلُّ شيء، وكهرمانيّةٌ حين تعذّرت المزامنة،
/// وزرقاءُ ما دام العملُ جارياً.
///
/// والتصميمُ كتب فيها «اتصال آمن ومشفّر»، وكُتب هنا «متصل بالخادم»: هذا ما
/// قاسته الشاشةُ فعلاً (نجحت المزامنة)، والتشفيرُ صفةُ الرابط لا شيءٌ تتحقّق
/// منه — وبناءُ التطوير على `http` أصلاً.
class _Progress extends StatelessWidget {
  const _Progress({
    required this.palette,
    required this.theme,
    required this.strings,
    required this.step,
    required this.syncFailed,
  });

  final HarajPalette palette;
  final ThemeData theme;
  final AppLocalizations strings;
  final _Step step;
  final bool syncFailed;

  @override
  Widget build(BuildContext context) {
    final done = step == _Step.ready;
    final label = switch (step) {
      _Step.boot => strings.splashStepBoot,
      _Step.session => strings.splashStepSession,
      _Step.auctions => strings.splashStepAuctions,
      _Step.ready =>
        syncFailed ? strings.splashStepOffline : strings.splashStepReady,
    };
    final (Color ink, Color surface, Color line) = !done
        ? (
            palette.gold,
            palette.gold.withValues(alpha: 0.08),
            palette.gold.withValues(alpha: 0.25),
          )
        : syncFailed
        ? (
            const Color(0xFFB45309),
            const Color(0xFFFFFBEB),
            const Color(0xFFFDE68A),
          )
        : (_okInk, _okSurface, _okLine);

    return Semantics(
      label: strings.splashLoadingLabel,
      value: label,
      liveRegion: true,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: <Widget>[
          Center(
            child: AnimatedContainer(
              duration: const Duration(milliseconds: 260),
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
              decoration: BoxDecoration(
                color: surface,
                borderRadius: BorderRadius.circular(999),
                border: Border.all(color: line),
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: <Widget>[
                  Container(
                    width: 8,
                    height: 8,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      color: ink,
                    ),
                  ),
                  const SizedBox(width: 8),
                  Flexible(
                    child: Text(
                      label,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: theme.textTheme.labelLarge?.copyWith(
                        color: ink,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

/// سطرُ الانتظار بدوّامته إلى أن يُفتح الباب.
class _Waiting extends StatelessWidget {
  const _Waiting({
    required this.palette,
    required this.theme,
    required this.label,
  });

  final HarajPalette palette;
  final ThemeData theme;
  final String label;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: 56,
      child: Row(
        mainAxisAlignment: MainAxisAlignment.center,
        children: <Widget>[
          SizedBox(
            width: 16,
            height: 16,
            child: CircularProgressIndicator(
              strokeWidth: 2,
              color: palette.gold,
              backgroundColor: palette.gold.withValues(alpha: 0.15),
            ),
          ),
          const SizedBox(width: 10),
          Text(
            '$label…',
            style: theme.textTheme.bodyMedium?.copyWith(
              color: palette.inkMuted,
            ),
          ),
        ],
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
    final style = theme.textTheme.bodySmall?.copyWith(color: palette.inkMuted);
    return Container(
      padding: const EdgeInsets.only(top: 14),
      decoration: BoxDecoration(
        border: Border(
          top: BorderSide(color: palette.navInactive.withValues(alpha: 0.6)),
        ),
      ),
      child: Row(
        children: <Widget>[
          Icon(Icons.place_outlined, size: 18, color: palette.gold),
          const SizedBox(width: 6),
          Expanded(child: Text(strings.splashPlace, style: style, maxLines: 1)),
          const SizedBox(width: 12),
          Text(
            strings.splashVersion(kAppVersion),
            style: style?.copyWith(
              color: palette.inkMuted.withValues(alpha: 0.75),
            ),
          ),
        ],
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// الحركة
// ---------------------------------------------------------------------------

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
