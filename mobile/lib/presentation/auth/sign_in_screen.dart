import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../app/providers.dart';
import '../../app/router.dart';
import '../../app/theme.dart';
import '../../domain/catalog/entities/auction_summary.dart';
import '../../domain/common/failure.dart';
import '../../l10n/generated/app_localizations.dart';
import '../catalog/widgets/countdown_text.dart';
import '../common/cooldown_button.dart';
import '../common/failure_view.dart';
import '../common/saudi_phone_field.dart';
import 'auth_shell.dart';
import 'pending_sign_in.dart';
import 'session_controller.dart';

/// الخطوة الأولى: رقم الجوال.
///
/// **لا تحقّق من شكل الرقم هنا.** شكل الرقم السعودي قاعدة يملكها الخادم
/// (`PHONE_PATTERN`) ويردّ برسالتها العربية؛ ونسخةٌ منها في الشاشة تفترق عنها
/// عند أول تعديل، فيرفض التطبيقُ رقماً يقبله الخادم أو العكس (المادة ٤-٥).
/// المعطَّل هنا حالة واحدة: حقل فارغ — لا شيء يُرسَل أصلاً.
///
/// و[SaudiPhoneField] **لا يكسر هذه القاعدة**: هو يوحّد ما كُتب (يُسقط `966`
/// و`0` البادئَين ويأخذ الأرقام وحدَها) ولا يحكم على الصحّة. والخادمُ يبقى
/// صاحبَ الكلمة. T944
///
/// ## وما تعرضه الشاشةُ حولَ الحقل. T947
///
/// طلبُ المالك (١٩ سبتمبر ٢٠٢٦): «تصميم أحلى بكتير لصفحة اللوجين… وفيه داتا
/// أكتر وتفاصيل أكتر».
///
/// وكانت لوحةً فيها جملةٌ وحقلٌ وزرّ — تطلب رقمَ جوّالٍ من شخصٍ لم يُقَل له ما
/// الذي وراءَ الباب. فصارت تقول ثلاثةَ أشياءَ **كلُّها صحيحةٌ وقابلةٌ
/// للتحقّق**:
///
/// * **المزادُ الجاري** — اسمُه وكم سيّارةً فيه وكم بقي عليه. يُقرأ من
///   `homeAuctionsProvider` الذي تقرؤه الرئيسيّة، فلا تقول هذه رقماً وتلك
///   غيرَه. وإن تعذّر الجلبُ **لا يُعرَض شيء** — رقمٌ تزيينيٌّ في شاشةِ دخولٍ
///   هو أوّلُ كذبةٍ يقرؤها العميل.
/// * **كيف يدخل** — برمزٍ لمرّة، لا بكلمة مرور.
/// * **ما يحكم المزايدة** — سرّيّةُ المظروف، ووديعةٌ تُسترَدّ بطلبٍ منه.
///
/// ## «مضربُ المزايد» — تصميمُ المالك (١١ أكتوبر ٢٠٢٦)
///
/// اختار من أربعة اقتراحاتٍ على لوحة التصميم الثاني: الشعارُ في **مضرب
/// مزايدة** يطفو على الكحليّ، وتحته ورقةٌ فاتحةٌ تصعد فيها العدّادُ والنموذج.
/// وشرطُه: «خلّي كلام الصفحة زي ما هو» — فلم يتغيّر نصٌّ واحد، تغيّر المكانُ
/// والشكل. وحين يُضغط «إرسال رمز التحقق» يرتفع المضرب كمن رفعه في القاعة.
class SignInScreen extends ConsumerStatefulWidget {
  const SignInScreen({super.key});

  @override
  ConsumerState<SignInScreen> createState() => _SignInScreenState();
}

class _SignInScreenState extends ConsumerState<SignInScreen> {
  final TextEditingController _phone = TextEditingController();

  bool _sending = false;
  Failure? _failure;
  int _cooldownSeconds = 0;
  int _cooldownToken = 0;

  @override
  void dispose() {
    _phone.dispose();
    super.dispose();
  }

  Future<void> _send() async {
    // ما يُرسَل صيغةُ الخادم دائماً؛ والعميلُ كتب رقمَه وحدَه.
    final phone = SaudiPhoneField.toServerFormat(_phone.text);
    setState(() {
      _sending = true;
      _failure = null;
    });

    try {
      final delivery = await ref
          .read(signInWithCodeProvider)
          .requestCode(phone: phone);
      ref
          .read(pendingSignInProvider.notifier)
          .start(phone: phone, delivery: delivery);
      if (mounted) context.goNamed(Routes.verifyCode);
    } on Failure catch (failure) {
      if (!mounted) return;
      setState(() {
        _failure = failure;
        _startCooldownIfServerSaidSo(failure);
      });
    } finally {
      if (mounted) setState(() => _sending = false);
    }
  }

