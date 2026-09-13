import 'package:flutter/material.dart';

import '../../domain/common/money.dart';

/// عرضُ مبلغٍ بالعملة بالعربية — «ر.س» بدل «SAR» بطلب المالك (١٣ سبتمبر ٢٠٢٦).
///
/// **الرقمُ كما أرسله الخادم** (المادة ١-٦): لا تنسيقَ ولا تقريب، وإنما تُترجَم
/// **كلمةُ العملة** وحدها — `SAR` → `ر.س`. وعملةٌ أخرى تُعرض كما جاءت، فلا
/// يُخترع رمزٌ لعملةٍ لا نعرفها. والاتجاه `ltr`: الرقم يُكتب يساراً لليمين حتى
/// داخل نصٍّ عربيّ، وترك الاتجاه للسياق يقلب موضع العملة.
class RiyalText extends StatelessWidget {
  const RiyalText(this.money, {this.style, super.key});

  final Money money;
  final TextStyle? style;

  static String label(Money money) {
    final currency = money.currency == 'SAR' ? 'ر.س' : money.currency;
    return '${money.amount} $currency';
  }

  @override
  Widget build(BuildContext context) => Directionality(
    textDirection: TextDirection.ltr,
    child: Text(label(money), style: style),
  );
}
