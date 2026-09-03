import 'package:flutter/material.dart';

import '../../../domain/profile/entities/customer_profile.dart';

/// حقل يُعرض مقفولاً **بسببه** — والسبب من الخادم كما جاء.
///
/// معيار قبول T715 بالضبط: «الحقول المقفولة تظهر مقفولة بسببها». الشاشة لا
/// تصوغ السبب ولا تستنتج القفل: `locked_fields` تصل من العقد، ونصّها هو نفسه
/// نصّ الرفض لو حاول أحد الكتابة — فلا يسمع العميل جوابين لقاعدة واحدة.
class LockedFieldRow extends StatelessWidget {
  const LockedFieldRow({
    required this.label,
    required this.value,
    required this.lock,
    super.key,
  });

  final String label;
  final String value;

  /// `null` يعني الحقل غير مقفول — عندها لا يُستعمل هذا الصف أصلاً.
  final LockedField lock;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.lock_outline, size: 16, color: theme.hintColor),
              const SizedBox(width: 8),
              Text(label, style: theme.textTheme.labelLarge),
            ],
          ),
          const SizedBox(height: 4),
          Text(value, style: theme.textTheme.bodyLarge),
          const SizedBox(height: 4),
          Text(
            lock.reason,
            style: theme.textTheme.bodySmall?.copyWith(color: theme.hintColor),
          ),
        ],
      ),
    );
  }
}
