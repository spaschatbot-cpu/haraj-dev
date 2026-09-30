import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../app/providers.dart';
import '../../app/router.dart';
import '../../app/theme.dart';
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
/// * **أرقامُ المنصّة الآن** — ما يُزايَد عليه، وما هو قريب، وكم مزاداً مضى.
///   تُقرأ من نقطة الكتالوج نفسِها التي تقرؤها الرئيسيّة (`PhaseCounts`)، فلا
///   تقول هذه رقماً وتقول تلك غيرَه. ولا تُخترَع ولا تُكتب في الشيفرة: تُجلب،
///   وإن تعذّر الجلبُ **لا يُعرَض شيء** — رقمٌ تزيينيٌّ في شاشةِ دخولٍ هو
///   أوّلُ كذبةٍ يقرؤها العميل.
/// * **كيف يدخل** — برمزٍ لمرّة، لا بكلمة مرور. وهو ما يُسقط سؤالَ «نسيت كلمة
///   السرّ» من التطبيق كلِّه.
/// * **ما يحكم المزايدة** — سرّيّةُ المظروف، ووديعةٌ تُسترَدّ بطلبٍ منه.
///   وكلاهما قاعدةٌ مبنيّةٌ في الخادم لا وعدٌ تسويقيّ.
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

    // **تصميمُ المالك** (٣٠ سبتمبر ٢٠٢٦): شريطٌ علويّ (اسمُ المنظومة وزرُّ
    // الإغلاق)، والشعارُ في دائرةٍ بشارة V2، وكرتُ المزاد الجاري، وبطاقةُ
    // الدخول، وثلاثُ ميزات، و«المتابعة كزائر».
    //
    // **وبلا تمرير** (طلبُه الثاني في اليوم نفسه): أحجامٌ أصغر، وسقط الشريطُ
    // العلويّ وشارةُ V2 وسطرُ الحاشية تحت الزرّ.
    //
    // **وبقدرٍ وسط** بطلبه: «لا داتا كتير قوي تخلّي العميل يعمل سكرول، ولا
    // قليلة قوي». فالميزاتُ عناوينُ بلا شرح، وسقط من التصميم «مثال: 5…» (الخانةُ
    // تقوله) و«الدعم الفني» و«موثّق عبر النفاذ الوطني» — لا صفحةَ دعمٍ ولا ربطَ
    // بالنفاذ في النظام، ووعدٌ في شاشة الدخول أوّلُ ما يُكذَّب.
    return Scaffold(
      backgroundColor: palette.pageBackground,
      body: SafeArea(
        // **موزَّعةٌ على طول الشاشة لا مكوَّمة** (طلبُ المالك الثالث، ٣٠
        // سبتمبر): «التوزيع مريح للعين، مش مضغوطة في بعضها». فالفراغُ يُقسَم
        // بـ`Spacer` بين الكتل — أوسعُه فوق الشعار وتحت الميزات — ويتّسع مع
        // الهاتف الطويل ويضيق مع القصير، وتمريرٌ لا يقع إلا على شاشةٍ أقصرَ من
        // المحتوى نفسه.
        //
        // و`IntrinsicHeight` لأن `Spacer` داخل غلافٍ قابلٍ للتمرير يحسب الباقي
        // صفراً — الحيلةُ نفسُها التي في شاشة البدء.
        child: LayoutBuilder(
          builder: (context, box) => SingleChildScrollView(
            padding: const EdgeInsets.symmetric(horizontal: 20),
            child: Center(
              child: ConstrainedBox(
                constraints: BoxConstraints(
                  minHeight: box.maxHeight,
                  maxWidth: 440,
                ),
                child: IntrinsicHeight(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: <Widget>[
                      const SizedBox(height: 8),
                      // **بلا «منظومة المزادات v2»** بطلب المالك: زرُّ الإغلاق وحده.
                      Align(
                        alignment: AlignmentDirectional.centerEnd,
                        child: _CloseButton(
                          onClose: () => context.go(Routes.homePath),
                          tooltip: l10n.signInDismiss,
                        ),
                      ),
                      const Spacer(flex: 2),
                      AuthEntrance(
                        child: _BrandMark(
                          title: l10n.splashHeadline,
                          subtitle: l10n.signInTagline,
                        ),
                      ),
                      const Spacer(flex: 2),
                      const AuthEntrance(
                        delay: Duration(milliseconds: 90),
                        child: _LiveAuctionCard(),
                      ),
                      const SizedBox(height: 16),
                      AuthEntrance(
                        delay: const Duration(milliseconds: 170),
                        child: _Card(
                          padding: const EdgeInsets.all(18),
                          child: _form(l10n, palette, expired: expired),
                        ),
                      ),
                      const SizedBox(height: 16),
                      const AuthEntrance(
                        delay: Duration(milliseconds: 240),
                        child: _Assurances(),
                      ),
                      const Spacer(flex: 3),
                      // «إغلاق» يرجع إلى الرئيسية لا يُغلق التطبيق.
                      TextButton(
                        onPressed: () => context.go(Routes.homePath),
                        style: TextButton.styleFrom(
                          foregroundColor: palette.ink,
                        ),
                        child: Text(
                          l10n.signInDismissGuest,
                          style: const TextStyle(fontWeight: FontWeight.w700),
                        ),
                      ),
                      const SizedBox(height: 8),
                    ],
                  ),
                ),
              ),
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
        Row(
          children: <Widget>[
            _IconTile(icon: Icons.lock_outline_rounded, palette: palette),
            const SizedBox(width: 12),
            Expanded(
              child: Text(
                l10n.signInTitle,
                style: TextStyle(
                  fontFamily: HarajTheme.fontFamily,
                  fontSize: 16,
                  fontWeight: FontWeight.w700,
                  color: palette.ink,
                ),
              ),
            ),
          ],
        ),
        Padding(
          padding: const EdgeInsets.symmetric(vertical: 14),
          child: Divider(height: 1, color: palette.navInactive),
        ),
        if (expired) ...<Widget>[
          _ExpiredNotice(text: l10n.sessionExpiredNotice, palette: palette),
          const SizedBox(height: 12),
        ],
        Text(
          l10n.signInIntroFull,
          style: TextStyle(
            fontFamily: HarajTheme.fontFamily,
            fontSize: 12.5,
            color: palette.inkMuted,
            height: 1.5,
          ),
        ),
        const SizedBox(height: 14),
        SaudiPhoneField(
          controller: _phone,
          label: l10n.signInPhoneLabel,
          boxed: true,
          onChanged: (_) => setState(() {}),
        ),
        const SizedBox(height: 16),
        if (_sending)
          const Center(child: CircularProgressIndicator())
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
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(16),
              ),
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

/// بطاقةٌ بيضاء بحدٍّ فاتح — الوعاءُ الواحد لكرت المزاد والدخول والميزات.
class _Card extends StatelessWidget {
  const _Card({required this.child, this.padding = const EdgeInsets.all(14)});

  final Widget child;
  final EdgeInsets padding;

  @override
  Widget build(BuildContext context) {
    final palette = HarajPalette.of(context);
    return Container(
      padding: padding,
      decoration: BoxDecoration(
        color: palette.cardSurface,
        borderRadius: BorderRadius.circular(22),
        border: Border.all(color: palette.navInactive.withValues(alpha: 0.7)),
        boxShadow: <BoxShadow>[
          BoxShadow(
            color: palette.ink.withValues(alpha: 0.05),
            blurRadius: 16,
            offset: const Offset(0, 6),
          ),
        ],
      ),
      child: child,
    );
  }
}

class _IconTile extends StatelessWidget {
  const _IconTile({required this.icon, required this.palette});

  final IconData icon;
  final HarajPalette palette;

  @override
  Widget build(BuildContext context) => Container(
    width: 34,
    height: 34,
    decoration: BoxDecoration(
      color: palette.gold.withValues(alpha: 0.08),
      borderRadius: BorderRadius.circular(12),
    ),
    child: Icon(icon, size: 18, color: palette.gold),
  );
}

/// زرُّ الإغلاق — يرجع إلى الرئيسية.
class _CloseButton extends StatelessWidget {
  const _CloseButton({required this.onClose, required this.tooltip});

  final VoidCallback onClose;
  final String tooltip;

  @override
  Widget build(BuildContext context) {
    final palette = HarajPalette.of(context);
    return Material(
      color: palette.cardSurface,
      shape: CircleBorder(side: BorderSide(color: palette.navInactive)),
      child: IconButton(
        tooltip: tooltip,
        onPressed: onClose,
        visualDensity: VisualDensity.compact,
        icon: Icon(Icons.close_rounded, color: palette.ink, size: 20),
      ),
    );
  }
}

/// الشعارُ في دائرةٍ داكنة بإطارٍ أبيض، ثم الاسمُ وسطرُ التعريف — بلا شارة V2
/// بطلب المالك.
class _BrandMark extends StatelessWidget {
  const _BrandMark({required this.title, required this.subtitle});

  final String title;
  final String subtitle;

  @override
  Widget build(BuildContext context) {
    final palette = HarajPalette.of(context);
    return Column(
      children: <Widget>[
        Container(
          width: 72,
          height: 72,
          padding: const EdgeInsets.all(15),
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            gradient: LinearGradient(
              begin: Alignment.topRight,
              end: Alignment.bottomLeft,
              colors: <Color>[
                Color.alphaBlend(
                  palette.gold.withValues(alpha: 0.25),
                  palette.heroTop,
                ),
                palette.heroBottom,
              ],
            ),
            border: Border.all(color: Colors.white, width: 3),
            boxShadow: <BoxShadow>[
              BoxShadow(
                color: palette.ink.withValues(alpha: 0.22),
                blurRadius: 14,
                offset: const Offset(0, 6),
              ),
            ],
          ),
          child: Image.asset(
            'assets/images/logo.png',
            fit: BoxFit.contain,
            errorBuilder: (_, _, _) =>
                const Icon(Icons.gavel_rounded, color: Colors.white),
          ),
        ),
        const SizedBox(height: 12),
        Text(
          title,
          textAlign: TextAlign.center,
          style: TextStyle(
            fontFamily: HarajTheme.fontFamily,
            fontSize: 21,
            fontWeight: FontWeight.w700,
            color: palette.ink,
          ),
        ),
        const SizedBox(height: 4),
        Text(
          subtitle,
          textAlign: TextAlign.center,
          style: TextStyle(
            fontFamily: HarajTheme.fontFamily,
            fontSize: 13.5,
            color: palette.inkMuted,
          ),
        ),
      ],
    );
  }
}

/// سطرُ «انتهت جلستك» داخل بطاقة الدخول.
class _ExpiredNotice extends StatelessWidget {
  const _ExpiredNotice({required this.text, required this.palette});

  final String text;
  final HarajPalette palette;

  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
    decoration: BoxDecoration(
      color: palette.pageBackground,
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

/// **المزادُ الجاري** — اسمُه وكم سيّارةً فيه وكم بقي على إغلاقه. T947
///
/// وحين لا مزادَ جارياً يقول متى يبدأ القادم، وحين لا هذا ولا ذاك **لا يُعرَض
/// شيء**: كرتٌ فارغٌ في بابِ الدخول أسوأُ من لا كرت. والمصدرُ
/// `homeAuctionsProvider` نفسُه الذي تقرؤه الرئيسيّة.
///
/// والتصميمُ يكتب «رقم الجلسة: مزاد 54»، والكرتُ لا يحمل رقمَ المزاد — يحمل
/// اسمَه («مزاد 54» أصلاً في بيانات v1 المنقولة)، فيُعرض الاسم.
class _LiveAuctionCard extends ConsumerWidget {
  const _LiveAuctionCard();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final palette = HarajPalette.of(context);
    final l10n = AppLocalizations.of(context);

    // `asData` لا `when`: الكرتُ يظهر حين تصل البيانات ويغيب قبلها وعند الفشل.
    final auctions = ref.watch(homeAuctionsProvider).asData?.value.value;
    if (auctions == null) return const SizedBox.shrink();

    final running = auctions.running.isEmpty ? null : auctions.running.first;
    final next = auctions.upcoming.isEmpty ? null : auctions.upcoming.first;
    final shown = running ?? next;
    if (shown == null) return const SizedBox.shrink();
    final live = running != null;

    return _Card(
      padding: const EdgeInsets.fromLTRB(16, 14, 16, 14),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: <Widget>[
          Row(
            children: <Widget>[
              Container(
                width: 9,
                height: 9,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: live ? const Color(0xFF10B981) : palette.gold,
                ),
              ),
              const SizedBox(width: 8),
              Text(
                live ? l10n.signInLiveAuction : l10n.signInNextAuction,
                style: TextStyle(
                  fontFamily: HarajTheme.fontFamily,
                  fontSize: 14,
                  fontWeight: FontWeight.w700,
                  color: palette.ink,
                ),
              ),
              const Spacer(),
              if (shown.vehiclesCount != null)
                Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 12,
                    vertical: 5,
                  ),
                  decoration: BoxDecoration(
                    color: palette.gold.withValues(alpha: 0.08),
                    borderRadius: BorderRadius.circular(10),
                    border: Border.all(
                      color: palette.gold.withValues(alpha: 0.25),
                    ),
                  ),
                  child: Text(
                    l10n.signInVehicleCount('${shown.vehiclesCount}'),
                    style: TextStyle(
                      fontFamily: HarajTheme.fontFamily,
                      fontSize: 13,
                      fontWeight: FontWeight.w700,
                      color: palette.gold,
                    ),
                  ),
                ),
            ],
          ),
          Padding(
            padding: const EdgeInsets.symmetric(vertical: 12),
            child: Divider(height: 1, color: palette.navInactive),
          ),
          Row(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: <Widget>[
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Text(
                      l10n.signInSessionLabel,
                      style: TextStyle(
                        fontFamily: HarajTheme.fontFamily,
                        fontSize: 12,
                        color: palette.inkMuted,
                      ),
                    ),
                    Text(
                      shown.title,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: TextStyle(
                        fontFamily: HarajTheme.fontFamily,
                        fontSize: 16,
                        fontWeight: FontWeight.w700,
                        color: palette.ink,
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 10),
              Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: 10,
                  vertical: 7,
                ),
                decoration: BoxDecoration(
                  color: const Color(0xFFFFFBEB),
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(color: const Color(0xFFFDE68A)),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: <Widget>[
                    const Icon(
                      Icons.schedule_rounded,
                      size: 15,
                      color: Color(0xFFB45309),
                    ),
                    const SizedBox(width: 5),
                    Text(
                      '${live ? l10n.signInEndsIn : l10n.signInStartsIn}: ',
                      style: const TextStyle(
                        fontFamily: HarajTheme.fontFamily,
                        fontSize: 12,
                        color: Color(0xFFB45309),
                      ),
                    ),
                    // العدّادُ نفسُه الذي على كروت الرئيسيّة — لا نسخةٌ ثانية.
                    CountdownText(
                      at: live ? shown.endsAt : shown.startsAt,
                      target: live
                          ? CountdownTarget.end
                          : CountdownTarget.start,
                      digital: true,
                      style: const TextStyle(
                        fontFamily: HarajTheme.fontFamily,
                        fontSize: 13,
                        fontWeight: FontWeight.w700,
                        color: Color(0xFF92400E),
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

/// ثلاثةُ أسطرٍ تقول ما وراء الباب — **وكلُّها قواعدُ مبنيّةٌ في الخادم**:
/// المزايدةُ مغلقة، والدخولُ برمزٍ لمرّة (`apps/accounts/otp.py`)، والوديعةُ
/// تُسترَدّ بطلب (`money.RefundRequest`). عناوينُ بلا شرح — القدرُ الوسط.
class _Assurances extends StatelessWidget {
  const _Assurances();

  @override
  Widget build(BuildContext context) {
    final strings = AppLocalizations.of(context);
    final palette = HarajPalette.of(context);
    final items = <(IconData, String)>[
      (Icons.visibility_off_outlined, strings.signInAssuranceSealed),
      (Icons.key_rounded, strings.signInAssuranceOtp),
      (Icons.verified_user_outlined, strings.signInAssuranceDeposit),
    ];
    return _Card(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
      child: Column(
        children: <Widget>[
          for (final (icon, text) in items)
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 6),
              child: Row(
                children: <Widget>[
                  Icon(icon, size: 18, color: palette.gold),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Text(
                      text,
                      style: TextStyle(
                        fontFamily: HarajTheme.fontFamily,
                        fontSize: 12.5,
                        fontWeight: FontWeight.w600,
                        color: palette.ink,
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
}
