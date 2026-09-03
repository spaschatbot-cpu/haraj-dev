import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../app/providers.dart';
import '../../app/router.dart';
import '../../domain/common/failure.dart';
import '../../domain/common/failure_codes.dart';
import '../../l10n/generated/app_localizations.dart';
import '../common/cooldown_button.dart';
import '../common/failure_view.dart';
import '../common/saudi_time.dart';
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

    final expiresAt = SaudiTime.forDisplay(pending.delivery.expiresAt);

    return Scaffold(
      appBar: AppBar(title: Text(l10n.verifyTitle)),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(l10n.verifySentTo(pending.phone)),
            const SizedBox(height: 4),
            Text(
              l10n.verifyExpiresAt(expiresAt),
              style: Theme.of(context).textTheme.bodySmall,
            ),
            const SizedBox(height: 16),
            TextField(
              controller: _code,
              keyboardType: TextInputType.number,
              autofillHints: const [AutofillHints.oneTimeCode],
              decoration: InputDecoration(labelText: l10n.verifyCodeLabel),
              onChanged: (_) => setState(() {}),
            ),
            if (_needsName) ...[
              const SizedBox(height: 16),
              TextField(
                controller: _fullName,
                decoration: InputDecoration(
                  labelText: l10n.verifyFullNameLabel,
                ),
                onChanged: (_) => setState(() {}),
              ),
            ],
            const SizedBox(height: 24),
            if (_busy)
              const Center(child: CircularProgressIndicator())
            else
              FilledButton(
                onPressed: _canSubmit ? () => _submit(pending.phone) : null,
                child: Text(l10n.verifySubmit),
              ),
            const SizedBox(height: 8),
            CooldownButton(
              label: l10n.verifyResend,
              seconds: _cooldownSeconds,
              token: _cooldownToken,
              onPressed: _busy ? null : () => _resend(pending.phone),
            ),
            TextButton(
              onPressed: () {
                ref.read(pendingSignInProvider.notifier).clear();
                context.goNamed(Routes.signIn);
              },
              child: Text(l10n.verifyChangePhone),
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

  bool get _canSubmit {
    if (_code.text.trim().isEmpty) return false;
    // الاسم شرط فقط بعد أن يطلبه الخادم لهذا الرقم.
    return !_needsName || _fullName.text.trim().isNotEmpty;
  }
}
