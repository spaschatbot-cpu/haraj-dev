import 'package:flutter/material.dart';

import '../../l10n/generated/app_localizations.dart';
import 'account_page_scaffold.dart';
import 'support_contact_card.dart';

/// صفحة «تواصل مع الدعم» — بطاقةُ الدعم الفني بزرّ واتساب.
class SupportScreen extends StatelessWidget {
  const SupportScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return AccountPageScaffold(
      title: l10n.accountMenuSupport,
      child: ListView(
        children: <Widget>[SupportContactCard(infoText: l10n.supportInfo)],
      ),
    );
  }
}
