import 'dart:io';

import 'package:flutter_test/flutter_test.dart';

import '../support/server_refusal_reasons.dart';

/// J7 — الرفض المُعدَّد هو نفسه في القناتين، ويُثبَت بالقراءة لا بالذاكرة.
///
/// معيار قبول T710 «اختبار لكل سبب رفض». الاختبار الذي ادّعى تحقيقه كان يعدّد
/// قائمةً من عندنا: ثمانية رموز، أربعة منها لا وجود لها في الخلفية إطلاقاً
/// (`insufficient_deposit`، `auction_not_open`، `account_suspended`،
/// `bid_below_minimum`)، وخمسة رموز حقيقية غائبة (`auction_not_live`،
/// `auction_ended`، `below_floor`، `phone_not_verified`،
/// `profile_incomplete`). ومرّ أخضر، لأن الاختبار كان يزوّد الواجهة المزيَّفة
/// بالرمز الذي يتوقّعه ثم يتحقّق أنه وصل.
///
/// وليست تلك مسألة نظافة: أي فرع مستقبلي على رمز أهلية — زرّ «وثّق جوالك» عند
/// `phone_not_verified` مثلاً — يُكتب على قائمةٍ لا تطابق الخادم فلا يُفعَّل
/// أبداً. وهو بعينه الخطأ الذي صُحِّح لـ`lower_needs_confirm` في T710 نفسها.
///
/// فالتعداد يُقرأ من مصدره: `RefusalReason` في `backend/apps/bidding/models.py`.
/// نظير `test/architecture/one_eligibility_gate_test.dart` — ذاك يمنع التطبيق
/// من **إنتاج** سبب، وهذا يضمن أنه يعرف كل سبب يُنتَج له.
void main() {
  final backendModels = File('../backend/apps/bidding/models.py');

  test('ملف تعداد الخلفية موجود — الحارس لا يمرّ على فراغ', () {
    // حارسٌ يمرّ لأنه لم يجد ما يفحصه لا يُميَّز عن حارسٍ يعمل. الحزمة تُشغَّل
    // من جذر `mobile/` داخل المستودع، والملف على مسافة مجلد واحد.
    expect(
      backendModels.existsSync(),
      isTrue,
      reason:
          'لم يوجد ${backendModels.path} — شغّل الحزمة من جذر mobile/ داخل '
          'المستودع، فالتعداد يُقرأ من الخلفية لا من نسخة عندنا.',
    );
  });

  test('تعداد أسباب الرفض في التطبيق هو تعداد الخادم حرفاً بحرف', () {
    // يُقرأ سطراً سطراً لا بتعبير نمطي واحد على الملف كله: نهايات الأسطر تختلف
    // بين المنصّات، وتعبيرٌ يعتمد على `\n\n` يمرّ على ويندوز بلا أن يجد شيئاً —
    // وحارسٌ لم يجد شيئاً يمرّ صامتاً وهو أسوأ من غيابه.
    final lines = backendModels.readAsLinesSync();
    final start = lines.indexWhere(
      (line) => line.startsWith('class RefusalReason('),
    );

    expect(
      start,
      isNonNegative,
      reason: 'لم يُعثر على RefusalReason في ملف الخلفية',
    );

    final body = <String>[];
    for (final line in lines.skip(start + 1)) {
      if (line.isNotEmpty && !line.startsWith(' ')) break;
      body.add(line);
    }

    final server = RegExp(
      r'''=\s*"([a-z_]+)"''',
    ).allMatches(body.join('\n')).map((match) => match.group(1)!).toSet();

    expect(
      server.length,
      greaterThan(5),
      reason: 'قراءة التعداد أعطت $server — تغيّر شكل الملف والحارس صار أعمى.',
    );

    final ours = serverRefusalReasons.keys.toSet();

    expect(
      ours.difference(server),
      isEmpty,
      reason:
          'رموز يعدّدها التطبيق ولا يرسلها الخادم — اختبارٌ لها اختبارٌ '
          'لشيء غير موجود.',
    );
    expect(
      server.difference(ours),
      isEmpty,
      reason:
          'أسباب رفض يرسلها الخادم ولا يغطّيها التطبيق — أضفها إلى '
          'test/support/server_refusal_reasons.dart.',
    );
  });

  test('رمز الخفض ليس من أسباب الرفض، ولا يتسلّل إلى القائمة', () {
    // `lower_needs_confirm` يكتبه `apps/bidding/services.py` لا `RefusalReason`،
    // ومساره في التطبيق حوار تأكيد لا رسالة رفض. خلطه بالقائمة كان سيجعل
    // المقارنة أعلاه تفشل بلا سبب حقيقي، أو تمرّ بعد أن يُضاف استثناء يخفي فرقاً.
    expect(serverRefusalReasons.containsKey(lowerNeedsConfirmCode), isFalse);
  });
}
