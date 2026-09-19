import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../app/providers.dart';
import '../../app/router.dart';
import '../../app/theme.dart';
import '../../domain/common/failure.dart';
import '../../domain/common/failure_codes.dart';
import '../../l10n/generated/app_localizations.dart';
import '../common/cooldown_button.dart';
import '../common/failure_view.dart';
import '../common/saudi_time.dart';
import 'auth_shell.dart';
import 'pending_sign_in.dart';
import 'session_controller.dart';

/// الخطوة الثانية: الرمز.
///
/// ثلاثة فروق يقيمها هذا الملف، وكلها **سلوك** لا نصّ — النصّ من الخادم دائماً:
///
/// 1. **فشل إرسال الرسالة ليس كوداً خاطئاً.** رمز `sms_undeliverable` يعني أنه
///    لا يوجد رمز أصلاً ليُكتب: تُبرز الشاشة «إعادة الإرسال» ولا تفرض مهلة
///    انتظار على عطل عندنا. شاشة تقول «الكود غلط» والبوابة ساقطة ترسل العميل
///    يعيد المحاولة إلى الأبد.
/// 2. **رقم بلا حساب يحتاج اسماً.** `registration_needs_name` يُرفَض قبل أن
///    يُستهلك الرمز، فيظهر حقل الاسم والرمز الذي بيد المستخدم ما زال صالحاً.
/// 3. **حدّ المعدّل مهلة معلومة.** 429 يصل بثوانيه، فيُعطَّل الزرّ ويُعرض العدّ.
///
/// ## والشكلُ صار شكلَ الخطوة الأولى. T948
///
/// طلبُ المالك (١٩ سبتمبر ٢٠٢٦): «حسّن تصميم الصفحة دي كمان، وحطّ اللوجو،
/// واعمل حركات وأنيميشن وإفكتس».
///
/// وكانت **شريطَ تطبيقٍ رماديّاً وحقلاً عارياً** بينما الخطوةُ التي قبلها
/// لوحةٌ ذهبيّةٌ فوق هالتين — بابٌ واحدٌ بوجهين، والعميلُ يعبره في ثانيتين
/// فيظنّ أنه خرج من التطبيق. فالهيكلُ الآن **مشتركٌ في [auth_shell]** لا
/// منسوخ: ما يظهر في إحداهما يظهر في الأخرى بحكم البناء.
///
/// وأربعُ حركاتٍ، **كلُّها تقول شيئاً**: دخولٌ متتابعٌ يقود العينَ من الشعار
/// إلى الحقل، وهالةٌ تتنفّس تقول إن الشاشةَ حيّة، و**اهتزازٌ عند رفض الرمز**
/// يُقرأ قبل أن تُقرأ الرسالة، وارتفاعٌ يتمدّد بهدوءٍ حين يظهر حقلُ الاسم.
/// وكلُّها تُطفأ لمن ضبط جهازَه على «تقليل الحركة».
class VerifyCodeScreen extends ConsumerStatefulWidget {
  const VerifyCodeScreen({super.key});

  @override
  ConsumerState<VerifyCodeScreen> createState() => _VerifyCodeScreenState();
}

class _VerifyCodeScreenState extends ConsumerState<VerifyCodeScreen> {
  final TextEditingController _code = TextEditingController();
  final TextEditingController _fullName = TextEditingController();

  bool _busy = false;
  bool _needsName = false;
  Failure? _failure;
  int _cooldownSeconds = 0;
  int _cooldownToken = 0;

  /// يتغيّر مع كلّ رفض، فيهتزّ الحقل. عدّادٌ لا `Failure` نفسُه: رفضان
  /// متتاليان بالسبب نفسِه كائنان متساويان، فلا يُلاحظ الثاني.
  int _rejections = 0;

  @override
  void initState() {
    super.initState();
    _cooldownSeconds =
        ref.read(pendingSignInProvider)?.delivery.resendAfterSeconds ?? 0;
  }

  @override
  void dispose() {
    _code.dispose();
    _fullName.dispose();
    super.dispose();
  }

