import 'package:flutter/material.dart';

import '../../domain/common/money.dart';

/// عرض مبلغ **كما وصل** من الخادم.
///
/// لا تنسيق، ولا فواصل آلاف، ولا تقريب، ولا `NumberFormat`. المادة ١-٦: الرقم
/// الذي يراه المستخدم هو الرقم الذي يقابله قيد في الدفتر — وأي تنسيق محلي هو
/// قاعدة عرض ثانية تعيش في التطبيق وتفترق عن التقارير وعن أودو.
///
/// الاتجاه هنا `ltr` بالتحديد: الرقم نفسه يُكتب من اليسار لليمين حتى داخل نصّ
/// عربي، وترك الاتجاه للسياق RTL يقلب موضع العملة والنقطة العشرية بصرياً.
class MoneyText extends StatelessWidget {
  const MoneyText(this.money, {this.style, super.key});

  final Money money;
  final TextStyle? style;

  @override
  Widget build(BuildContext context) => Directionality(
    textDirection: TextDirection.ltr,
    child: Text('${money.amount} ${money.currency}', style: style),
  );
}
