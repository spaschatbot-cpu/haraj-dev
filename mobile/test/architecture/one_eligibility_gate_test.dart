import 'package:flutter_test/flutter_test.dart';

import '../support/source_files.dart';

/// نظير `ops/checks/one_eligibility_gate.py` في التطبيق.
///
/// الخلفية تحرس بوابة الأهلية بفحص آلي يرفض قارئاً ثانياً لتلك الحقائق، لأن
/// القاعدة التي يحرسها المراجع وحده تتسرّب عند أول يوم ضاغط. **القناة الثالثة
/// تحتاج الحارس نفسه**: في v1 كانت الصفحة الرئيسية وحدها فيها ستة مسارات
/// لإرسال مزايدة، وكل قاعدة جديدة كان لا بدّ أن تُضاف في ستة أماكن وإلا سُرّبت
/// من واحد.
///
/// المعيار J7 أن يُرفض العميل **بنفس السبب المُعدَّد حرفياً** في التطبيق
/// والويب. الطريقة الوحيدة لضمانه ألّا يوجد في التطبيق ما ينتج سبباً.
void main() {
  List<SourceFile> biddingSources() => readLibrarySources(
    excluding: generatedPaths,
  ).where((file) => file.path.contains('/bidding/')).toList();

  test('شيفرة المزايدة موجودة أصلاً — الحارس لا يمرّ على فراغ', () {
    expect(biddingSources().length, greaterThan(5));
  });

  test('لا مفردة أهلية واحدة في شيفرة المزايدة', () {
    // الأسماء مأخوذة من `apps/bidding/eligibility.py`: ما تقرؤه تلك الدالة
    // لتقرّر. ظهور أيٍّ منها هنا يعني أن التطبيق بدأ يقرأ الحقائق نفسها —
    // وهي الخطوة الأولى نحو قرارٍ ثانٍ يفترق عن الأول.
    const vocabulary = <String>[
      'eligib',
      'canBid',
      'mayBid',
      'allowedToBid',
      'minimumBid',
      'minBid',
      'nextValidBid',
      'deposit',
      'insurance',
      'outstandingDues',
      'unpaidDues',
      'auctionOpen',
      'biddingOpen',
    ];

    final offenders = <String>[];
    for (final file in biddingSources()) {
      final code = file.withoutComments.toLowerCase();
      for (final word in vocabulary) {
        if (code.contains(word.toLowerCase())) {
          offenders.add('${file.path}: $word');
        }
      }
    }

    expect(
      offenders,
      isEmpty,
      reason:
          'check_eligibility في الخلفية نقطة القرار الوحيدة. '
          'المخالفات: $offenders',
    );
  });

  test('تأكيد الخفض يُرفع في موضع واحد فقط في التطبيق كله', () {
    // كل موضع إضافي مسارٌ آخر يستطيع أن يخفض مزايدة، وF3 معناها أن يوجد
    // مسارٌ واحد يمرّ من تأكيد المستخدم بعد رفض الخادم.
    final occurrences = <String>[];
    for (final file in readLibrarySources(excluding: generatedPaths)) {
      for (final (index, line) in file.withoutComments.split('\n').indexed) {
        if (line.contains('confirmLower: true')) {
          occurrences.add('${file.path}:${index + 1}');
        }
      }
    }

    expect(
      occurrences,
      hasLength(1),
      reason: 'مواضع رفع علم الخفض: $occurrences',
    );
  });

  test('لا نقطة API للمزايدة خارج العميل المولَّد', () {
    // مسارٌ مكتوب نصّاً في شاشة هو نقطة ثانية لا يراها المخطط ولا الحارس.
    final offenders = <String>[];
    for (final file in readLibrarySources(excluding: generatedPaths)) {
      final code = file.withoutComments;
      if (RegExp(r"""['"]/api/v1/(vehicles/.*bids|bids)""").hasMatch(code)) {
        offenders.add(file.path);
      }
    }

    expect(offenders, isEmpty, reason: 'مسارات مكتوبة بيد: $offenders');
  });
}
