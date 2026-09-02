import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:yaml/yaml.dart';

/// T702: «ممنوع كتابة نماذج يدوياً» — العميل كله من المخطط.
///
/// الفحص هنا بنيوي لا سلوكي: يتأكد أن كل ملف تحت مجلد الإخراج مولَّد فعلاً،
/// وأن مجلد الإخراج هو نفسه المعلن في `swagger_parser.yaml`. نموذج مكتوب بيد
/// يُدسّ بين المولَّدات هو بالضبط ما يجعل إعادة التوليد تمحو عملاً ظنّ صاحبه
/// أنه محفوظ.
void main() {
  const generatedDirectory = 'lib/data/api/generated';

  test('مجلد الإخراج هو المعلن في swagger_parser.yaml', () {
    final config =
        loadYaml(File('swagger_parser.yaml').readAsStringSync()) as YamlMap;
    final section = config['swagger_parser'] as YamlMap;

    expect(section['output_directory'], generatedDirectory);
    expect(
      File(section['schema_path'] as String).existsSync(),
      isTrue,
      reason: 'مسار المخطط في الإعداد يجب أن يشير إلى ملف موجود',
    );
  });

  test('كل ملف في مجلد العميل يحمل ترويسة «مولَّد — لا تُعدَّل»', () {
    final handWritten = Directory(generatedDirectory)
        .listSync(recursive: true)
        .whereType<File>()
        .where((file) => file.path.endsWith('.dart'))
        .where((file) => !file.readAsStringSync().contains('GENERATED CODE'))
        .map((file) => file.path)
        .toList();

    expect(
      handWritten,
      isEmpty,
      reason: 'ملفات مكتوبة بيد داخل مجلد المولَّد: $handWritten',
    );
  });

  test('العميل مولَّد فعلاً — لا مجلد فارغ يمرّ بصمت', () {
    final models = Directory(
      '$generatedDirectory/models',
    ).listSync().whereType<File>().where((file) => file.path.endsWith('.dart'));

    expect(models.length, greaterThan(20));
  });
}