  /// حدّ المعدّل (429) و«الرمز السابق ما زال حيّاً» يصلان بثوانٍ محدَّدة.
  void _startCooldownIfServerSaidSo(Failure failure) {
    final seconds = failure is ApiFailure ? failure.retryAfterSeconds : null;
    if (seconds == null) return;
    _cooldownSeconds = seconds;
    _cooldownToken += 1;
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final expired =
        ref.watch(sessionControllerProvider) == SessionState.expired;
    final palette = HarajPalette.of(context);

    // **الكحليُّ فوق والورقةُ تحت**: الهويّةُ (المضربُ والاسم) على الكحليّ،
    // وكلُّ ما يُقرأ ويُكتب في ورقةٍ فاتحة — الحقلُ لا يقع على خلفيّةٍ داكنة.
    // والورقةُ تمرَّر وحدَها على الهاتف القصير، والمضربُ ثابت.
    return Scaffold(
      backgroundColor: palette.gold,
      body: Stack(
        children: <Widget>[
          const Positioned.fill(child: AuthStripes()),
          SafeArea(
            bottom: false,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: <Widget>[
                Padding(
                  padding: const EdgeInsets.fromLTRB(20, 10, 20, 0),
                  child: Row(
                    children: <Widget>[
                      const _LivePill(),
                      const Spacer(),
                      _CloseButton(
                        onClose: () => context.go(Routes.homePath),
                        tooltip: l10n.signInDismiss,
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 6),
                AuthEntrance(child: AuthPaddle(raised: _sending)),
                const SizedBox(height: 12),
                AuthEntrance(
                  delay: const Duration(milliseconds: 80),
                  child: Column(
                    children: <Widget>[
                      Text(
                        l10n.splashHeadline,
                        textAlign: TextAlign.center,
                        style: const TextStyle(
                          fontFamily: HarajTheme.fontFamily,
                          fontSize: 24,
                          fontWeight: FontWeight.w700,
                          color: Colors.white,
                        ),
                      ),
                      const SizedBox(height: 2),
                      Text(
                        l10n.signInTagline,
                        textAlign: TextAlign.center,
                        style: const TextStyle(
                          fontFamily: HarajTheme.fontFamily,
                          fontSize: 13,
                          color: Color(0xFFC9D6E5),
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 18),
                Expanded(
                  child: AuthEntrance(
                    delay: const Duration(milliseconds: 160),
                    child: AuthSheet(
                      child: _sheetContent(l10n, palette, expired: expired),
                    ),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _sheetContent(
    AppLocalizations l10n,
    HarajPalette palette, {
    required bool expired,
  }) {
    return LayoutBuilder(
      builder: (context, box) => SingleChildScrollView(
        padding: EdgeInsets.fromLTRB(
          20,
          12,
          20,
          12 + MediaQuery.paddingOf(context).bottom,
        ),
        child: ConstrainedBox(
          constraints: BoxConstraints(minHeight: box.maxHeight - 24),
          child: IntrinsicHeight(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: <Widget>[
                Center(
                  child: Container(
                    width: 44,
                    height: 5,
                    decoration: BoxDecoration(
                      color: palette.navInactive,
                      borderRadius: BorderRadius.circular(3),
                    ),
                  ),
                ),
                const SizedBox(height: 14),
                const _AuctionRow(),
                _form(l10n, palette, expired: expired),
                const SizedBox(height: 14),
                const _Assurances(),
                const Spacer(),
                const SizedBox(height: 12),
                // «إغلاق» يرجع إلى الرئيسية لا يُغلق التطبيق.
                OutlinedButton(
                  onPressed: () => context.go(Routes.homePath),
                  style: OutlinedButton.styleFrom(
                    foregroundColor: palette.gold,
                    minimumSize: const Size.fromHeight(46),
                    side: BorderSide(color: palette.navInactive, width: 1.5),
                    shape: const StadiumBorder(),
                  ),
                  child: Text(
                    l10n.signInDismissGuest,
                    style: const TextStyle(
                      fontFamily: HarajTheme.fontFamily,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _form(
    AppLocalizations l10n,
    HarajPalette palette, {
    required bool expired,
  }) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      mainAxisSize: MainAxisSize.min,
      children: <Widget>[
        Text(
          l10n.signInTitle,
          style: TextStyle(
            fontFamily: HarajTheme.fontFamily,
            fontSize: 17,
            fontWeight: FontWeight.w700,
            color: palette.gold,
          ),
        ),
        const SizedBox(height: 4),
        if (expired) ...<Widget>[
          const SizedBox(height: 6),
          _ExpiredNotice(text: l10n.sessionExpiredNotice, palette: palette),
          const SizedBox(height: 10),
        ],
        Text(
          l10n.signInIntroFull,
          style: TextStyle(
            fontFamily: HarajTheme.fontFamily,
            fontSize: 13,
            color: palette.inkMuted,
            height: 1.55,
          ),
        ),
        const SizedBox(height: 12),
        SaudiPhoneField(
          controller: _phone,
          label: l10n.signInPhoneLabel,
          boxed: true,
          onChanged: (_) => setState(() {}),
        ),
        const SizedBox(height: 12),
        if (_sending)
          const SizedBox(
            height: 52,
            child: Center(child: CircularProgressIndicator()),
          )
        else if (_cooldownSeconds > 0)
          CooldownButton(
            label: l10n.signInSendCode,
            seconds: _cooldownSeconds,
            token: _cooldownToken,
            onPressed: SaudiPhoneField.isBlank(_phone.text) ? null : _send,
          )
        else
          FilledButton.icon(
            onPressed: SaudiPhoneField.isBlank(_phone.text) ? null : _send,
            icon: const Icon(Icons.sms_outlined, size: 19),
            label: Text(l10n.signInSendCode),
            style: FilledButton.styleFrom(
              backgroundColor: palette.gold,
              foregroundColor: Colors.white,
              disabledBackgroundColor: palette.gold.withValues(alpha: 0.35),
              disabledForegroundColor: Colors.white,
              minimumSize: const Size.fromHeight(52),
              shape: const StadiumBorder(),
              textStyle: const TextStyle(
                fontFamily: HarajTheme.fontFamily,
                fontWeight: FontWeight.w700,
                fontSize: 16,
              ),
            ),
          ),
        if (_failure != null) ...<Widget>[
          const SizedBox(height: 12),
          FailureView(failure: _failure!),
        ],
      ],
    );
  }
}

// ---------------------------------------------------------------------------
// أجزاءُ الشاشة.
// ---------------------------------------------------------------------------

/// ألوانُ التصميم خارج الباليت: الأخضرُ والكهرمانيّ بدرجاتهما في `docs/palette.md`.
const Color _emerald = Color(0xFF13795F);
const Color _emeraldSoft = Color(0xFF8FD1BD);
const Color _emeraldInk = Color(0xFF0B4A3B);
const Color _amberFill = Color(0xFFFBECC8);
const Color _amberLine = Color(0xFFE8C88A);
const Color _amberSolid = Color(0xFFB7791F);
const Color _amberInk = Color(0xFF6B4508);

/// المزادُ المعروض: الجاري إن وُجد، وإلّا القادم، وإلّا لا شيء.
({AuctionSummary auction, bool live})? _shownAuction(WidgetRef ref) {
  // `asData` لا `when`: يظهر حين تصل البيانات ويغيب قبلها وعند الفشل.
  final auctions = ref.watch(homeAuctionsProvider).asData?.value.value;
  if (auctions == null) return null;
  if (auctions.running.isNotEmpty) {
    return (auction: auctions.running.first, live: true);
  }
  if (auctions.upcoming.isNotEmpty) {
    return (auction: auctions.upcoming.first, live: false);
  }
  return null;
}

/// زرُّ الإغلاق على الكحليّ — يرجع إلى الرئيسية.
class _CloseButton extends StatelessWidget {
  const _CloseButton({required this.onClose, required this.tooltip});

  final VoidCallback onClose;
  final String tooltip;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.white.withValues(alpha: 0.08),
      shape: CircleBorder(
        side: BorderSide(color: Colors.white.withValues(alpha: 0.25)),
      ),
      child: IconButton(
        tooltip: tooltip,
        onPressed: onClose,
        icon: const Icon(Icons.close_rounded, color: Colors.white, size: 20),
      ),
    );
  }
}

/// «المزاد الجاري» وعددُ سيّاراته على الكحليّ، بنقطةٍ تنبض.
class _LivePill extends ConsumerWidget {
  const _LivePill();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = AppLocalizations.of(context);
    final shown = _shownAuction(ref);
    if (shown == null) return const SizedBox.shrink();
    final count = shown.auction.vehiclesCount;
    return Container(
      padding: const EdgeInsets.fromLTRB(12, 6, 6, 6),
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.10),
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: Colors.white.withValues(alpha: 0.18)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: <Widget>[
          _PulseDot(color: shown.live ? _emeraldSoft : _amberLine),
          const SizedBox(width: 8),
          Text(
            shown.live ? l10n.signInLiveAuction : l10n.signInNextAuction,
            style: const TextStyle(
              fontFamily: HarajTheme.fontFamily,
              fontSize: 12.5,
              fontWeight: FontWeight.w700,
              color: Colors.white,
            ),
          ),
          if (count != null) ...<Widget>[
            const SizedBox(width: 8),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 2),
              decoration: BoxDecoration(
                color: _emeraldSoft,
                borderRadius: BorderRadius.circular(999),
              ),
              child: Text(
                l10n.signInVehicleCount('$count'),
                style: const TextStyle(
                  fontFamily: HarajTheme.fontFamily,
                  fontSize: 12,
                  fontWeight: FontWeight.w700,
                  color: _emeraldInk,
                ),
              ),
            ),
          ],
        ],
      ),
    );
  }
}

/// نقطةٌ تنبض بحلقةٍ تتّسع وتخبو — وتسكن لمن أطفأ الحركة.
class _PulseDot extends StatefulWidget {
  const _PulseDot({required this.color});

  final Color color;

  @override
  State<_PulseDot> createState() => _PulseDotState();
}

class _PulseDotState extends State<_PulseDot>
    with SingleTickerProviderStateMixin {
  late final AnimationController _pulse = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: 1800),
  );

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (MediaQuery.disableAnimationsOf(context)) {
      _pulse.stop();
    } else if (!_pulse.isAnimating) {
      _pulse.repeat();
    }
  }

  @override
  void dispose() {
    _pulse.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => AnimatedBuilder(
    animation: _pulse,
    builder: (context, _) => Container(
      width: 8,
      height: 8,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        color: widget.color,
        boxShadow: <BoxShadow>[
          BoxShadow(
            color: widget.color.withValues(alpha: 0.6 * (1 - _pulse.value)),
            spreadRadius: 6 * _pulse.value,
          ),
        ],
      ),
    ),
  );
}

/// سطرُ «انتهت جلستك» داخل النموذج.
class _ExpiredNotice extends StatelessWidget {
  const _ExpiredNotice({required this.text, required this.palette});

  final String text;
  final HarajPalette palette;

  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
    decoration: BoxDecoration(
      color: Colors.white,
      borderRadius: BorderRadius.circular(14),
      border: Border.all(color: palette.navInactive),
    ),
    child: Row(
      children: <Widget>[
        Icon(Icons.schedule_rounded, size: 20, color: palette.gold),
        const SizedBox(width: 10),
        Expanded(
          child: Text(
            text,
            style: TextStyle(
              fontFamily: HarajTheme.fontFamily,
              fontSize: 13,
              color: palette.ink,
            ),
          ),
        ),
      ],
    ),
  );
}

/// **المزادُ** باسمه، و«ينتهي بعد:» بخاناتٍ للساعات والدقائق والثواني. T947
///
/// وحين لا مزادَ جارياً يقول متى يبدأ القادم، وحين لا هذا ولا ذاك **لا يُعرَض
/// شيء** ولا الفاصلُ تحته: صفٌّ فارغٌ في بابِ الدخول أسوأُ من لا صفّ.
class _AuctionRow extends ConsumerWidget {
  const _AuctionRow();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final palette = HarajPalette.of(context);
    final l10n = AppLocalizations.of(context);
    final shown = _shownAuction(ref);
    if (shown == null) return const SizedBox.shrink();
    final live = shown.live;
    final at = live ? shown.auction.endsAt : shown.auction.startsAt;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: <Widget>[
        Row(
          children: <Widget>[
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Text(
                    l10n.signInSessionLabel,
                    style: TextStyle(
                      fontFamily: HarajTheme.fontFamily,
                      fontSize: 11.5,
                      color: palette.inkMuted,
                    ),
                  ),
                  Text(
                    shown.auction.title,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(
                      fontFamily: HarajTheme.fontFamily,
                      fontSize: 15.5,
                      fontWeight: FontWeight.w700,
                      color: palette.gold,
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(width: 10),
            Column(
              crossAxisAlignment: CrossAxisAlignment.end,
              children: <Widget>[
                Text(
                  '${live ? l10n.signInEndsIn : l10n.signInStartsIn}:',
                  style: const TextStyle(
                    fontFamily: HarajTheme.fontFamily,
                    fontSize: 11.5,
                    fontWeight: FontWeight.w700,
                    color: Color(0xFF84560C),
                  ),
                ),
                const SizedBox(height: 4),
                _CountdownBoxes(at: at),
              ],
            ),
          ],
        ),
        Padding(
          padding: const EdgeInsets.symmetric(vertical: 14),
          child: Divider(height: 1, color: palette.navInactive),
        ),
      ],
    );
  }
}

/// العدّادُ خاناتٍ: الأيّامُ كهرمانيّة، والساعاتُ والدقائقُ كحليّة، والثواني
/// خضراء. **والحسابُ حسابُ [CountdownText] نفسُه** (`remainingWholeDays`
/// و`remainingDigits`) — العدُّ لا يُنسخ، الشكلُ وحده يختلف.
class _CountdownBoxes extends ConsumerStatefulWidget {
  const _CountdownBoxes({required this.at});

  final DateTime at;

  @override
  ConsumerState<_CountdownBoxes> createState() => _CountdownBoxesState();
}

class _CountdownBoxesState extends ConsumerState<_CountdownBoxes> {
  Timer? _ticker;

  @override
  void initState() {
    super.initState();
    final tick = ref.read(countdownTickProvider);
    if (tick != null) {
      _ticker = Timer.periodic(tick, (_) => setState(() {}));
    }
  }

  @override
  void dispose() {
    _ticker?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final palette = HarajPalette.of(context);
    final now = ref.watch(nowProvider)();
    final remaining = widget.at.toUtc().difference(now.toUtc());
    final days = remainingWholeDays(remaining);
    final parts = remainingDigits(remaining).split(':');

    Widget box(String text, Color fill, Color ink) => Container(
      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 3),
      decoration: BoxDecoration(
        color: fill,
        borderRadius: BorderRadius.circular(8),
      ),
      child: Text(
        text,
        style: TextStyle(
          fontFamily: HarajTheme.fontFamily,
          fontSize: 15,
          fontWeight: FontWeight.w700,
          color: ink,
        ),
      ),
    );
    Widget colon() => Padding(
      padding: const EdgeInsets.symmetric(horizontal: 2),
      child: Text(
        ':',
        style: TextStyle(fontWeight: FontWeight.w700, color: palette.gold),
      ),
    );

    // **`ltr` صراحةً** كما في [CountdownText]: الساعةُ تُقرأ من اليسار.
    return Directionality(
      textDirection: TextDirection.ltr,
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: <Widget>[
          if (days != null) ...<Widget>[
            Directionality(
              textDirection: TextDirection.rtl,
              child: box(l10n.countdownDaysOnly(days), _amberFill, _amberInk),
            ),
            const SizedBox(width: 4),
          ],
          box(parts[0], palette.gold, Colors.white),
          colon(),
          box(parts[1], palette.gold, Colors.white),
          colon(),
          box(parts[2], _emerald, Colors.white),
        ],
      ),
    );
  }
}

/// ثلاثةُ أسطرٍ تقول ما وراء الباب — **وكلُّها قواعدُ مبنيّةٌ في الخادم**:
/// المزايدةُ مغلقة، والدخولُ برمزٍ لمرّة (`apps/accounts/otp.py`)، والوديعةُ
/// تُسترَدّ بطلب (`money.RefundRequest`). لكلٍّ لونُه: الكحليّ والأخضر
/// والكهرمانيّ.
class _Assurances extends StatelessWidget {
  const _Assurances();

  @override
  Widget build(BuildContext context) {
    final strings = AppLocalizations.of(context);
    final palette = HarajPalette.of(context);
    final items = <(IconData, Color, String)>[
      (
        Icons.visibility_off_outlined,
        palette.gold,
        strings.signInAssuranceSealed,
      ),
      (Icons.key_rounded, _emerald, strings.signInAssuranceOtp),
      (
        Icons.verified_user_outlined,
        _amberSolid,
        strings.signInAssuranceDeposit,
      ),
    ];
    return Column(
      children: <Widget>[
        for (final (icon, colour, text) in items)
          Padding(
            padding: const EdgeInsets.symmetric(vertical: 4),
            child: Row(
              children: <Widget>[
                Icon(icon, size: 18, color: colour),
                const SizedBox(width: 10),
                Expanded(
                  child: Text(
                    text,
                    style: const TextStyle(
                      fontFamily: HarajTheme.fontFamily,
                      fontSize: 12.5,
                      fontWeight: FontWeight.w600,
                      color: Color(0xFF35577F),
                    ),
                  ),
                ),
              ],
            ),
          ),
      ],
    );
  }
}
