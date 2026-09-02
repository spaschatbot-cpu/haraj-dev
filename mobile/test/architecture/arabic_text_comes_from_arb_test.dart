import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';

import '../support/source_files.dart';

/// معيار القبول H3: «كل نصّ عربي ومن ملف ترجمة، لا نصّ مكتوب داخل شاشة»،
/// والقبول منصوص عليه بوصفه **فحصاً نصّياً يمنع أي نصّ عربي مكتوب داخل شاشة**.
///
/// الاستثناء الوحيد هو التعليقات — وهي تُحذف قبل الفحص: المادة ٤-٦ تطلب أن
/// يشرح التعليق السبب، والسبب يُكتب بلغة من يقرؤه.
void main() {
  test('لا نصّ عربي حرفي في شيفرة lib/', () {
    final sources = readLibrarySources(
      excluding: <String>[
        // ملفات الترجمة نفسها — هي المصدر المقصود للنصّ العربي.
        'lib/l10n/',
        // مولَّد من المخطط: تعليقاته من وصف OpenAPI العربي، ولا يُحرَّر بيد.
        'lib/data/api/generated/',
        '.g.dart',
        '.freezed.dart',
      ],
    );

    final arabic = RegExp(r'[؀-ۿ]');
    final offenders = <String>[];

    for (final file in sources) {
      final code = file.withoutComments;
      for (final (index, line) in code.split('\n').indexed) {
        if (arabic.hasMatch(line)) {
          offenders.add('${file.path}:${index + 1}: ${line.trim()}');
        }
      }
    }

    expect(
      offenders,
      isEmpty,
      reason:
          'النصّ العربي يعيش في lib/l10n/arb/app_ar.arb وحده. '
          'المخالفات:\n${offenders.join('\n')}',
    );
  });

  test('ملفا الترجمة يحملان نفس المفاتيح', () {
    // مفتاح في العربية بلا نظير إنجليزي يظهر عند المستخدم كمفتاح خام. ولأن
    // العربية هي القالب، فالنقص يقع في الإنجليزية دائماً ويمرّ صامتاً.
    Map<String, Object?> keysOf(String path) {
      final decoded =
          jsonDecode(File(path).readAsStringSync()) as Map<String, Object?>;
      return Map<String, Object?>.fromEntries(
        decoded.entries.where((entry) => !entry.key.startsWith('@')),
      );
    }

    final arabic = keysOf('lib/l10n/arb/app_ar.arb').keys.toSet();
    final english = keysOf('lib/l10n/arb/app_en.arb').keys.toSet();

    expect(
      arabic.difference(english),
      isEmpty,
      reason: 'مفاتيح عربية بلا ترجمة إنجليزية',
    );
    expect(
      english.difference(arabic),
      isEmpty,
      reason: 'مفاتيح إنجليزية بلا أصل عربي — العربية هي القالب',
    );
  });
}
