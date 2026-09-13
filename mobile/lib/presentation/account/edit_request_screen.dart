import 'package:flutter/material.dart';

import '../../l10n/generated/app_localizations.dart';
import 'account_page_scaffold.dart';
import 'support_contact_card.dart';

/// صفحة «طلب تعديل البيانات» — تعديلُ البيانات يمرّ بالدعم، فبطاقتُه هنا بنصّ
/// معلومةٍ يشرح ذلك (المادة ٤-٥: نفسُ بطاقة الدعم بنصٍّ مختلف).
class EditRequestScreen extends StatelessWidget {
  const EditRequestScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return AccountPageScaffold(
      title: l10n.accountMenuEditRequest,
      child: ListView(
        children: <Widget>[SupportContactCard(infoText: l10n.editRequestInfo)],
      ),
    );
  }
}
