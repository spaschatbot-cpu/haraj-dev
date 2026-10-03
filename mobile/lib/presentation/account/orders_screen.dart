import 'package:flutter/material.dart';

import '../../app/theme.dart';
import '../../l10n/generated/app_localizations.dart';
import 'account_page_scaffold.dart';

/// صفحة «الطلبات» — على تصميم المالك (١٣ سبتمبر ٢٠٢٦): أربعُ خدماتٍ في شبكةٍ
/// ٢×٢، كلٌّ بأيقونةٍ وعنوانٍ وشارة «قريباً».
///
/// **كلُّها «قريباً»**: لا مدخلَ لأيٍّ منها في عقد الخادم بعد، فالبطاقاتُ
/// معروضةٌ ومعطَّلةٌ بصدق بدل أن تفتح شاشةً فارغة — تُوصَل واحدةً واحدة حين
/// يصل مدخلُها.
class OrdersScreen extends StatelessWidget {
  const OrdersScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final items = <({IconData icon, String label})>[
      (icon: Icons.person_off_outlined, label: l10n.ordersHandover),
      (icon: Icons.directions_car_outlined, label: l10n.ordersTransfer),
      (icon: Icons.local_shipping_outlined, label: l10n.ordersDelivery),
      (icon: Icons.download_outlined, label: l10n.ordersReceive),
    ];

    return AccountPageScaffold(
      title: l10n.accountMenuOrders,
      child: GridView.count(
        padding: EdgeInsets.fromLTRB(
          16,
          16,
          16,
          16 + MediaQuery.paddingOf(context).bottom,
        ),
        crossAxisCount: 2,
        // فجوةُ ١٢ — إيقاعُ القوائم في الزجاج الأبيض (٣ أكتوبر ٢٠٢٦).
        mainAxisSpacing: 12,
        crossAxisSpacing: 12,
        // نسبةٌ أطول: البطاقةُ بأيقونةٍ وعنوانٍ وشارةٍ كانت تفيض ١٧ بكسلاً
        // بنسبة ٠٫٩٥ (١٣ سبتمبر ٢٠٢٦). ٠٫٧٨ يعطي الارتفاعَ الذي يسعها.
        childAspectRatio: 0.78,
        children: <Widget>[
          for (final item in items)
            _OrderCard(
              icon: item.icon,
              label: item.label,
              soon: l10n.ordersSoon,
            ),
        ],
      ),
    );
  }
}

class _OrderCard extends StatelessWidget {
  const _OrderCard({
    required this.icon,
    required this.label,
    required this.soon,
  });

  final IconData icon;
  final String label;
  final String soon;

  @override
  Widget build(BuildContext context) {
    final palette = HarajPalette.of(context);
    // بطاقةٌ زجاجيّة بحدٍّ رقيق وظلٍّ ناعم — تصميمُ الزجاج الأبيض بطلب المالك
    // (٣ أكتوبر ٢٠٢٦). سقط الاستروكُ الذهبيّ العلويّ: شريطٌ ملوّنٌ على حافّة
    // كلّ بطاقة يُثقل الشبكةَ ويقطع شفافيّةَ الزجاج، والحدُّ يكفي حدّاً.
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: palette.cardSurface,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: palette.navInactive.withValues(alpha: 0.7)),
        boxShadow: <BoxShadow>[
          BoxShadow(
            color: palette.ink.withValues(alpha: 0.05),
            blurRadius: 16,
            offset: const Offset(0, 6),
          ),
        ],
      ),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: <Widget>[
          Container(
            width: 64,
            height: 64,
            alignment: Alignment.center,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: palette.gold.withValues(alpha: 0.10),
            ),
            child: Icon(icon, size: 28, color: palette.gold),
          ),
          const SizedBox(height: 14),
          Text(
            label,
            textAlign: TextAlign.center,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: TextStyle(
              color: palette.ink,
              fontSize: 15,
              fontWeight: FontWeight.w700,
              fontFamily: HarajTheme.fontFamily,
            ),
          ),
          const SizedBox(height: 10),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 5),
            decoration: BoxDecoration(
              color: palette.gold.withValues(alpha: 0.08),
              borderRadius: BorderRadius.circular(999),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: <Widget>[
                Icon(
                  Icons.hourglass_empty_rounded,
                  size: 13,
                  color: palette.gold,
                ),
                const SizedBox(width: 5),
                Text(
                  soon,
                  style: TextStyle(
                    color: palette.gold,
                    fontSize: 12,
                    fontWeight: FontWeight.w700,
                    fontFamily: HarajTheme.fontFamily,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
