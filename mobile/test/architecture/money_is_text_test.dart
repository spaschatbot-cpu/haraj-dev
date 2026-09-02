import 'package:flutter_test/flutter_test.dart';

import '../support/source_files.dart';

/// معيار القبول H4: **لا حساب مالي في التطبيق** — «يُثبت بمراجعة وفحص نصّي».
///
/// هذا هو الفحص النصّي. المادة ٣-٢ تمنع `float` في أي مسار مالي، و`double` في
/// Dart هو IEEE-754 نفسه.
void main() {
  test('لا `double` في طبقتي النطاق والبيانات', () {
    // هاتان الطبقتان منطق صافٍ: لا مقاسات widgets ولا إحداثيات، فلا عذر
    // لـ`double` فيهما أصلاً. (`double.infinity` في العرض مسموح: مقاس لا مبلغ.)
    final sources = readLibrarySources(excluding: generatedPaths);
    final offenders = sources
        .where(
          (file) =>
              file.path.startsWith('lib/domain/') ||
              file.path.startsWith('lib/data/'),
        )
        .where((file) => RegExp(r'\bdouble\b').hasMatch(file.withoutComments))
        .map((file) => file.path)
        .toList();

    expect(offenders, isEmpty, reason: 'المادة ٣-٢: $offenders');
  });

  test('لا حقل ذو اسم مالي بنوع رقمي — حتى في الشيفرة المولَّدة', () {
    // يشمل `lib/data/api/generated/` عمداً: لو غيّر الخادم مبلغاً من نصّ إلى
    // رقم، يسقط هذا الاختبار عند أول إعادة توليد بدل أن يمرّ إلى المستخدم.
    final sources = readLibrarySources();
    final moneyNamed = RegExp(
      r'\b(?:double|num)\s+\w*'
      r'(?:amount|balance|price|total|fee|paid|due|deposit|bid)\w*\b',
      caseSensitive: false,
    );

    final offenders = <String>[];
    for (final file in sources) {
      for (final match in moneyNamed.allMatches(file.withoutComments)) {
        offenders.add('${file.path}: ${match.group(0)}');
      }
    }

    expect(
      offenders,
      isEmpty,
      reason: 'المبالغ تصل نصّاً عشرياً وتبقى نصّاً: $offenders',
    );
  });

  test('لا تحويل نصّ إلى عدد عشري في أي مكان', () {
    final sources = readLibrarySources();
    const forbidden = <String>['double.parse', 'num.parse', '.toDouble()'];

    final offenders = <String>[];
    for (final file in sources) {
      final code = file.withoutComments;
      for (final token in forbidden) {
        if (code.contains(token)) offenders.add('${file.path}: $token');
      }
    }

    expect(
      offenders,
      isEmpty,
      reason:
          'تحويل مبلغ إلى عدد عشري يفقد الدقة ويفتح باب الحساب في الشاشة: '
          '$offenders',
    );
  });

  test('صنف Money لا يعرّف عمليات حسابية', () {
    final money = readLibrarySources()
        .firstWhere((file) => file.path.endsWith('domain/common/money.dart'))
        .withoutComments;

    for (final operator in <String>[
      'operator +',
      'operator -',
      'operator *',
      'operator /',
    ]) {
      expect(
        money.contains(operator),
        isFalse,
        reason:
            'المادة ١-٦: كل رقم يظهر لمستخدم يقابله قيد. الحساب في الشاشة '
            'ينتج رقماً بلا قيد. ($operator)',
      );
    }
  });
}
