import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../l10n/generated/app_localizations.dart';

/// الأقسام الخمسة في الشريط السفليّ، **بترتيب ظهورها**.
///
/// تعدادٌ لا قائمةُ عناصرٍ مكتوبة في `build`: الترتيب هنا هو ترتيب الفروع في
/// `StatefulShellRoute`، والاثنان يُقرأان بالفهرس. قائمتان تفترقان عند أول
/// إضافةٍ في إحداهما، فيفتح تبويبُ «المفضلة» شاشةَ «محفظتي» — عطلٌ لا يكشفه
/// إلا مستخدم.
enum HomeSection {
  home(Icons.gavel_outlined, Icons.gavel),
  activity(Icons.receipt_long_outlined, Icons.receipt_long),
  favourites(Icons.favorite_border, Icons.favorite),
  wallet(Icons.account_balance_wallet_outlined, Icons.account_balance_wallet),
  account(Icons.person_outline, Icons.person);

  const HomeSection(this.icon, this.selectedIcon);

  /// أيقونتان لا واحدة: الفرق بين المختار وغيره لا يُحمَّل على اللون وحده —
  /// نسبةُ تباينٍ تكفي عيناً قد لا تكفي أخرى، والامتلاء يُقرأ بلا لون.
  final IconData icon;
  final IconData selectedIcon;

  /// النصّ من ملفّ الترجمة، والاختيار هنا لا هناك: التعداد يعرف نفسه، وملفّ
  /// الترجمة لا يعرف الترتيب.
  String label(AppLocalizations l10n) => switch (this) {
    HomeSection.home => l10n.navHome,
    HomeSection.activity => l10n.navActivity,
    HomeSection.favourites => l10n.navFavourites,
    HomeSection.wallet => l10n.navWallet,
    HomeSection.account => l10n.navAccount,
  };
}

/// القشرة التي تحمل الأقسام الخمسة وشريطها السفليّ.
///
/// **لكل قسمٍ مكدّسه** (`StatefulShellRoute.indexedStack`): من فتح مركبةً من
/// المفضلة ثم ذهب إلى المحفظة وعاد، يجد المركبة كما تركها لا رأس القسم. وهذا
/// هو الفرق بين شريطٍ يتنقّل بين خمس شاشات وشريطٍ يتنقّل بين خمسة **أقسام**.
///
/// والشاشات تحتفظ بـ`Scaffold` و`AppBar` الخاصّين بها؛ القشرة تضيف الشريط
/// وحده. جمعُ العنوان هنا كان يعني عنواناً واحداً لكل شاشةٍ داخل القسم.
class HomeShell extends StatelessWidget {
  const HomeShell({required this.navigationShell, super.key});

  final StatefulNavigationShell navigationShell;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);

    return Scaffold(
      body: navigationShell,
      bottomNavigationBar: NavigationBar(
        selectedIndex: navigationShell.currentIndex,
        onDestinationSelected: (index) => navigationShell.goBranch(
          index,
          // ضغطُ القسم المفتوح يعود إلى رأسه — سلوكٌ يتوقّعه من اعتاد
          // التطبيقات: «رجّعني لأول الصفحة» بضغطةٍ على ما هو مفتوح أصلاً.
          initialLocation: index == navigationShell.currentIndex,
        ),
        destinations: <NavigationDestination>[
          for (final section in HomeSection.values)
            NavigationDestination(
              icon: Icon(section.icon),
              selectedIcon: Icon(section.selectedIcon),
              label: section.label(l10n),
              // اسمُ القسم للقارئ الصوتيّ هو نفسه المكتوب — لا وصفٌ ثانٍ
              // يفترق عنه عند أول تعديل.
              tooltip: section.label(l10n),
            ),
        ],
      ),
    );
  }
}
