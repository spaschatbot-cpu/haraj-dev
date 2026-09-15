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
        mainAxisSpacing: 14,
        crossAxisSpacing: 14,
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
    return Container(
      decoration: BoxDecoration(
        color: palette.cardSurface,
        borderRadius: BorderRadius.circular(18),
        boxShadow: <BoxShadow>[
          BoxShadow(
            color: palette.ink.withValues(alpha: 0.06),
            blurRadius: 12,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(18),
        child: Column(
          children: <Widget>[
            // استروكٌ ذهبيٌّ علويّ — لهجةٌ على حافّة كل بطاقة.
            Container(
              height: 4,
              decoration: BoxDecoration(
                gradient: LinearGradient(
                  colors: <Color>[palette.gold, palette.goldDeep],
                ),
              ),
            ),
            Expanded(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: <Widget>[
                    Container(
                      width: 60,
                      height: 60,
                      alignment: Alignment.center,
                      decoration: BoxDecoration(
                        borderRadius: BorderRadius.circular(16),
                        color: palette.gold.withValues(alpha: 0.12),
                      ),
                      child: Icon(icon, size: 28, color: palette.goldDeep),
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
                      padding: const EdgeInsets.symmetric(
                        horizontal: 12,
                        vertical: 5,
                      ),
                      decoration: BoxDecoration(
                        color: palette.gold.withValues(alpha: 0.10),
                        borderRadius: BorderRadius.circular(20),
                      ),
                      child: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: <Widget>[
                          Icon(
                            Icons.hourglass_empty_rounded,
                            size: 13,
                            color: palette.goldDeep,
                          ),
                          const SizedBox(width: 5),
                          Text(
                            soon,
                            style: TextStyle(
                              color: palette.goldDeep,
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
              ),
            ),
          ],
        ),
      ),
    );
  }
}
