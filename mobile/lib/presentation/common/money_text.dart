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
  const MoneyText(Money money, {this.style, super.key})
    : _money = money,
      _bare = null;

  /// مبلغ ذكره الخادم بلا عملة.
  ///
  /// له موضعان بالضبط، وكلاهما نصّ الخادم لا اختيارنا: حمولة رفض «أكّد الخفض»
  /// (`standing` و`requested`)، وإطار البثّ الحي. لا تحمل النقطتان عملةً لأن
  /// العملة تُذكر على المركبة، والبديل الوحيد أن يختار التطبيق عملةً من عنده —
  /// وهو اختراعُ معلومةٍ في شاشة مال.
  const MoneyText.bare(String amount, {this.style, super.key})
    : _money = null,
      _bare = amount;

  final Money? _money;
  final String? _bare;
  final TextStyle? style;

  @override
  Widget build(BuildContext context) {
    final money = _money;
    return Directionality(
      textDirection: TextDirection.ltr,
      child: Text(
        money == null ? _bare! : '${money.amount} ${money.currency}',
        style: style,
      ),
    );
  }
}