  Future<void> _submit(String phone) async {
    setState(() {
      _busy = true;
      _failure = null;
    });

    try {
      await ref
          .read(signInWithCodeProvider)
          .submitCode(
            phone: phone,
            code: _code.text.trim(),
            fullName: _fullName.text.trim(),
          );
      ref.read(sessionControllerProvider.notifier).markSignedIn();
      ref.read(pendingSignInProvider.notifier).clear();
      if (mounted) context.goNamed(Routes.home);
    } on Failure catch (failure) {
      if (!mounted) return;
      setState(() {
        _failure = failure;
        _rejections += 1;
        if (failure is ApiFailure) {
          // الاسم مطلوب: يظهر الحقل، ورسالة الخادم فوقه تشرح لماذا.
          _needsName |= failure.code == FailureCodes.registrationNeedsName;
          _applyCooldown(failure);
        }
      });
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _resend(String phone) async {
    setState(() {
      _busy = true;
      _failure = null;
    });

    try {
      final delivery = await ref
          .read(signInWithCodeProvider)
          .requestCode(phone: phone);
      ref.read(pendingSignInProvider.notifier).renew(delivery);
      setState(() {
        _cooldownSeconds = delivery.resendAfterSeconds;
        _cooldownToken += 1;
      });
    } on Failure catch (failure) {
      if (!mounted) return;
      setState(() {
        _failure = failure;
        if (failure is ApiFailure) _applyCooldown(failure);
      });
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  /// مهلة الانتظار من الخادم وحده.
  ///
  /// `sms_undeliverable` مستثنى صراحةً: العطل عندنا، ومنع المستخدم من إعادة
  /// المحاولة عقوبة على شيء لم يفعله — وهو أيضاً الحالة الوحيدة التي تكون فيها
  /// إعادة المحاولة الفورية مفيدة فعلاً.
  void _applyCooldown(ApiFailure failure) {
    if (failure.code == FailureCodes.smsUndeliverable) return;
    final seconds = failure.retryAfterSeconds;
    if (seconds == null) return;
    _cooldownSeconds = seconds;
    _cooldownToken += 1;
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final pending = ref.watch(pendingSignInProvider);

    if (pending == null) {
      // لا رمز مُرسَل: هذه الشاشة بلا معنى، والموجّه يعيد إلى الخطوة الأولى.
      return const Scaffold(body: SizedBox.shrink());
    }

    final palette = HarajPalette.of(context);
    final theme = Theme.of(context);
    final expiresAt = SaudiTime.forDisplay(pending.delivery.expiresAt);

    return Scaffold(
      backgroundColor: palette.pageBackground,
      body: AuthBackdrop(
        child: SafeArea(
          child: Center(
            child: SingleChildScrollView(
              padding: const EdgeInsets.fromLTRB(20, 24, 20, 24),
              child: ConstrainedBox(
                constraints: const BoxConstraints(maxWidth: 400),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: <Widget>[
                    const AuthEntrance(
                      child: AuthBrand(
                        title: 'مزاد حراج واحد',
                        subtitle: 'خطوةٌ أخيرة — الرمزُ في رسالةٍ على جوّالك',
                        size: 66,
                      ),
                    ),
                    const SizedBox(height: 18),
                    AuthEntrance(
                      child: _SentTo(
                        phone: pending.phone,
                        expiresAt: expiresAt,
                        l10n: l10n,
                        onChangePhone: () {
                          ref.read(pendingSignInProvider.notifier).clear();
                          context.goNamed(Routes.signIn);
                        },
                      ),
                    ),
                    const SizedBox(height: 14),
                    AuthEntrance(
                      child: AuthPanel(
                        title: l10n.verifyTitle,
                        icon: Icons.mark_email_read_outlined,
                        child: _form(l10n, palette, theme, pending.phone),
                      ),
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
    ThemeData theme,
    String phone,
  ) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      mainAxisSize: MainAxisSize.min,
      children: <Widget>[
        // **الحقلُ يهتزّ حين يُرفض الرمز** — والاهتزازُ حول الحقل وحدَه لا
        // حول اللوحة: العينُ تُساق إلى ما يجب أن يُصحَّح.
        ShakeOnChange(
          trigger: _rejections == 0 ? null : _rejections,
          child: TextField(
            controller: _code,
            keyboardType: TextInputType.number,
            textAlign: TextAlign.center,
            textDirection: TextDirection.ltr,
            autofocus: true,
            autofillHints: const <String>[AutofillHints.oneTimeCode],
            // أرقامٌ فقط: الرمزُ أرقامٌ، وحرفٌ فيه يُرسَل ويُرفَض بعد رحلةِ
            // شبكة. ولا حدَّ لطوله هنا — طولُه قاعدةُ الخادم لا الشاشة.
            inputFormatters: <TextInputFormatter>[
              FilteringTextInputFormatter.digitsOnly,
            ],
            style: theme.textTheme.headlineSmall?.copyWith(
              color: Colors.white,
              fontWeight: FontWeight.w700,
              // تباعدٌ يجعل الستّةَ أرقامٍ تُقرأ رقماً رقماً عند المراجعة.
              letterSpacing: 8,
            ),
            decoration: InputDecoration(
              labelText: l10n.verifyCodeLabel,
              hintText: '••••••',
              hintStyle: TextStyle(
                color: palette.inkMuted.withValues(alpha: 0.5),
                letterSpacing: 8,
              ),
              filled: true,
              border: OutlineInputBorder(
                borderRadius: BorderRadius.circular(12),
              ),
            ),
            onChanged: (_) => setState(() {}),
            onSubmitted: (_) => _canSubmit ? _submit(phone) : null,
          ),
        ),
        if (_needsName) ...<Widget>[
          const SizedBox(height: 14),
          const AuthNotice(
            icon: Icons.person_add_alt_1_outlined,
            text: 'حسابٌ جديد — اكتب اسمَك كما في الهويّة لنُكمل التسجيل.',
          ),
          const SizedBox(height: 10),
          TextField(
            controller: _fullName,
            textCapitalization: TextCapitalization.words,
            decoration: InputDecoration(
              labelText: l10n.verifyFullNameLabel,
              filled: true,
              border: OutlineInputBorder(
                borderRadius: BorderRadius.circular(12),
              ),
            ),
            onChanged: (_) => setState(() {}),
          ),
        ],
        const SizedBox(height: 16),
        // تبديلٌ ناعمٌ بين الزرّ والدوّار: قفزةٌ بينهما تُقرأ وميضاً.
        AnimatedSwitcher(
          duration: const Duration(milliseconds: 180),
          child: _busy
              ? const Padding(
                  key: ValueKey<String>('busy'),
                  padding: EdgeInsets.symmetric(vertical: 8),
                  child: Center(child: CircularProgressIndicator()),
                )
              : FilledButton.icon(
                  key: const ValueKey<String>('submit'),
                  onPressed: _canSubmit ? () => _submit(phone) : null,
                  icon: const Icon(Icons.login_rounded, size: 18),
                  label: Text(l10n.verifySubmit),
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
        ),
        const SizedBox(height: 6),
        CooldownButton(
          label: l10n.verifyResend,
          seconds: _cooldownSeconds,
          token: _cooldownToken,
          onPressed: _busy ? null : () => _resend(phone),
        ),
        if (_failure != null) ...<Widget>[
          const SizedBox(height: 12),
          FailureView(failure: _failure!),
        ],
      ],
    );
  }

  bool get _canSubmit {
    if (_code.text.trim().isEmpty) return false;
    // الاسم شرط فقط بعد أن يطلبه الخادم لهذا الرقم.
    return !_needsName || _fullName.text.trim().isNotEmpty;
  }
}

/// «أرسلنا رمزاً إلى …» ومعه وقتُ الانتهاء وزرُّ تعديل الرقم.
///
/// **والرقمُ وزرُّ تعديله في مكانٍ واحد**: كان الزرُّ في ذيل الشاشة بعيداً عن
/// الرقم الذي يُصحِّحه، ومن أخطأ في رقمه يقرؤه في الأعلى ثمّ يبحث عن المخرج.
class _SentTo extends StatelessWidget {
  const _SentTo({
    required this.phone,
    required this.expiresAt,
    required this.l10n,
    required this.onChangePhone,
  });

  final String phone;
  final DateTime expiresAt;
  final AppLocalizations l10n;
  final VoidCallback onChangePhone;

  @override
  Widget build(BuildContext context) {
    final palette = HarajPalette.of(context);
    final theme = Theme.of(context);

    return Container(
      padding: const EdgeInsets.fromLTRB(14, 12, 14, 8),
      decoration: BoxDecoration(
        color: palette.cardSurface.withValues(alpha: 0.6),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: palette.navInactive.withValues(alpha: 0.3)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: <Widget>[
          Row(
            children: <Widget>[
              Icon(Icons.sms_outlined, size: 16, color: palette.goldOnDark),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  l10n.verifySentTo(phone),
                  style: theme.textTheme.bodySmall?.copyWith(
                    color: Colors.white,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 6),
          Row(
            children: <Widget>[
              Icon(
                Icons.timelapse_rounded,
                size: 15,
                color: palette.inkMuted,
              ),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  l10n.verifyExpiresAt(expiresAt),
                  style: theme.textTheme.bodySmall?.copyWith(
                    color: palette.inkMuted,
                  ),
                ),
              ),
              TextButton(
                onPressed: onChangePhone,
                style: TextButton.styleFrom(
                  foregroundColor: palette.goldOnDark,
                  padding: const EdgeInsets.symmetric(horizontal: 8),
                  minimumSize: const Size(0, 32),
                  tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                ),
                child: Text(l10n.verifyChangePhone),
              ),
            ],
          ),
        ],
      ),
    );
  }
}
