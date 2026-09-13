import 'package:flutter/material.dart';

import '../../l10n/generated/app_localizations.dart';
import 'account_page_scaffold.dart';
import 'guide_view.dart';

/// صفحة «شرح التسجيل» — خطواتٌ مصوّرةٌ عبر `GuideView` المشترك.
class RegistrationGuideScreen extends StatelessWidget {
  const RegistrationGuideScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return AccountPageScaffold(
      title: l10n.accountMenuRegistrationGuide,
      child: GuideView(
        headerTitle: l10n.guideHeaderTitle,
        headerSubtitle: l10n.guideHeaderSubtitle,
        headerIcon: Icons.edit_note_rounded,
        steps: <GuideStep>[
          GuideStep(l10n.guideStep1Title, l10n.guideStep1Body),
          GuideStep(l10n.guideStep2Title, l10n.guideStep2Body),
          GuideStep(l10n.guideStep3Title, l10n.guideStep3Body),
          GuideStep(l10n.guideStep4Title, l10n.guideStep4Body),
        ],
        videoSoonText: l10n.guideVideoSoon,
        hintText: l10n.guideSupportHint,
      ),
    );
  }
}
