import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../app/providers.dart';
import '../../app/router.dart';
import '../../app/theme.dart';
import '../../domain/common/failure.dart';
import '../../domain/common/failure_codes.dart';
import '../../domain/profile/entities/customer_profile.dart';
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
/// **ثمّ صار الزجاجَ الأبيض (٣ أكتوبر ٢٠٢٦)** حين بُنيت شاشةُ الدخول به
/// داخل ملفّها: فبقي من [auth_shell] الحركاتُ وحدَها (`AuthEntrance`
/// و`ShakeOnChange`)، والشعارُ والبطاقاتُ هنا على مثال شاشة الدخول.
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

  bool _busy = false;
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
          .submitCode(phone: phone, code: _code.text.trim());

      // **الرمزُ وحدَه، ثمّ القرار** — ترتيبُ v1 وطلبُ المالك (٢٨ سبتمبر ٢٠٢٦):
      // مكتملٌ ⇐ الرئيسية على طول؛ جديدٌ أو ناقصٌ ⇐ «أكمل تسجيلك». وكان الاسمُ
      // يُطلب هنا بعد رفض `registration_needs_name` للحساب الجديد وحده، فيبقى
      // حسابٌ منقولٌ من v1 باسمٍ فارغ ناقصاً بلا أن يُسأل.
      //
      // وما ينقص جوابُ الخادم (`registrationMissing`). وفشلُ السؤال لا يُسقط
      // الدخول: الجلسةُ قائمة، والرئيسيةُ أصدقُ من شاشة خطأٍ بعد رمزٍ صحيح.
      final profile = await ref
          .read(manageProfileProvider)
          .load()
          .then<CustomerProfile?>((snapshot) => snapshot.value)
          .catchError((Object _) => null);
      if (!mounted) return;

      // **والدخولُ يُعلَن بعد السؤال لا قبله.** `markSignedIn` يوقظ الموجّه،
      // وقاعدتُه تردّ كلَّ داخلٍ عن مسار الدخول إلى الرئيسية فوراً — فكانت هذه
      // الشاشةُ تُغلَق قبل أن يعود جوابُ «ما ينقص»، و`mounted` بعدها كاذبة، فيبقى
      // الحسابُ الجديدُ في الرئيسية بلا اسم. قِيس في نسخة الويب من التطبيق: رمزٌ
      // صحيح ⇐ الرئيسية، و`GET /profile/` يعود بثلاثة نواقص بعد أن أُغلقت الشاشة.
      // والرموزُ محفوظةٌ في `submitCode`، فالسؤالُ يعمل قبل الإعلان.
      ref.read(sessionControllerProvider.notifier).markSignedIn();
      ref.read(pendingSignInProvider.notifier).clear();
      if (profile != null && !profile.isRegistered) {
        context.goNamed(Routes.completeRegistration);
      } else {
        context.goNamed(Routes.home);
      }
    } on Failure catch (failure) {
      if (!mounted) return;
      setState(() {
        _failure = failure;
        _rejections += 1;
        if (failure is ApiFailure) _applyCooldown(failure);
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
      return const Scaffold(
        backgroundColor: Colors.transparent,
        body: SizedBox.shrink(),
      );
    }

    final palette = HarajPalette.of(context);
    final expiresAt = SaudiTime.forDisplay(pending.delivery.expiresAt);

    // **تصميمُ الزجاج الأبيض بطلب المالك (٣ أكتوبر ٢٠٢٦)** — وجهُ الخطوة
    // الأولى نفسُه: الشعارُ في دائرته ثمّ بطاقتان بيضاوان على أرضيّة
    // `GlassBackdrop` العامّة. وسقطت اللوحةُ الداكنةُ بشريطها وهالتا
    // `AuthBackdrop` — بابٌ واحدٌ بوجهٍ واحد.
    //
    // والفراغُ يُقسَم بـ`Spacer` كما في شاشة الدخول فلا تمريرَ على هاتفٍ
    // عاديّ، و`IntrinsicHeight` لأن `Spacer` داخل غلافٍ قابلٍ للتمرير يحسب
    // الباقي صفراً. والتمريرُ باقٍ لشاشةٍ أقصرَ من المحتوى أو لوحةِ مفاتيحَ
    // مفتوحة.
    return Scaffold(
      backgroundColor: Colors.transparent,
      body: SafeArea(
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
                      const Spacer(flex: 2),
                      AuthEntrance(
                        child: _BrandMark(
                          title: l10n.splashHeadline,
                          subtitle: l10n.verifyTagline,
                        ),
                      ),
                      const Spacer(flex: 2),
                      AuthEntrance(
                        delay: const Duration(milliseconds: 90),
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
                      const SizedBox(height: 16),
                      AuthEntrance(
                        delay: const Duration(milliseconds: 170),
                        child: _Card(
                          padding: const EdgeInsets.all(18),
                          child: _form(l10n, palette, pending.phone),
                        ),
                      ),
                      const Spacer(flex: 3),
                      const SizedBox(height: 16),
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

  Widget _form(AppLocalizations l10n, HarajPalette palette, String phone) {
    final border = OutlineInputBorder(
      borderRadius: BorderRadius.circular(16),
      borderSide: BorderSide(color: palette.navInactive),
    );
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      mainAxisSize: MainAxisSize.min,
      children: <Widget>[
        Row(
          children: <Widget>[
            _IconTile(icon: Icons.mark_email_read_outlined, palette: palette),
            const SizedBox(width: 12),
            Expanded(
              child: Text(
                l10n.verifyTitle,
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
            style: TextStyle(
              fontFamily: HarajTheme.fontFamily,
              fontSize: 22,
              color: palette.ink,
              fontWeight: FontWeight.w700,
              // تباعدٌ يجعل الستّةَ أرقامٍ تُقرأ رقماً رقماً عند المراجعة.
              letterSpacing: 8,
            ),
            decoration: InputDecoration(
              labelText: l10n.verifyCodeLabel,
              labelStyle: TextStyle(
                fontFamily: HarajTheme.fontFamily,
                color: palette.inkMuted,
              ),
              floatingLabelStyle: TextStyle(
                fontFamily: HarajTheme.fontFamily,
                color: palette.gold,
                fontWeight: FontWeight.w600,
              ),
              hintText: '••••••',
              hintStyle: TextStyle(
                color: palette.inkMuted.withValues(alpha: 0.5),
                letterSpacing: 8,
              ),
              filled: true,
              fillColor: palette.cardSurface,
              contentPadding: const EdgeInsets.symmetric(
                horizontal: 16,
                vertical: 16,
              ),
              border: border,
              enabledBorder: border,
              focusedBorder: border.copyWith(
                borderSide: BorderSide(color: palette.gold, width: 1.6),
              ),
            ),
            onChanged: (_) => setState(() {}),
            onSubmitted: (_) => _canSubmit ? _submit(phone) : null,
          ),
        ),
        const SizedBox(height: 16),
        // تبديلٌ ناعمٌ بين الزرّ والدوّار: قفزةٌ بينهما تُقرأ وميضاً.
        AnimatedSwitcher(
          duration: const Duration(milliseconds: 180),
          child: _busy
              ? const SizedBox(
                  key: ValueKey<String>('busy'),
                  height: 52,
                  child: Center(child: CircularProgressIndicator()),
                )
              : FilledButton.icon(
                  key: const ValueKey<String>('submit'),
                  onPressed: _canSubmit ? () => _submit(phone) : null,
                  icon: const Icon(Icons.login_rounded, size: 19),
                  label: Text(l10n.verifySubmit),
                  style: FilledButton.styleFrom(
                    backgroundColor: palette.gold,
                    foregroundColor: Colors.white,
                    disabledBackgroundColor: palette.gold.withValues(
                      alpha: 0.35,
                    ),
                    disabledForegroundColor: Colors.white,
                    minimumSize: const Size.fromHeight(52),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(16),
                    ),
                    textStyle: const TextStyle(
                      fontFamily: HarajTheme.fontFamily,
                      fontWeight: FontWeight.w700,
                      fontSize: 15,
                    ),
                  ),
                ),
        ),
        const SizedBox(height: 8),
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

  // الرمزُ وحدَه شرطُ الإرسال — البياناتُ في «أكمل تسجيلك» بعده.
  bool get _canSubmit => _code.text.trim().isNotEmpty;
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

    return _Card(
      padding: const EdgeInsets.fromLTRB(16, 14, 12, 10),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: <Widget>[
          Row(
            children: <Widget>[
              _IconTile(icon: Icons.sms_outlined, palette: palette),
              const SizedBox(width: 12),
              Expanded(
                child: Text(
                  l10n.verifySentTo(phone),
                  style: TextStyle(
                    fontFamily: HarajTheme.fontFamily,
                    fontSize: 13.5,
                    fontWeight: FontWeight.w600,
                    color: palette.ink,
                  ),
                ),
              ),
            ],
          ),
          Padding(
            padding: const EdgeInsetsDirectional.fromSTEB(0, 10, 4, 6),
            child: Divider(height: 1, color: palette.navInactive),
          ),
          Row(
            children: <Widget>[
              Icon(Icons.timelapse_rounded, size: 16, color: palette.inkMuted),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  l10n.verifyExpiresAt(expiresAt),
                  style: TextStyle(
                    fontFamily: HarajTheme.fontFamily,
                    fontSize: 12.5,
                    color: palette.inkMuted,
                  ),
                ),
              ),
              TextButton(
                onPressed: onChangePhone,
                style: TextButton.styleFrom(
                  foregroundColor: palette.gold,
                  padding: const EdgeInsets.symmetric(horizontal: 10),
                  minimumSize: const Size(0, 34),
                  tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                  textStyle: const TextStyle(
                    fontFamily: HarajTheme.fontFamily,
                    fontSize: 13,
                    fontWeight: FontWeight.w700,
                  ),
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

/// بطاقةٌ بيضاء زجاجيّة بحدٍّ فاتح — وعاءُ شاشة الدخول نفسُه، مكرَّراً هنا
/// لأن ذاك خاصٌّ بملفّه.
class _Card extends StatelessWidget {
  const _Card({required this.child, this.padding = const EdgeInsets.all(16)});

  final Widget child;
  final EdgeInsetsGeometry padding;

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

/// الشعارُ في دائرةٍ داكنة بإطارٍ أبيض ثمّ الاسمُ وسطرُ الخطوة — علامةُ شاشة
/// الدخول نفسُها، فيعبر العميلُ من الخطوة الأولى إلى الثانية بلا قفزة.
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
