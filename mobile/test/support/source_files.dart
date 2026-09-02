/// أدوات مشتركة لاختبارات الفحص النصّي على شجرة `lib/`.
///
/// الفحص النصّي هنا ليس ترفاً: معياران من معايير قبول الفيز 008 (H3 و H4)
/// منصوص عليهما بوصفهما فحصاً نصّياً، لأن القاعدة التي يحرسها المراجع وحده
/// تتسرّب عند أول يوم ضاغط.
library;

import 'dart:io';

/// ملف مصدر مع مساره النسبي ومحتواه.
final class SourceFile {
  const SourceFile(this.path, this.content);

  final String path;
  final String content;

  /// المحتوى بعد حذف التعليقات.
  ///
  /// طريقة تقريبية مقصودة: التعليقات في هذا المستودع عربية بكثافة (المادة ٤-٦)،
  /// فأي فحص عن نصّ عربي داخل الشيفرة سيغرق فيها. قد تُشوَّه سلسلة تحوي `//`،
  /// لكن التشويه لا يُدخل حروفاً عربية، فلا ينتج إنذاراً كاذباً.
  String get withoutComments {
    final withoutBlocks = content.replaceAll(
      RegExp(r'/\*.*?\*/', dotAll: true),
      ' ',
    );
    return withoutBlocks
        .split('\n')
        .map((line) {
          final commentStart = line.indexOf('//');
          return commentStart == -1 ? line : line.substring(0, commentStart);
        })
        .join('\n');
  }
}

/// كل ملفات Dart تحت `lib/`، مع استثناء المسارات المعطاة.
List<SourceFile> readLibrarySources({List<String> excluding = const []}) {
  final root = Directory('lib');
  if (!root.existsSync()) {
    throw StateError(
      'اختبارات الفحص النصّي تُشغَّل من جذر حزمة mobile/ — لم يوجد مجلد lib/',
    );
  }

  return root
      .listSync(recursive: true)
      .whereType<File>()
      .map((file) => file.path.replaceAll(r'\', '/'))
      .where((path) => path.endsWith('.dart'))
      .where((path) => !excluding.any((fragment) => path.contains(fragment)))
      .map((path) => SourceFile(path, File(path).readAsStringSync()))
      .toList(growable: false);
}

/// مسارات الشيفرة المولَّدة — تُستثنى حيث لا معنى لفحصها، وتُفحص حيث يكون
/// الفحص هو الغرض (مثل: أن يبقى المبلغ نصّاً في نماذج المخطط).
const List<String> generatedPaths = <String>[
  'lib/data/api/generated/',
  'lib/l10n/generated/',
  '.g.dart',
  '.freezed.dart',
];
