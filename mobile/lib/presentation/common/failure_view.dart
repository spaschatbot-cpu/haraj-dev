import 'package:flutter/material.dart';

import '../../domain/common/failure.dart';
import '../../l10n/generated/app_localizations.dart';
import 'failure_message.dart';

/// عرض خطأ موحّد لكل الشاشات (T705).
///
/// وجوده كـwidget واحد هو ما يجعل «كل رمز خطأ له عرض مناسب» قابلاً للتحقق:
/// شاشة تكتب معالجة خطأ خاصة بها تخرج عن هذا العقد وتُرفض في المراجعة.
class FailureView extends StatelessWidget {
  const FailureView({required this.failure, this.onRetry, super.key});

  final Failure failure;
  final VoidCallback? onRetry;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return Padding(
      padding: const EdgeInsets.all(24),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            failureMessage(context, failure),
            textAlign: TextAlign.center,
            style: Theme.of(context).textTheme.bodyLarge,
          ),
          if (onRetry != null) ...[
            const SizedBox(height: 16),
            FilledButton(onPressed: onRetry, child: Text(l10n.retry)),
          ],
        ],
      ),
    );
  }
}
