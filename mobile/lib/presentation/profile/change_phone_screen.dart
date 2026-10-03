import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../app/providers.dart';
import '../../app/router.dart';
import '../../app/theme.dart';
import '../../domain/auth/entities/auth_session.dart';
import '../../domain/common/failure.dart';
import '../../l10n/generated/app_localizations.dart';
import '../auth/session_controller.dart';
import '../common/cooldown_button.dart';
import '../common/failure_view.dart';
import '../common/haraj_app_bar.dart';
import '../common/saudi_phone_field.dart';

/// تغيير رقم الجوال بتأكيد الرقمين.
///
/// خطوتان في شاشة واحدة، والرمزان يُدخلان معاً: لا حالة وسطى «الرقم القديم
/// مُثبَت والجديد لا». تلك الحالة هي مسار الاستيلاء على الحساب في v1 — من وصل
/// إلى جلسة مفتوحة نقل الحساب إلى رقمه، وجوّالُ صاحبه لم يرنّ.
///
/// والنجاح ينتهي بالخروج: الخادم يُلغي كل الجلسات، فالبقاء في الشاشة كذبة
/// تكتشفها أول 401.
class ChangePhoneScreen extends ConsumerStatefulWidget {
  const ChangePhoneScreen({super.key});

  @override
  ConsumerState<ChangePhoneScreen> createState() => _ChangePhoneScreenState();
}

class _ChangePhoneScreenState extends ConsumerState<ChangePhoneScreen> {
  final TextEditingController _newPhone = TextEditingController();
  final TextEditingController _currentCode = TextEditingController();
  final TextEditingController _newCode = TextEditingController();

  bool _busy = false;
  Failure? _failure;
  PhoneChangeCodes? _sent;
  int _cooldownSeconds = 0;
  int _cooldownToken = 0;

  @override
  void dispose() {
    _newPhone.dispose();
    _currentCode.dispose();
    _newCode.dispose();
    super.dispose();
  }

