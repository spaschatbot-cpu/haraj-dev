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
    final theme = Theme.of(context);

    // **لوحةٌ في وسط الصفحة لا صفحةٌ كاملة** — بطلب المالك في ٩ سبتمبر ٢٠٢٦.
    //
    // الشاشةُ الكاملة تقول «هذه محطّتُك الآن»، وتسجيلُ الدخول ليس محطّة: هو
    // بابٌ يُفتح في طريقٍ إلى شيءٍ آخر (مفضّلة، مشاركات، مزايدة). واللوحةُ
    // فوق أرضيّةٍ ساكنة تقول ذلك: افعل أو أغلق وارجع.
    //
    // **ولا `AppBar`**: زرُّ الرجوع فيه مقبضٌ ثانٍ لما يفعله «إغلاق» أسفل
    // اللوحة، ومقبضان لفعلٍ واحدٍ في شاشةٍ من حقلٍ واحد ضجيج.
    return Scaffold(
      backgroundColor: palette.pageBackground,
      // الأرضيّةُ والشعارُ واللوحةُ **مشتركةٌ مع شاشة الرمز** ([AuthBackdrop]
      // و[AuthBrand] و[AuthPanel] في `auth_shell.dart`). كانت هنا نسخةٌ
      // خاصّةٌ منها، ونسختان من هيكلٍ واحدٍ تفترقان عند أوّل تعديل — فيعبر
      // العميلُ من خطوةٍ إلى خطوةٍ فيظنّ أنه خرج من التطبيق. T948
      body: AuthBackdrop(
        child: SafeArea(
          child: Center(
            child: SingleChildScrollView(
              padding: const EdgeInsets.fromLTRB(20, 24, 20, 24),
              child: ConstrainedBox(
                // **٤٠٠ لا عرضُ الشاشة**: حقلٌ واحد ممتدٌّ على شاشةٍ عريضة
                // يُقرأ نموذجاً طويلاً، وهو حقلٌ واحد.
                constraints: const BoxConstraints(maxWidth: 400),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: <Widget>[
                    // دخولٌ متتابع: الشعارُ ثمّ الشريطُ ثمّ اللوحة. تأخيرٌ
                    // يقود العينَ من أعلى إلى الحقل، لا ثلاثُ ودجاتٍ تظهر
                    // معاً.
                    const AuthEntrance(
                      child: AuthBrand(
                        title: 'مزاد حراج واحد',
                        subtitle: 'مزايدةٌ مغلقة على سيّارات المزاد — من جوّالك',
                      ),
                    ),
                    const SizedBox(height: 18),
                    const AuthEntrance(
                      delay: Duration(milliseconds: 90),
                      child: _LiveAuctionStrip(),
                    ),
                    const SizedBox(height: 14),
                    AuthEntrance(
                      delay: const Duration(milliseconds: 170),
                      child: AuthPanel(
                        title: l10n.signInTitle,
                        icon: Icons.lock_outline_rounded,
                        child: _form(l10n, palette, theme, expired: expired),
                      ),
                    ),
                    const SizedBox(height: 14),
                    AuthEntrance(
                      delay: const Duration(milliseconds: 240),
                      child: _Assurances(palette: palette, theme: theme),
                    ),
                    const SizedBox(height: 4),
                    // **«إغلاق» يرجع إلى الرئيسية لا يُغلق التطبيق**:
                    // اللوحةُ مسارٌ في الشجرة لا نافذةٌ فوقها، ولا شيء
                    // تحتها يُكشف بالإغلاق.
                    TextButton(
                      onPressed: () => context.go(Routes.homePath),
                      style: TextButton.styleFrom(
                        foregroundColor: palette.inkMuted,
                      ),
                      child: Text(l10n.signInDismiss),
                    ),
                  ],
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
    HarajPalette palette,
    ThemeData theme, {
    required bool expired,
  }) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      mainAxisSize: MainAxisSize.min,
      children: <Widget>[
        if (expired) ...<Widget>[
          AuthNotice(
            icon: Icons.schedule_rounded,
            text: l10n.sessionExpiredNotice,
          ),
          const SizedBox(height: 14),
        ],
        Text(
          l10n.signInIntro,
          style: theme.textTheme.bodyMedium?.copyWith(color: palette.inkMuted),
        ),
        const SizedBox(height: 14),
        SaudiPhoneField(
          controller: _phone,
          label: l10n.signInPhoneLabel,
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
            icon: const Icon(Icons.sms_outlined, size: 18),
            label: Text(l10n.signInSendCode),
            style: FilledButton.styleFrom(
              backgroundColor: palette.goldDeep,
              foregroundColor: Colors.white,
              disabledBackgroundColor: palette.navInactive.withValues(
                alpha: 0.45,
              ),
              padding: const EdgeInsets.symmetric(vertical: 15),
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(12),
              ),
              textStyle: const TextStyle(
                fontFamily: HarajTheme.fontFamily,
                fontWeight: FontWeight.w700,
                fontSize: 15,
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
// أجزاءُ الشاشة. T947
// ---------------------------------------------------------------------------

/// **المزادُ الجاري** — لا ثلاثةُ عدّادات. T947
///
/// كانت هنا ثلاثةُ صناديق: «تُزايَد الآن ٣٤ · قريباً ٠ · مزادات سابقة ١٠٣٧».
/// وقرارُ المالك (١٩ سبتمبر ٢٠٢٦): «الغِ دول واستبدلهم بحاجة أحسن».
///
/// **وكانت أرقاماً لا خبراً.** «١٠٣٧ مزاداً سابقاً» ماضٍ لا يدعو أحداً إلى
/// شيء، و«قريباً ٠» صفرٌ يُقرأ نقصاً وهو حقيقةٌ عاديّة بين مزادين. ومن يقف
/// على باب الدخول يسأل سؤالاً واحداً: **«فيه إيه دلوقتي؟»**
///
/// فصار شريطاً واحداً يجيبه: اسمُ المزاد الجاري، وكم سيّارةً فيه، **وكم بقي
/// على إغلاقه — عدّاداً يتحرّك**. وحين لا مزادَ جارياً يقول متى يبدأ القادم،
/// وحين لا هذا ولا ذاك **لا يُعرَض شيء**: شريطٌ فارغٌ في بابِ الدخول أسوأُ من
/// لا شريط.
///
/// والمصدرُ `homeAuctionsProvider` نفسُه الذي تقرؤه الرئيسيّة — فلا يقول هذا
/// مزاداً وتقول تلك غيرَه.
class _LiveAuctionStrip extends ConsumerWidget {
  const _LiveAuctionStrip();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final palette = HarajPalette.of(context);
    final theme = Theme.of(context);

    // `asData` لا `when`: الشريطُ يظهر حين تصل البيانات ويغيب قبلها وعند
    // الفشل — ولا رسالةَ خطأٍ في بابِ الدخول عن شيءٍ تزيينيّ.
    final auctions = ref.watch(homeAuctionsProvider).asData?.value.value;
    if (auctions == null) return const SizedBox.shrink();

    final running = auctions.running.isEmpty ? null : auctions.running.first;
    final next = auctions.upcoming.isEmpty ? null : auctions.upcoming.first;
    final shown = running ?? next;
    if (shown == null) return const SizedBox.shrink();

    final live = running != null;
    final accent = live ? palette.goldOnDark : Colors.white;

    return Container(
      padding: const EdgeInsets.fromLTRB(14, 12, 14, 12),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(16),
        gradient: LinearGradient(
          begin: Alignment.topRight,
          end: Alignment.bottomLeft,
          colors: <Color>[
            palette.heroTop.withValues(alpha: 0.95),
            palette.heroBottom.withValues(alpha: 0.95),
          ],
        ),
        border: Border.all(
          color: accent.withValues(alpha: live ? 0.45 : 0.22),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: <Widget>[
          Row(
            children: <Widget>[
              // نقطةٌ تقول «حيّ» — ولا تُعرَض للمجدول، فالمجدولُ ليس حيّاً.
              if (live) ...<Widget>[
                Container(
                  width: 8,
                  height: 8,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: palette.goldOnDark,
                    boxShadow: <BoxShadow>[
                      BoxShadow(
                        color: palette.goldOnDark.withValues(alpha: 0.7),
                        blurRadius: 8,
                      ),
                    ],
                  ),
                ),
                const SizedBox(width: 7),
              ],
              Text(
                live ? 'المزاد الجاري' : 'المزاد القادم',
                style: theme.textTheme.labelMedium?.copyWith(
                  color: accent,
                  fontWeight: FontWeight.w700,
                ),
              ),
              const Spacer(),
              if (shown.vehiclesCount != null)
                Text(
                  '${shown.vehiclesCount} سيّارة',
                  textDirection: TextDirection.rtl,
                  style: theme.textTheme.labelMedium?.copyWith(
                    color: Colors.white.withValues(alpha: 0.85),
                  ),
                ),
            ],
          ),
          const SizedBox(height: 7),
          Text(
            shown.title,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: theme.textTheme.titleSmall?.copyWith(
              color: Colors.white,
              fontWeight: FontWeight.w700,
            ),
          ),
          const SizedBox(height: 8),
          Row(
            children: <Widget>[
              Icon(
                live ? Icons.timer_outlined : Icons.event_outlined,
                size: 15,
                color: Colors.white.withValues(alpha: 0.75),
              ),
              const SizedBox(width: 6),
              // العدّادُ نفسُه الذي على كروت الرئيسيّة — لا نسخةٌ ثانية منه.
              CountdownText(
                at: live ? shown.endsAt : shown.startsAt,
                target: live ? CountdownTarget.end : CountdownTarget.start,
                style: theme.textTheme.bodySmall?.copyWith(
                  color: Colors.white.withValues(alpha: 0.9),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

/// ثلاثةُ أسطرٍ تقول ما وراء الباب — **وكلُّها قواعدُ مبنيّةٌ في الخادم**.
///
/// لا وعدٌ تسويقيّ: المزايدةُ مغلقةٌ فعلاً (لا يرى أحدٌ مبلغَ غيره)، والدخولُ
/// برمزٍ لمرّةٍ لا بكلمة مرور (`apps/accounts/otp.py`)، والوديعةُ تُسترَدّ
/// بطلبٍ من التطبيق (`money.RefundRequest`).
class _Assurances extends StatelessWidget {
  const _Assurances({required this.palette, required this.theme});

  final HarajPalette palette;
  final ThemeData theme;

  static const List<(IconData, String)> _items = <(IconData, String)>[
    (Icons.visibility_off_outlined, 'مزايدةٌ مغلقة: لا يرى أحدٌ مبلغك'),
    (Icons.password_rounded, 'بلا كلمة مرور — رمزٌ لمرّةٍ واحدة'),
    (Icons.savings_outlined, 'التأمينُ وديعةٌ تُسترَدّ بطلبٍ منك'),
  ];

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(vertical: 12, horizontal: 14),
      decoration: BoxDecoration(
        color: palette.cardSurface.withValues(alpha: 0.5),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: palette.navInactive.withValues(alpha: 0.3)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: <Widget>[
          for (var index = 0; index < _items.length; index += 1) ...<Widget>[
            Row(
              children: <Widget>[
                Icon(_items[index].$1, size: 16, color: palette.goldOnDark),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    _items[index].$2,
                    style: theme.textTheme.bodySmall?.copyWith(
                      color: palette.inkMuted,
                      height: 1.5,
                    ),
                  ),
                ),
              ],
            ),
            if (index != _items.length - 1) const SizedBox(height: 9),
          ],
        ],
      ),
    );
  }
}
