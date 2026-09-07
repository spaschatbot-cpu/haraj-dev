import 'package:flutter_test/flutter_test.dart';
import 'package:haraj_mobile/domain/common/money.dart';

/// المادة ٣-٢ و١-٦ في Dart.
void main() {
  test('المبلغ يبقى نصّاً كما وصل — بلا تطبيع ولا تقريب', () {
    const money = Money(amount: '12500.10', currency: 'SAR');

    expect(money.amount, '12500.10');
    // نفس السلسلة بالضبط: أصفار الخانتين جزء من الرقم الذي يقابله قيد.
    expect(money.amount, isNot('12500.1'));
  });

  test('صفر يُحفظ بشكله لا بقيمته', () {
    expect(const Money(amount: '0.00', currency: 'SAR').amount, '0.00');
  });

  test('التساوي على النصّ والعملة معاً', () {
    const riyals = Money(amount: '100.00', currency: 'SAR');
    const dollars = Money(amount: '100.00', currency: 'USD');

    expect(riyals, const Money(amount: '100.00', currency: 'SAR'));
    expect(riyals, isNot(dollars));
  });
}
