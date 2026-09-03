import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../app/providers.dart';
import '../../app/router.dart';
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

    return Scaffold(
      appBar: AppBar(title: Text(l10n.signInTitle)),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            if (expired) ...[
              Text(
                l10n.sessionExpiredNotice,
                style: Theme.of(context).textTheme.bodyMedium,
              ),
              const SizedBox(height: 16),
            ],
            Text(l10n.signInIntro),
            const SizedBox(height: 16),
            TextField(
              controller: _phone,
              keyboardType: TextInputType.phone,
              autofillHints: const [AutofillHints.telephoneNumber],
              decoration: InputDecoration(
                labelText: l10n.signInPhoneLabel,
                hintText: l10n.signInPhoneHint,
              ),
              onChanged: (_) => setState(() {}),
            ),
            const SizedBox(height: 24),
            if (_sending)
              const Center(child: CircularProgressIndicator())
            else if (_cooldownSeconds > 0)
              CooldownButton(
                label: l10n.signInSendCode,
                seconds: _cooldownSeconds,
                token: _cooldownToken,
                onPressed: _phone.text.trim().isEmpty ? null : _send,
              )
            else
              FilledButton(
                onPressed: _phone.text.trim().isEmpty ? null : _send,
                child: Text(l10n.signInSendCode),
              ),
            if (_failure != null) ...[
              const SizedBox(height: 16),
              FailureView(failure: _failure!),
            ],
          ],
        ),
      ),
    );
  }
}
