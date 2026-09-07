import 'package:flutter_test/flutter_test.dart';

import '../support/source_files.dart';

/// معيار T713: **نتيجة الدفع تُسنَد من الخادم، لا من معامل في رابط العودة.**
///
/// الاختبارات السلوكية تثبت أن الشاشة تسأل الخادم. هذا الفحص يثبت الأصعب:
/// أنه **لا يوجد في شيفرة الشحن موضع يقرأ رابط العودة أصلاً**، فلا شيء
/// يمكن التلاعب به. في v1 كان `?status=paid` كافياً ليعتقد التطبيق أن الدفع
/// تمّ، ورصيدٌ تحرّك على هذا الأساس.
void main() {
  final topUpSources = readLibrarySources(
    excluding: generatedPaths,
  ).where((file) => file.path.contains('top_up')).toList(growable: false);

  test('شيفرة الشحن موجودة أصلاً — الفحص لا يمرّ على فراغ', () {
    expect(topUpSources, isNotEmpty);
  });

  test('لا قراءة لمعاملات رابط أو شظيّته في مسار الشحن', () {
    const forbidden = <String>[
      'queryParameters',
      'queryParametersAll',
      '.fragment',
      'Uri.base',
      'getInitialLink',
      'GoRouterState',
    ];

    final offenders = <String>[];
    for (final file in topUpSources) {
      final code = file.withoutComments;
      for (final token in forbidden) {
        if (code.contains(token)) offenders.add('${file.path}: $token');
      }
    }

    expect(
      offenders,
      isEmpty,
      reason:
          'العودة من البوابة تُسأل عنها نقطة الخادم بمرجع النيّة، ولا يُقرأ '
          'منها شيء: $offenders',
    );
  });

  test('طبقة العرض لا تصنع حالة نجاح لنيّة شحن', () {
    // «نجح» صفة يرسلها الخادم. لو أسندتها شاشة لنفسها لصار للنجاح مصدران،
    // وأحدهما تحت يد من يعود من البوابة.
    final offenders = readLibrarySources(excluding: generatedPaths)
        .where((file) => file.path.startsWith('lib/presentation/'))
        .where(
          (file) =>
              file.withoutComments.contains('TopUpStatus.succeeded') ||
              file.withoutComments.contains('TopUp('),
        )
        .map((file) => file.path)
        .toList();

    expect(
      offenders,
      isEmpty,
      reason: 'حالة النيّة تأتي من الخادم: $offenders',
    );
  });
}
