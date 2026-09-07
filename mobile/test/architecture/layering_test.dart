import 'package:flutter_test/flutter_test.dart';

import '../support/source_files.dart';

/// يفرض قاعدة المعمارية الثلاثية (خطة الفريق §5).
///
/// القاعدة تُكتب في وثيقة، وتُنسى في PR رقم أربعين. هذا الاختبار يجعل خرقها
/// يسقط الـCI في نفس الدقيقة.
void main() {
  final sources = readLibrarySources(excluding: generatedPaths);

  test('طبقة العرض لا تستورد طبقة البيانات', () {
    // الاستثناء الوحيد: جذر التركيب `lib/app/` — هو المكان المعرَّف لربط
    // التنفيذ بالعقد، ولا يصدّر إلا أنواع النطاق.
    final offenders = sources
        .where((file) => file.path.startsWith('lib/presentation/'))
        .where(
          (file) => RegExp(
            r'''import\s+['"](?:package:haraj_mobile/data/|(?:\.\./)+data/)''',
          ).hasMatch(file.withoutComments),
        )
        .map((file) => file.path)
        .toList();

    expect(
      offenders,
      isEmpty,
      reason:
          'presentation تصل إلى البيانات عبر domain فقط. '
          'الملفات المخالفة: $offenders',
    );
  });

  test('طبقة النطاق Dart صافٍ — بلا Flutter ولا dio ولا drift', () {
    const forbidden = <String>[
      'package:flutter/',
      'package:flutter_riverpod/',
      'package:dio/',
      'package:drift/',
      'package:retrofit/',
      'package:flutter_secure_storage/',
    ];

    final offenders = <String>[];
    for (final file in sources.where(
      (file) => file.path.startsWith('lib/domain/'),
    )) {
      for (final package in forbidden) {
        if (file.withoutComments.contains("import '$package")) {
          offenders.add('${file.path} → $package');
        }
      }
    }

    expect(
      offenders,
      isEmpty,
      reason:
          'النطاق يجب أن يبقى قابلاً للاختبار بلا Flutter ولا شبكة. '
          'المخالفات: $offenders',
    );
  });

  test('طبقة النطاق لا تستورد طبقة البيانات', () {
    // الفحص على **الاستيرادات** لا على النصّ كله: ذكر ملف في تعليق توثيقي
    // ليس اعتماداً، وإسقاط الاختبار عليه يعلّم الفريق تجاهله.
    final offenders = sources
        .where((file) => file.path.startsWith('lib/domain/'))
        .where(
          (file) => RegExp(
            r'''import\s+['"](?:package:haraj_mobile/data/|(?:\.\./)+data/)''',
          ).hasMatch(file.withoutComments),
        )
        .map((file) => file.path)
        .toList();

    expect(offenders, isEmpty, reason: 'الاعتماد للداخل فقط: $offenders');
  });
}
