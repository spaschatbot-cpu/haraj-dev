import 'package:flutter_test/flutter_test.dart';

import '../support/source_files.dart';

/// قاعدة التصميم 5 في الفيز 008: **لا تمويه (`blur`) في عناصر القوائم — يقتل
/// التمرير على الأجهزة المتوسطة.**
///
/// القاعدة مكتوبة في spec، وقاعدةٌ يحرسها المراجع وحده تتسرّب في أول يوم ضاغط.
/// وثمنها هنا غير مرئي في المراجعة: `BackdropFilter` يجبر Flutter على قراءة ما
/// خلفه ورسمه من جديد في كل إطار، فقائمةٌ بمئتي مركبة تسقط تحت الستين إطاراً
/// (معيار H2) على جهاز لا يملكه من كتب الشاشة.
void main() {
  test('لا تمويه في طبقة العرض', () {
    const forbidden = <String>['BackdropFilter', 'ImageFilter.blur'];

    final offenders = <String>[];
    for (final file in readLibrarySources(
      excluding: generatedPaths,
    ).where((file) => file.path.startsWith('lib/presentation/'))) {
      final code = file.withoutComments;
      for (final token in forbidden) {
        if (code.contains(token)) offenders.add('${file.path}: $token');
      }
    }

    expect(offenders, isEmpty, reason: 'قاعدة التصميم 5: $offenders');
  });
}
