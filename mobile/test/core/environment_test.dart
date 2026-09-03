import 'package:flutter_test/flutter_test.dart';
import 'package:haraj_mobile/core/environment.dart';

/// T718 — البيئة تعرف نفسها، والافتراض يميل إلى الأمان (المادة ٥-٦).
void main() {
  test('اسم البيئة يُقرأ كما يكتبه البناء', () {
    expect(AppEnvironment.parse('production'), AppEnvironment.production);
    expect(AppEnvironment.parse('prod'), AppEnvironment.production);
    expect(AppEnvironment.parse('staging'), AppEnvironment.staging);
    expect(AppEnvironment.parse('development'), AppEnvironment.development);
  });

  test('حالة الأحرف لا تصنع بيئة أخرى', () {
    expect(AppEnvironment.parse('PRODUCTION'), AppEnvironment.production);
    expect(AppEnvironment.parse('Staging'), AppEnvironment.staging);
  });

  test('قيمة لا نعرفها لا تصير إنتاجاً أبداً', () {
    // الميل مقصود: بناءٌ يظنّ نفسه إنتاجاً وهو ليس كذلك يُخفي لافتته ويرسل
    // رسائل بلا ختم — وهي بالضبط الطريقة التي تصل بها رسالة اختبار إلى عميل
    // حقيقي. بناءٌ يظنّ نفسه تطويراً وهو إنتاج يعرض لافتة زائدة، وهذا كل شيء.
    expect(AppEnvironment.parse(''), AppEnvironment.development);
    expect(AppEnvironment.parse('produktion'), AppEnvironment.development);
    expect(AppEnvironment.parse('live'), AppEnvironment.development);
  });

  test('كل بيئة غير الإنتاج تعرّف نفسها', () {
    expect(AppEnvironment.development.showsBanner, isTrue);
    expect(AppEnvironment.staging.showsBanner, isTrue);
    expect(AppEnvironment.production.showsBanner, isFalse);
  });

  test('بناء بلا --dart-define لا يمكن أن يصيب الإنتاج', () {
    final config = AppConfig.fromBuild();

    expect(config.environment, AppEnvironment.development);
    expect(config.apiBaseUrl, isNotEmpty);
  });
}
