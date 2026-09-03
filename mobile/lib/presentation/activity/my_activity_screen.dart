import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../l10n/generated/app_localizations.dart';
import 'activity_providers.dart';
import 'widgets/activity_list_view.dart';
import 'widgets/invoice_card.dart';
import 'widgets/participation_card.dart';
import 'widgets/purchase_card.dart';

/// تبويبات شاشة «حسابي». الاسم النصّي هو ما يصل في رابط الإشعار.
enum MyActivityTab {
  participations('participations'),
  purchases('purchases'),
  invoices('invoices');

  const MyActivityTab(this.slug);

  final String slug;

  /// اسم غير معروف (أو غائب) يفتح التبويب الأول ولا يُسقط الشاشة: إشعار من
  /// نسخة خادم أحدث يجب أن يفتح شيئاً، لا أن يعرض عطباً.
  static MyActivityTab fromSlug(String? slug) => values.firstWhere(
    (tab) => tab.slug == slug,
    orElse: () => MyActivityTab.participations,
  );
}

/// مشاركاتي ومشترياتي وفواتيري — **شاشة واحدة بثلاثة تبويبات**.
///
/// **لماذا واحدة لا ثلاث:** الثلاث إجابة على سؤال واحد يسأله العميل: «إيش
/// اللي لي وإيش اللي عليّ؟» والحلقة بينها ضيّقة — المشاركة تعرض تأميناً
/// مقفولاً، وسببُ القفل فاتورةٌ في التبويب الثالث. شاشات منفصلة تجعل العميل
/// يقرأ نصف الجواب ثم يبحث عن نصفه الآخر في قائمة أخرى، وهو بالضبط ما جعل
/// «ليه ما أقدر أسحب رصيدي؟» أكثر أسئلة v1.
///
/// ومع ذلك لكل تبويب **عنوانه** (`?tab=`): معيار H6 يشترط أن يفتح الإشعار
/// الشاشة الصحيحة مباشرةً، وإشعار فاتورة يجب أن يفتح الفواتير لا أن ينزل على
/// تبويب أول يبحث المستخدم بعده بيده.
class MyActivityScreen extends StatelessWidget {
  const MyActivityScreen({
    this.initialTab = MyActivityTab.participations,
    super.key,
  });

  final MyActivityTab initialTab;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);

    return DefaultTabController(
      length: MyActivityTab.values.length,
      initialIndex: initialTab.index,
      child: Scaffold(
        appBar: AppBar(
          title: Text(l10n.myActivityTitle),
          bottom: TabBar(
            tabs: <Widget>[
              Tab(text: l10n.tabParticipations),
              Tab(text: l10n.tabPurchases),
              Tab(text: l10n.tabInvoices),
            ],
          ),
        ),
        body: const TabBarView(
          children: <Widget>[
            _ParticipationsTab(),
            _PurchasesTab(),
            _InvoicesTab(),
          ],
        ),
      ),
    );
  }
}

class _ParticipationsTab extends ConsumerWidget {
  const _ParticipationsTab();

  @override
  Widget build(BuildContext context, WidgetRef ref) => ActivityListView(
    state: ref.watch(myParticipationsProvider),
    emptyMessage: AppLocalizations.of(context).emptyParticipations,
    onRetry: () => ref.invalidate(myParticipationsProvider),
    itemBuilder: (context, item) => ParticipationCard(participation: item),
  );
}

class _PurchasesTab extends ConsumerWidget {
  const _PurchasesTab();

  @override
  Widget build(BuildContext context, WidgetRef ref) => ActivityListView(
    state: ref.watch(myPurchasesProvider),
    emptyMessage: AppLocalizations.of(context).emptyPurchases,
    onRetry: () => ref.invalidate(myPurchasesProvider),
    itemBuilder: (context, item) => PurchaseCard(purchase: item),
  );
}

class _InvoicesTab extends ConsumerWidget {
  const _InvoicesTab();

  @override
  Widget build(BuildContext context, WidgetRef ref) => ActivityListView(
    state: ref.watch(myInvoicesProvider),
    emptyMessage: AppLocalizations.of(context).emptyInvoices,
    onRetry: () => ref.invalidate(myInvoicesProvider),
    itemBuilder: (context, item) => InvoiceCard(invoice: item),
  );
}
