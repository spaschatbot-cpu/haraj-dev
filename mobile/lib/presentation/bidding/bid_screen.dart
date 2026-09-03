import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../domain/bidding/entities/live_bids_update.dart';
import '../../l10n/generated/app_localizations.dart';
import '../common/money_text.dart';
import 'bidding_controllers.dart';
import 'live_status_banner.dart';
import 'place_bid_panel.dart';

/// شاشة المزايدة على مركبة واحدة.
///
/// مؤقّتة في موضعها لا في محتواها: صفحة المركبة (T709) هي التي ستستضيف
/// `PlaceBidPanel` في النهاية. فصلها اليوم يجعل المزايدة قابلة للفتح
/// والاختبار قبل أن تُبنى تلك الصفحة، وضمّها لاحقاً يحذف هذا الملف ولا يمسّ
/// الصندوق.
class BidScreen extends ConsumerWidget {
  const BidScreen({required this.vehicleId, super.key});

  final String vehicleId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = AppLocalizations.of(context);
    final live = ref.watch(liveBidsProvider);

    return Scaffold(
      appBar: AppBar(title: Text(l10n.bidPanelTitle)),
      body: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // حالة البثّ فوق كل شيء: ما تحتها أرقام، والعميل يحتاج أن يعرف كم
          // يصدّقها قبل أن يقرأها لا بعدها.
          LiveStatusBanner(
            connection: live.value?.connection ?? LiveConnection.connecting,
          ),
          Expanded(
            child: SingleChildScrollView(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  _StandingBid(update: live.value, vehicleId: vehicleId),
                  const SizedBox(height: 24),
                  PlaceBidPanel(vehicleId: vehicleId),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

/// مزايدة العميل القائمة على هذه المركبة — وليس رقم أحد غيره.
///
/// لا «أعلى مزايدة» ولا «أنت الأعلى» ولا عدد المنافسين: المزاد مغلق، ولا نقطة
/// في الخادم تسرد مزايدات مركبة أصلاً. لو ظهر أحدها في تصميم، فالجواب أن
/// الخادم لن يرسله.
class _StandingBid extends StatelessWidget {
  const _StandingBid({required this.update, required this.vehicleId});

  final LiveBidsUpdate? update;
  final String vehicleId;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final theme = Theme.of(context);
    final standing = update?.standingOn(vehicleId);

    if (standing == null) {
      return Text(l10n.liveNoStandingBid, style: theme.textTheme.bodyMedium);
    }

    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Flexible(
          child: Text(l10n.liveStandingBid, style: theme.textTheme.bodyMedium),
        ),
        const SizedBox(width: 12),
        MoneyText.bare(standing.amount, style: theme.textTheme.titleLarge),
      ],
    );
  }
}
