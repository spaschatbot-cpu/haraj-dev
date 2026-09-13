import 'package:flutter/material.dart';

import '../../l10n/generated/app_localizations.dart';
import 'account_page_scaffold.dart';
import 'guide_view.dart';

/// صفحة «شرح شحن المحفظة» — خمسُ خطواتٍ مصوّرةٍ عبر `GuideView` المشترك.
class WalletGuideScreen extends StatelessWidget {
  const WalletGuideScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return AccountPageScaffold(
      title: l10n.accountMenuWalletGuide,
      child: GuideView(
        headerTitle: l10n.walletGuideHeaderTitle,
        headerSubtitle: l10n.walletGuideHeaderSubtitle,
        headerIcon: Icons.account_balance_wallet_rounded,
        steps: <GuideStep>[
          GuideStep(l10n.walletGuideStep1Title, l10n.walletGuideStep1Body),
          GuideStep(l10n.walletGuideStep2Title, l10n.walletGuideStep2Body),
          GuideStep(l10n.walletGuideStep3Title, l10n.walletGuideStep3Body),
          GuideStep(l10n.walletGuideStep4Title, l10n.walletGuideStep4Body),
          GuideStep(l10n.walletGuideStep5Title, l10n.walletGuideStep5Body),
        ],
        videoSoonText: l10n.guideVideoSoon,
        hintText: l10n.guideContactHint,
      ),
    );
  }
}
