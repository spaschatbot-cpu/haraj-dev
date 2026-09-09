import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../app/providers.dart';
import '../../app/router.dart';
import '../../app/theme.dart';
import '../../domain/common/failure.dart';
import '../../l10n/generated/app_localizations.dart';
import '../common/cooldown_button.dart';
import '../common/failure_view.dart';
import 'pending_sign_in.dart';
import 'session_controller.dart';

/// الخطوة الأولى: رقم الجوال.
///
/// **لا تحقّق من شكل الرقم هنا.** شكل الرقم السعودي قاعدة يملكها الخادم
/// (`PHONE_PATTERN`) ويردّ برسالتها العربية؛ ونسخةٌ منها في الشاشة تفترق عنها
/// عند أول تعديل، فيرفض التطبيقُ رقماً يقبله الخادم أو العكس (المادة ٤-٥).
/// المعطَّل هنا حالة واحدة: حقل فارغ — لا شيء يُرسَل أصلاً.
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
    final phone = _phone.text.trim();
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
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(20),
            child: ConstrainedBox(
              // **٤٠٠ لا عرضُ الشاشة**: حقلٌ واحد ممتدٌّ على شاشةٍ عريضة
              // يُقرأ نموذجاً طويلاً، وهو حقلٌ واحد.
              constraints: const BoxConstraints(maxWidth: 400),
              child: Material(
                color: palette.cardSurface,
                borderRadius: BorderRadius.circular(20),
                clipBehavior: Clip.antiAlias,
                elevation: 3,
                shadowColor: palette.ink.withValues(alpha: 0.22),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: <Widget>[
                    // شريطٌ داكن بعنوان اللوحة — نفس تدرّج الهيدر، فتُقرأ
                    // اللوحةُ من التطبيق لا نافذةً غريبة عليه.
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
                            Icon(
                              Icons.lock_outline_rounded,
                              size: 18,
                              color: palette.goldOnDark,
                            ),
                            const SizedBox(width: 8),
                            Expanded(
                              child: Text(
                                l10n.signInTitle,
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
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.stretch,
                        mainAxisSize: MainAxisSize.min,
                        children: <Widget>[
                          if (expired) ...<Widget>[
                            Text(
                              l10n.sessionExpiredNotice,
                              style: theme.textTheme.bodyMedium?.copyWith(
                                color: palette.ink,
                              ),
                            ),
                            const SizedBox(height: 14),
                          ],
                          Text(
                            l10n.signInIntro,
                            style: theme.textTheme.bodyMedium?.copyWith(
                              color: palette.inkMuted,
                            ),
                          ),
                          const SizedBox(height: 14),
                          TextField(
                            controller: _phone,
                            keyboardType: TextInputType.phone,
                            textDirection: TextDirection.ltr,
                            autofillHints: const <String>[
                              AutofillHints.telephoneNumber,
                            ],
                            decoration: InputDecoration(
                              labelText: l10n.signInPhoneLabel,
                              hintText: l10n.signInPhoneHint,
                              filled: true,
                              fillColor: palette.pageBackground,
                              border: OutlineInputBorder(
                                borderRadius: BorderRadius.circular(12),
                              ),
                            ),
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
                              onPressed: _phone.text.trim().isEmpty
                                  ? null
                                  : _send,
                            )
                          else
                            FilledButton(
                              onPressed: _phone.text.trim().isEmpty
                                  ? null
                                  : _send,
                              style: FilledButton.styleFrom(
                                backgroundColor: palette.goldDeep,
                                foregroundColor: Colors.white,
                                padding: const EdgeInsets.symmetric(
                                  vertical: 14,
                                ),
                                shape: RoundedRectangleBorder(
                                  borderRadius: BorderRadius.circular(12),
                                ),
                              ),
                              child: Text(l10n.signInSendCode),
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
                          if (_failure != null) ...<Widget>[
                            const SizedBox(height: 10),
                            FailureView(failure: _failure!),
                          ],
                        ],
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
}
