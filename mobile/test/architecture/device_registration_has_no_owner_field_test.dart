import 'dart:io';

import 'package:flutter_test/flutter_test.dart';

/// ⚠️ حارس ثغرة v1 على **العقد** نفسه (T716).
///
/// ثغرة IDOR على FCM في v1: كان معرّف الحساب حقلاً في جسم التسجيل، فتسجيل جهاز
/// باسم عميل آخر كان بُعد حقلٍ واحد، وإشعارات هذه القناة تقول على ماذا يزايد
/// الرجل وبكم.
///
/// الفحص هنا على **الشيفرة المولَّدة** لا على شيفرتنا، وذلك هو الغرض: يوم يعيد
/// أحدٌ حقل المالك إلى المخطط، يسقط هذا الاختبار عند أول إعادة توليد — قبل أن
/// يكتب أحدٌ سطراً يملؤه. اختبار على مستودعنا وحده يمرّ في ذلك اليوم بسلام.
void main() {
  const owners = <String>[
    'user',
    'userId',
    'user_id',
    'account',
    'accountId',
    'ownerId',
    'phone',
  ];

  const models = <String>[
    'lib/data/api/generated/models/device_registration.dart',
    'lib/data/api/generated/models/device_unregistration.dart',
  ];

  for (final path in models) {
    test('لا حقل مالك في ${path.split('/').last}', () {
      final file = File(path);
      expect(
        file.existsSync(),
        isTrue,
        reason:
            'العقد لم يعد يولّد $path — إن تغيّر اسم النموذج فحدّث الحارس معه، '
            'ولا تحذفه.',
      );

      final fields = RegExp(r'^\s*final\s+\w+\??\s+(\w+);', multiLine: true)
          .allMatches(file.readAsStringSync())
          .map((match) => match.group(1)!)
          .toList();

      expect(fields, isNotEmpty, reason: 'لم تُقرأ حقول $path');
      for (final owner in owners) {
        expect(
          fields,
          isNot(contains(owner)),
          reason:
              'حقل «$owner» في جسم تسجيل الجهاز يعيد فتح ثغرة v1: المالك يأتي '
              'من رمز الدخول، لا من الجسم.',
        );
      }
    });
  }

  test('العقد لا يعيد رمز الجهاز في أي استجابة', () {
    // الرمز اعتماد للإرسال إلى الجهاز؛ استجابة تحمله تضعه في سجلّ وصول وفي
    // ذاكرة وسيط وفي تقرير انهيار العميل.
    final device = File(
      'lib/data/api/generated/models/device.dart',
    ).readAsStringSync();

    expect(
      RegExp(r'^\s*final\s+\w+\??\s+token;', multiLine: true).hasMatch(device),
      isFalse,
      reason: 'استجابة الجهاز تحمل الرمز — أزِله من المخطط لا من هنا.',
    );
  });
}
