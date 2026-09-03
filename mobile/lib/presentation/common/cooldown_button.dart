import 'dart:async';

import 'package:flutter/material.dart';

import '../../l10n/generated/app_localizations.dart';

/// زرّ لا يُضغط قبل أن تنقضي ثوانٍ **قالها الخادم**.
///
/// الثواني لا يخترعها التطبيق: تأتي مع الرمز المُرسَل (`resend_after`) ومع
/// الرفض (`detail.retry_after` في 429 وفي «الرمز السابق ما زال حيّاً»). زرّ
/// يعرض «حاول لاحقاً» بلا رقم يجعل المستخدم يضغط كل ثانية — على نفس الحدّ
/// الذي رفضه.
class CooldownButton extends StatefulWidget {
  const CooldownButton({
    required this.label,
    required this.seconds,
    required this.token,
    required this.onPressed,
    super.key,
  });

  final String label;

  /// طول المهلة بالثواني — صفر يعني «اضغط الآن».
  final int seconds;

  /// يتغيّر مع كل مهلة جديدة فيعيد العدّ من أولها.
  ///
  /// بلا رمز مميِّز لا تفرّق الشاشة بين «مهلة ستون ثانية جديدة» و«نفس المهلة
  /// التي تعدّ منذ عشرين»، فتقفز الأرقام إلى الوراء عند كل إعادة بناء.
  final Object token;

  /// `null` يعني الزرّ معطَّل لسبب آخر (إرسال جارٍ، حقل فارغ).
  final VoidCallback? onPressed;

  @override
  State<CooldownButton> createState() => _CooldownButtonState();
}

class _CooldownButtonState extends State<CooldownButton> {
  Timer? _ticker;
  int _remaining = 0;

  @override
  void initState() {
    super.initState();
    _restart();
  }

  @override
  void didUpdateWidget(CooldownButton oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.token != widget.token) _restart();
  }

  void _restart() {
    _ticker?.cancel();
    _remaining = widget.seconds < 0 ? 0 : widget.seconds;
    if (_remaining == 0) return;

    // عدّ بخطوة واحدة لا حساب فرق بين لحظتين: المهلة رقم من الخادم، وربطها
    // بساعة الجهاز يجعل جهازاً ساعته متأخّرة ينتظر أبداً.
    _ticker = Timer.periodic(const Duration(seconds: 1), (timer) {
      setState(() => _remaining -= 1);
      if (_remaining <= 0) timer.cancel();
    });
  }

  @override
  void dispose() {
    _ticker?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final waiting = _remaining > 0;

    return TextButton(
      onPressed: waiting ? null : widget.onPressed,
      child: Text(
        waiting
            ? '${widget.label} ${l10n.waitSeconds(_remaining)}'
            : widget.label,
      ),
    );
  }
}