  Future<void> _sendCodes() async {
    setState(() {
      _busy = true;
      _failure = null;
    });

    try {
      final sent = await ref
          .read(changePhoneNumberProvider)
          .requestCodes(
            newPhone: SaudiPhoneField.toServerFormat(_newPhone.text),
          );
      setState(() {
        _sent = sent;
        _cooldownSeconds = sent.delivery.resendAfterSeconds;
        _cooldownToken += 1;
      });
    } on Failure catch (failure) {
      if (!mounted) return;
      setState(() {
        _failure = failure;
        final seconds = failure is ApiFailure
            ? failure.retryAfterSeconds
            : null;
        if (seconds != null) {
          _cooldownSeconds = seconds;
          _cooldownToken += 1;
        }
      });
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _confirm() async {
    setState(() {
      _busy = true;
      _failure = null;
    });

    try {
      await ref
          .read(changePhoneNumberProvider)
          .confirm(
            newPhone: SaudiPhoneField.toServerFormat(_newPhone.text),
            currentCode: _currentCode.text.trim(),
            newCode: _newCode.text.trim(),
          );

      // الجلسات كلها أُلغيت — هذه منها. الخروج جزء من النجاح لا نتيجة عطل.
      await ref.read(sessionControllerProvider.notifier).signOut();
      if (!mounted) return;
      final l10n = AppLocalizations.of(context);
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text(l10n.changePhoneDone)));
      context.goNamed(Routes.signIn);
    } on Failure catch (failure) {
      if (mounted) setState(() => _failure = failure);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final palette = HarajPalette.of(context);
    final sent = _sent;

    // تصميمُ الزجاج الأبيض بطلب المالك (٣ أكتوبر ٢٠٢٦): الخلفيّةُ المتدرّجة
    // خلف كلّ المسارات (`GlassBackdrop`)، والخطوتان في بطاقتين زجاجيّتين —
    // الرقمُ الجديد، ثم الرمزان — كي تُقرأ الثانيةُ خطوةً تاليةً لا امتداداً.
    return Scaffold(
      backgroundColor: Colors.transparent,
      appBar: HarajAppBar(title: l10n.changePhoneTitle),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            _GlassCard(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  _CardHeader(
                    icon: Icons.phone_iphone_rounded,
                    title: l10n.changePhoneTitle,
                  ),
                  Padding(
                    padding: const EdgeInsets.symmetric(vertical: 14),
                    child: Divider(
                      height: 1,
                      color: palette.navInactive.withValues(alpha: 0.7),
                    ),
                  ),
                  Text(l10n.changePhoneIntro, style: _bodyStyle(palette)),
                  const SizedBox(height: 16),
                  // الهيئةُ المؤطَّرة كشاشة الدخول؛ وهي بلا تسميةٍ عائمة،
                  // فالتسميةُ سطرٌ فوقها.
                  Text(l10n.changePhoneNewLabel, style: _labelStyle(palette)),
                  const SizedBox(height: 8),
                  SaudiPhoneField(
                    controller: _newPhone,
                    label: l10n.changePhoneNewLabel,
                    enabled: sent == null,
                    boxed: true,
                    onChanged: (_) => setState(() {}),
                  ),
                  if (sent == null) ...[
                    const SizedBox(height: 16),
                    if (_busy)
                      const Center(child: CircularProgressIndicator())
                    else if (_cooldownSeconds > 0)
                      CooldownButton(
                        label: l10n.changePhoneSendCodes,
                        seconds: _cooldownSeconds,
                        token: _cooldownToken,
                        onPressed: SaudiPhoneField.isBlank(_newPhone.text)
                            ? null
                            : _sendCodes,
                      )
                    else
                      FilledButton(
                        onPressed: SaudiPhoneField.isBlank(_newPhone.text)
                            ? null
                            : _sendCodes,
                        style: _primaryButton(palette),
                        child: Text(l10n.changePhoneSendCodes),
                      ),
                  ],
                ],
              ),
            ),

            if (sent != null) ...[
              const SizedBox(height: 14),
              _GlassCard(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    _CardHeader(
                      icon: Icons.sms_outlined,
                      title: l10n.changePhoneConfirm,
                    ),
                    Padding(
                      padding: const EdgeInsets.symmetric(vertical: 14),
                      child: Divider(
                        height: 1,
                        color: palette.navInactive.withValues(alpha: 0.7),
                      ),
                    ),
                    Text(
                      l10n.changePhoneSentNotice(
                        SaudiPhoneField.toServerFormat(_newPhone.text),
                      ),
                      style: _bodyStyle(palette),
                    ),
                    const SizedBox(height: 16),
                    TextField(
                      controller: _currentCode,
                      keyboardType: TextInputType.number,
                      decoration: _inputDecoration(
                        palette,
                        l10n.changePhoneCurrentCode,
                      ),
                      onChanged: (_) => setState(() {}),
                    ),
                    const SizedBox(height: 12),
                    TextField(
                      controller: _newCode,
                      keyboardType: TextInputType.number,
                      decoration: _inputDecoration(
                        palette,
                        l10n.changePhoneNewCode,
                      ),
                      onChanged: (_) => setState(() {}),
                    ),
                    const SizedBox(height: 16),
                    if (_busy)
                      const Center(child: CircularProgressIndicator())
                    else
                      FilledButton(
                        onPressed: _bothCodesEntered ? _confirm : null,
                        style: _primaryButton(palette),
                        child: Text(l10n.changePhoneConfirm),
                      ),
                  ],
                ),
              ),
            ],

            if (_failure != null) ...[
              const SizedBox(height: 16),
              FailureView(failure: _failure!),
            ],
          ],
        ),
      ),
    );
  }

  /// الرمزان معاً — نفس قاعدة الخادم: واحد صحيح لا يغيّر شيئاً.
  bool get _bothCodesEntered =>
      _currentCode.text.trim().isNotEmpty && _newCode.text.trim().isNotEmpty;
}

