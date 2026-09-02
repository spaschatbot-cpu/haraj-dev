import 'package:flutter_test/flutter_test.dart';

import '../support/source_files.dart';

/// الرموز لا تخرج من التخزين الآمن.
///
/// نسخة احتياطية للجهاز أو وصول جذر إلى مجلد التطبيق يكشفان قاعدة SQLite
/// و`SharedPreferences` كاملتين. رمز تحديث مسرَّب = جلسة مسروقة، وهو نفس نوع
/// الثغرة التي أنتجت مسار الاستيلاء على الحساب في v1.
void main() {
  final sources = readLibrarySources(excluding: generatedPaths);

  test('flutter_secure_storage يُستورد في مكان واحد فقط', () {
    final importers = sources
        .where(
          (file) =>
              file.content.contains("import 'package:flutter_secure_storage/"),
        )
        .map((file) => file.path)
        .toList();

    expect(importers, <String>[
      'lib/data/local/secure/secure_token_store.dart',
    ], reason: 'مخزن الرموز نقطة قرار واحدة (المادة ٤-٥): $importers');
  });

  test('لا رمز يُكتب في التخزين العادي', () {
    // نطاق الفحص: كل ما ليس المخزن الآمن نفسه.
    final offenders = <String>[];
    final tokenNearStorage = RegExp(
      r'(?:shared_preferences|SharedPreferences)',
      caseSensitive: false,
    );

    for (final file in sources) {
      if (tokenNearStorage.hasMatch(file.withoutComments)) {
        offenders.add(file.path);
      }
    }

    expect(
      offenders,
      isEmpty,
      reason:
          'SharedPreferences ليس مكاناً لأي سرّ، ولا يوجد سبب آخر لاستعماله '
          'في هذه البذرة: $offenders',
    );
  });

  test('جدول الكاش لا يحمل عموداً للرموز', () {
    final schema = sources
        .firstWhere((file) => file.path.endsWith('cache/cache_database.dart'))
        .withoutComments;

    for (final forbidden in <String>['token', 'Token', 'refresh', 'access']) {
      expect(
        schema.contains(forbidden),
        isFalse,
        reason: 'قاعدة الكاش تُقرأ من نسخة احتياطية — لا سرّ فيها ($forbidden)',
      );
    }
  });
}
