/// مبلغ مالي كما وصل من الخادم.
///
/// **لماذا نصّ لا رقم:** المادة ٣-٢ من الدستور تمنع `float` في أي مسار مالي،
/// والمنع يسري على Dart كما يسري على بايثون. `double` في Dart هو IEEE-754
/// نفسه: `0.1 + 0.2` لا يساوي `0.3`، و`12500.10` لا يُمثَّل تمثيلاً دقيقاً.
///
/// **ولماذا بلا عمليات حسابية:** المادة ١-٦ — كل رقم يظهر لمستخدم له مصدر في
/// الدفتر. أي جمع أو طرح هنا ينتج رقماً بلا قيد يقابله، وأي قاعدة تُحسب في
/// الشاشة نسخة ثانية ستفترق عن الأصل (المادة ٤-٥). الخادم يرسل المجاميع
/// محسوبة — `due_amount` يأتي جاهزاً، لا يُطرح هنا.
///
/// لذلك لا يوجد في هذا الصنف `operator +` ولا `operator -` ولا تحويل إلى
/// `double`. غيابها مقصود، وأي إضافة لها تُرفض في المراجعة.
final class Money {
  const Money({required this.amount, required this.currency});

  /// المبلغ كما جاء في JSON: نصّ عشري بخانتين، مثل `"12500.00"`.
  final String amount;

  /// رمز العملة كما جاء، مثل `"SAR"`.
  final String currency;

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is Money && other.amount == amount && other.currency == currency;

  @override
  int get hashCode => Object.hash(amount, currency);

  @override
  String toString() => '$amount $currency';
}