// ---------------------------------------------------------------------------
// أجزاءُ الزجاج الأبيض (٣ أكتوبر ٢٠٢٦) — على مقاس شاشة الدخول وتفاصيل المركبة.
// خاصّةٌ بالملفّ لا مشتركة: الأجزاءُ المشتركة يحرّرها غيرُ هذه الشاشة الآن،
// ونسخةٌ صغيرةٌ هنا أرخصُ من تعارضٍ في ملفٍّ عامّ.
// ---------------------------------------------------------------------------

/// بطاقةٌ زجاجيّة: سطحٌ أبيضُ شفّاف، وحدٌّ رفيع، وظلٌّ خفيف.
class _GlassCard extends StatelessWidget {
  const _GlassCard({required this.child});

  final Widget child;

  @override
  Widget build(BuildContext context) {
    final palette = HarajPalette.of(context);
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: palette.cardSurface,
        borderRadius: BorderRadius.circular(20),
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

/// رأسُ البطاقة: أيقونةٌ زرقاء في مربّعٍ مدوّرٍ بمسحةٍ خفيفة، ثم العنوان.
class _CardHeader extends StatelessWidget {
  const _CardHeader({required this.icon, required this.title});

  final IconData icon;
  final String title;

  @override
  Widget build(BuildContext context) {
    final palette = HarajPalette.of(context);
    return Row(
      children: <Widget>[
        Container(
          width: 36,
          height: 36,
          alignment: Alignment.center,
          decoration: BoxDecoration(
            color: palette.gold.withValues(alpha: 0.08),
            borderRadius: BorderRadius.circular(10),
          ),
          child: Icon(icon, size: 19, color: palette.gold),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: Text(
            title,
            style: TextStyle(
              fontFamily: HarajTheme.fontFamily,
              fontSize: 16,
              fontWeight: FontWeight.w700,
              color: palette.ink,
            ),
          ),
        ),
      ],
    );
  }
}

TextStyle _bodyStyle(HarajPalette palette) => TextStyle(
  fontFamily: HarajTheme.fontFamily,
  fontSize: 13.5,
  height: 1.6,
  color: palette.inkMuted,
);

TextStyle _labelStyle(HarajPalette palette) => TextStyle(
  fontFamily: HarajTheme.fontFamily,
  fontSize: 13,
  fontWeight: FontWeight.w600,
  color: palette.ink,
);

/// الزرُّ الأساسيّ: لونُ العلامة صلباً، بارتفاع ٥٠ وتدويرِ ١٤.
ButtonStyle _primaryButton(HarajPalette palette) => FilledButton.styleFrom(
  backgroundColor: palette.gold,
  foregroundColor: Colors.white,
  disabledBackgroundColor: palette.gold.withValues(alpha: 0.35),
  disabledForegroundColor: Colors.white,
  minimumSize: const Size.fromHeight(50),
  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
  textStyle: const TextStyle(
    fontFamily: HarajTheme.fontFamily,
    fontWeight: FontWeight.w700,
    fontSize: 15,
  ),
);

/// خانةُ إدخالٍ زجاجيّة: مملوءةٌ بسطح البطاقة، وحدُّها رفيع، ويزرقّ عند
/// التركيز.
InputDecoration _inputDecoration(HarajPalette palette, String label) {
  OutlineInputBorder edge(Color colour, [double width = 1]) =>
      OutlineInputBorder(
        borderRadius: BorderRadius.circular(14),
        borderSide: BorderSide(color: colour, width: width),
      );
  return InputDecoration(
    labelText: label,
    labelStyle: TextStyle(
      fontFamily: HarajTheme.fontFamily,
      color: palette.inkMuted,
    ),
    filled: true,
    fillColor: palette.cardSurface,
    contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
    border: edge(palette.navInactive),
    enabledBorder: edge(palette.navInactive),
    focusedBorder: edge(palette.gold, 1.4),
  );
}
