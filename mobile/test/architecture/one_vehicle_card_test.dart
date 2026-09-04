import 'package:flutter_test/flutter_test.dart';

import '../support/source_files.dart';

/// كرت المركبة يُرسَم في مكوّن واحد — نظير `ops/checks/one_vehicle_card.py`
/// في الخلفية و`ops/checks/web_one_vehicle_card.mjs` في الويب.
///
/// العطل الذي وُجد هذا الفحص لأجله، بنصّ التاسك: في v1 كانت الصفحة الرئيسية
/// وحدها فيها **أربعة** مسارات لرسم كرت المركبة وثلاث قوائم حقول، فأي حقل
/// يُضاف للمنتج يظهر في بعضها ويختفي في الباقي **بصمت** — ولم ينتبه أحد حتى
/// سأل عميل عن حقل يراه في شاشة ولا يراه في أخرى. وحين انتُبه كانت الأربعة قد
/// افترقت في أربعة اتجاهات، فلا نسخة منها تصلح مرجعاً للباقي.
///
/// **ما الذي يُحسب رسماً لكرت:** قراءة ثلاثة أو أكثر من حقول الكرت في ملف عرضٍ
/// ليس المكوّن. حقلٌ واحد شاشةٌ تذكر عنوان مركبة؛ ثلاثةٌ كرتٌ ثانٍ يُولد.
void main() {
  /// المكوّن الوحيد المسموح له برسم الكرت.
  const card = 'lib/presentation/catalog/widgets/vehicle_card.dart';

  /// ملفات مستثناة، وكلٌّ منها قرارٌ مكتوب هنا لا اسمٌ أفلت من نمط.
  const exempt = <String>[
    card,
    // صفحة المركبة نفسها: تعرض مركبة واحدة كاملةً — معرض صور وجدول مواصفات —
    // وهذا عرضٌ آخر لا نسخةٌ من الكرت. طيّها داخل المكوّن يعطي الكرت «وضعاً
    // مفصَّلاً»، ومكوّنٌ بوضعين مكوّنان يتقاسمان ملفاً.
    'lib/presentation/catalog/vehicle_screen.dart',
  ];

  /// الحقول التي يعني اجتماعها «هذا كرت مركبة».
  const cardFields = <String>[
    'thumbnailUrl',
    'reservePrice',
    'lotNumber',
    'bidsCount',
    'vehicleReservePrice',
    // العدّاد صار جزءاً من الكرت، فصار حقله من علامات «هذا كرت»: شاشةٌ ترسم
    // صورةً وسعراً وعدّاداً كرتٌ ثانٍ مهما اختلف شكله.
    'auctionEndsAt',
  ];

  /// اثنان صدفة، وثلاثة كرت. مكتوبٌ هنا كي يكون رفعه قراراً ظاهراً لا تعديلاً
  /// صامتاً في تعبير نمطي.
  const threshold = 3;

  List<String> offendersIn(Iterable<SourceFile> sources) {
    final offenders = <String>[];
    for (final file in sources.where(
      (file) =>
          file.path.startsWith('lib/presentation/') &&
          !exempt.contains(file.path),
    )) {
      final used = cardFields
          .where(
            (field) => RegExp('\\b$field\\b').hasMatch(file.withoutComments),
          )
          .toList();
      if (used.length >= threshold) {
        offenders.add('${file.path}: ${used.join(', ')}');
      }
    }
    return offenders;
  }

  test('لا كرت مركبة يُرسم خارج مكوّنه', () {
    final offenders = offendersIn(
      readLibrarySources(excluding: generatedPaths),
    );

    expect(
      offenders,
      isEmpty,
      reason:
          'استعمل presentation/catalog/widgets/vehicle_card.dart. '
          'المخالفات: $offenders',
    );
  });

  test('الفحص نفسه يمسك مخالفة مصنوعة — وإلا فهو حارس نائم', () {
    // حارسٌ يمرّ دائماً لا يُميَّز عن حارسٍ لا يعمل إلا بتجربته على مخالفة.
    const fabricated = SourceFile(
      'lib/presentation/catalog/second_card.dart',
      'Text(vehicle.title); Image(vehicle.thumbnailUrl); '
          'MoneyText(vehicle.reservePrice); Text(vehicle.lotNumber);',
    );

    expect(offendersIn(<SourceFile>[fabricated]), hasLength(1));
  });

  test('الكرت لا يعرف سعراً غير سعر الوقوف', () {
    // دليل النظام §8-3: `reserve_price` هو الحقل الوحيد لسعر المركبة. في v1
    // حُسب السعر في أربع شاشات بأربع طرق فاختلفت الأرقام أمام العميل، فأي اسم
    // آخر يحمل «سعراً» أو «مبلغاً» داخل الكرت بداية الطريق نفسه.
    final source = readLibrarySources()
        .firstWhere((file) => file.path == card)
        .withoutComments;

    expect(source.contains('reservePrice'), isTrue);

    final otherMoney =
        RegExp(
            r'\b\w*(?:Amount|Price)\b',
          ).allMatches(source).map((match) => match.group(0)!).toSet()
          ..remove('reservePrice')
          ..remove('vehicleReservePrice')
          ..remove('vehicleReservePriceUnset');

    expect(
      otherMoney,
      isEmpty,
      reason: 'سعر واحد للمركبة في كل شاشة: $otherMoney',
    );
  });
}
