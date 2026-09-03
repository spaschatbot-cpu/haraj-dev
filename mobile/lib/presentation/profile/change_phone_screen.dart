import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../app/providers.dart';
import '../../app/router.dart';
import '../../domain/auth/entities/auth_session.dart';
import '../../domain/common/failure.dart';
import '../../l10n/generated/app_localizations.dart';
import '../auth/session_controller.dart';
import '../common/cooldown_button.dart';
import '../common/failure_view.dart';

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
          .requestCodes(newPhone: _newPhone.text.trim());
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
            newPhone: _newPhone.text.trim(),
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
    final sent = _sent;

    return Scaffold(
      appBar: AppBar(title: Text(l10n.changePhoneTitle)),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(l10n.changePhoneIntro),
            const SizedBox(height: 16),
            TextField(
              controller: _newPhone,
              keyboardType: TextInputType.phone,
              enabled: sent == null,
              decoration: InputDecoration(
                labelText: l10n.changePhoneNewLabel,
                hintText: l10n.signInPhoneHint,
              ),
              onChanged: (_) => setState(() {}),
            ),
            const SizedBox(height: 16),

            if (sent == null) ...[
              if (_busy)
                const Center(child: CircularProgressIndicator())
              else if (_cooldownSeconds > 0)
                CooldownButton(
                  label: l10n.changePhoneSendCodes,
                  seconds: _cooldownSeconds,
                  token: _cooldownToken,
                  onPressed: _newPhone.text.trim().isEmpty ? null : _sendCodes,
                )
              else
                FilledButton(
                  onPressed: _newPhone.text.trim().isEmpty ? null : _sendCodes,
                  child: Text(l10n.changePhoneSendCodes),
                ),
            ] else ...[
              Text(l10n.changePhoneSentNotice(_newPhone.text.trim())),
              const SizedBox(height: 16),
              TextField(
                controller: _currentCode,
                keyboardType: TextInputType.number,
                decoration: InputDecoration(
                  labelText: l10n.changePhoneCurrentCode,
                ),
                onChanged: (_) => setState(() {}),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: _newCode,
                keyboardType: TextInputType.number,
                decoration: InputDecoration(labelText: l10n.changePhoneNewCode),
                onChanged: (_) => setState(() {}),
              ),
              const SizedBox(height: 24),
              if (_busy)
                const Center(child: CircularProgressIndicator())
              else
                FilledButton(
                  onPressed: _bothCodesEntered ? _confirm : null,
                  child: Text(l10n.changePhoneConfirm),
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
