import 'dart:io';

import 'package:flutter_test/flutter_test.dart';

/// كل مسار ينادِيه التطبيق يخدمه الخادم — يُقارَن حرفاً بحرف، لا بالذاكرة.
///
/// المسار الذي يعرفه العميل المولَّد يأتي من المخطط المؤقّت
/// (`openapi/haraj-mock.yaml`)، والذي يخدمه الخادم مكتوب في مخططه المثبَّت
/// (`backend/openapi/schema.yaml`). لا شيء كان يقارن الاثنين، فافترقا بصمت في
/// موضعين، وكلاهما مرّ أخضر لأن كل اختبار في التطبيق يعمل على واجهة مزيَّفة لا
/// على موجّه Django:
///
/// * **الشرطة الأخيرة.** ثمانية عشر مساراً كُتبت بلا شرطة (`/api/v1/devices`)
///   والخلفية تعرّفها كلها بشرطة، و`CommonMiddleware` مفعَّل و`APPEND_SLASH`
///   افتراضه `True`. فـ`POST /api/v1/vehicles/12/bids` لا يُنفَّذ: يردّ الخادم
///   301 إلى `/bids/`، ويضيع جسم الطلب في التحويل. المزايدة لا تصل أصلاً.
/// * **أسماء لا وجود لها.** `wallet/topup-intents` والخادم يخدم
///   `wallet/topups/`، و`participations` ولم يكن للخادم نقطة بهذا الاسم —
///   404 على «اشحن بالبطاقة» و«مشاركاتي».
///
/// لماذا يُقارَن المسار وحده: بقيّة الفرق بين المخططين معروف ومكتوب في
/// `specs/008-flutter-app/tasks.md` (معرّفات نصّية، `page`/`page_size`،
/// أسماء حقول)، ويُوفَّق مرة واحدة عند تثبيت T621. أما المسار فليس فرقاً في
/// الشكل: مسارٌ لا يخدمه الخادم شاشةٌ لا تعمل، اليوم لا بعد T621.
///
/// وحين يُبدَّل مصدر التوليد إلى مخطط الخادم يبقى هذا الاختبار على حاله ويصير
/// تحصيل حاصل — وهذا هو المطلوب من حارس.
void main() {
  final schema = File('../backend/openapi/schema.yaml');
  final clients = Directory('lib/data/api/generated/clients');

  /// `{vehicleId}` و`{id}` اسمان لشيء واحد: متغيّر في القالب. المقارنة على
  /// الشكل لا على التسمية، وإلا سقط الاختبار على فرق لا يراه أي خادم.
  String shape(String path) => path.replaceAll(RegExp(r'\{[^}]*\}'), '{}');

  test(
    'المخطط المثبَّت والعميل المولَّد موجودان — الحارس لا يمرّ على فراغ',
    () {
      expect(schema.existsSync(), isTrue, reason: 'لم يوجد ${schema.path}');
      expect(clients.existsSync(), isTrue, reason: 'لم يوجد ${clients.path}');
    },
  );

  test('لا مسار في العميل المولَّد بلا نظير في مخطط الخادم', () {
    final served = schema
        .readAsLinesSync()
        .map((line) => RegExp(r'^  (/api/v1/\S*):$').firstMatch(line))
        .whereType<RegExpMatch>()
        .map((match) => shape(match.group(1)!))
        .toSet();

    expect(
      served.length,
      greaterThan(20),
      reason: 'قراءة مسارات الخادم أعطت ${served.length} — الحارس صار أعمى.',
    );

    final called = <String, String>{};
    for (final file in clients.listSync().whereType<File>()) {
      final path = file.path.replaceAll(r'\', '/');
      if (!path.endsWith('.dart') || path.endsWith('.g.dart')) continue;
      for (final match in RegExp(
        r"""@(?:GET|POST|PUT|PATCH|DELETE)\('([^']+)'\)""",
      ).allMatches(file.readAsStringSync())) {
        called[match.group(1)!] = path;
      }
    }

    expect(
      called.length,
      greaterThan(20),
      reason: 'لم تُقرأ مسارات العميل — الحارس صار أعمى.',
    );

    final orphans = <String>[
      for (final entry in called.entries)
        if (!served.contains(shape(entry.key)))
          '${entry.key}  (${entry.value})',
    ];

    expect(
      orphans,
      isEmpty,
      reason:
          'مسارات ينادِيها التطبيق ولا يخدمها الخادم — 404 أو 301 على شاشة '
          'حيّة:\n${orphans.join('\n')}',
    );
  });

  test('لا مسار في العميل بلا شرطة أخيرة', () {
    // مذكور صراحةً وإن كان الاختبار أعلاه يلتقطه: الشرطة الغائبة تعطي 301 لا
    // 404، والفرق أن التحويل **يبدو ناجحاً** في السجلّ ويضيع فيه جسم الـPOST.
    // فشلٌ باسمه أسرع في القراءة من فشل يقول «لا نظير له».
    final offenders = <String>[];
    for (final file in clients.listSync().whereType<File>()) {
      final path = file.path.replaceAll(r'\', '/');
      if (!path.endsWith('.dart') || path.endsWith('.g.dart')) continue;
      for (final match in RegExp(
        r"""@(?:GET|POST|PUT|PATCH|DELETE)\('([^']+)'\)""",
      ).allMatches(file.readAsStringSync())) {
        if (!match.group(1)!.endsWith('/')) {
          offenders.add('${match.group(1)}  ($path)');
        }
      }
    }

    expect(
      offenders,
      isEmpty,
      reason:
          'Django يعرّف كل مسار بشرطة و`APPEND_SLASH` مفعَّل — بلا شرطة يردّ '
          '301 بدل أن ينفّذ:\n${offenders.join('\n')}',
    );
  });
}
