import 'package:flutter/material.dart';

import '../../domain/bidding/entities/live_bids_update.dart';
import '../../l10n/generated/app_localizations.dart';

/// حال البثّ الحي، مكتوباً.
///
/// **هذا الشريط هو الغرض من البثّ لا زينته.** الاتصال الميت والاتصال الهادئ
/// يبدوان سواءً على الشاشة: الأرقام واقفة في الحالتين. من يقرأ رقماً بائتاً
/// على أنه الحالي ويزايد عليه يخسر مالاً حقيقياً — فالحالة تُعرض دائماً، ولا
/// تُخفى حين تكون «حي» كي لا يتعلّم العميل أن غيابها يعني شيئاً.
class LiveStatusBanner extends StatelessWidget {
  const LiveStatusBanner({required this.connection, super.key});

  final LiveConnection connection;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final theme = Theme.of(context);
    final lost = connection == LiveConnection.lost;

    return Container(
      width: double.infinity,
      color: lost
          ? theme.colorScheme.errorContainer
          : theme.colorScheme.surfaceContainerHighest,
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      child: Text(
        switch (connection) {
          LiveConnection.connecting => l10n.liveConnecting,
          LiveConnection.live => l10n.liveConnected,
          LiveConnection.lost => l10n.liveLost,
        },
        style: theme.textTheme.bodySmall?.copyWith(
          color: lost
              ? theme.colorScheme.onErrorContainer
              : theme.colorScheme.onSurfaceVariant,
          fontWeight: lost ? FontWeight.w700 : null,
        ),
      ),
    );
  }
}
