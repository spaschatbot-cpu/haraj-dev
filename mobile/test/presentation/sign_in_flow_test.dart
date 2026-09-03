import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:haraj_mobile/app/providers.dart';
import 'package:haraj_mobile/domain/auth/entities/auth_session.dart';
import 'package:haraj_mobile/domain/common/failure.dart';
import 'package:haraj_mobile/domain/common/failure_codes.dart';

import '../support/fake_repositories.dart';
import '../support/pump_app.dart';

/// T706 — الدخول والتسجيل بالجوال وOTP.
///
/// كل تأكيد هنا عن **سلوك** الشاشة أمام جواب الخادم، لا عن نصّها: النصّ عربي
/// من الخادم ويُعرض كما جاء، والاختبار يتحقّق أنه ظهر كما جاء.
void main() {
  ApiFailure refusal({
    required String code,
    required String message,
    int status = 409,
    Map<String, Object?>? detail,
  }) => ApiFailure(
    code: code,
    message: message,
    statusCode: status,
    details: detail,
  );

  Future<void> submitPhone(WidgetTester tester) async {
    await tester.enterText(find.byType(TextField).first, '966500000001');
    await tester.pump();
    await tester.tap(find.text('إرسال رمز التحقق'));
    await tester.pumpAndSettle();
  }

  testWidgets('رقم صحيح ينقل إلى شاشة الرمز ويعرض الرقم الذي أُرسل إليه', (
    tester,
  ) async {
    final auth = FakeAuthRepository();
    final container = await pumpApp(
      tester,
      overrides: [authRepositoryProvider.overrideWithValue(auth)],
      location: '/sign-in',
    );

    await submitPhone(tester);

    expect(currentLocation(container), '/sign-in/code');
    expect(find.textContaining('966500000001'), findsWidgets);
  });

  testWidgets(
    'حدّ المعدّل يعرض رسالة الخادم ويعطّل الزرّ بالثواني التي قالها',
    (tester) async {
      // 429 برسالة الخادم و`retry_after`. بلا العدّاد يضغط المستخدم كل ثانية
      // على نفس الحدّ الذي رفضه.
      final auth = FakeAuthRepository()
        ..failure = refusal(
          code: FailureCodes.rateLimited,
          message: 'عدد المحاولات كبير، حاول بعد قليل',
          status: 429,
          detail: const <String, Object?>{'retry_after': 3},
        );

      await pumpApp(
        tester,
        overrides: [authRepositoryProvider.overrideWithValue(auth)],
        location: '/sign-in',
      );
      await submitPhone(tester);

      expect(find.text('عدد المحاولات كبير، حاول بعد قليل'), findsOneWidget);
      final waiting = tester.widget<TextButton>(find.byType(TextButton));
      expect(waiting.onPressed, isNull, reason: 'الزرّ معطَّل ما دامت المهلة');
      expect(find.textContaining('بعد 3 ثانية'), findsOneWidget);

      await tester.pump(const Duration(seconds: 3));
      // العدّاد اختفى من نصّ الزرّ — والمطابقة تامّة لا احتواء: رسالة الخادم
      // نفسها تحوي كلمة «بعد».
      expect(find.text('إرسال رمز التحقق'), findsOneWidget);
      expect(
        tester.widget<TextButton>(find.byType(TextButton)).onPressed,
        isNotNull,
      );
    },
  );

  testWidgets('فشل إرسال الرسالة لا ينقل إلى شاشة الرمز', (tester) async {
    // 503 من T603: لا يوجد رمز أصلاً ليُكتب، فشاشة تطلب رمزاً كذبة.
    final auth = FakeAuthRepository()
      ..failure = refusal(
        code: FailureCodes.smsUndeliverable,
        message: 'تعذّر إرسال رمز التحقق الآن. جرّب بعد قليل.',
        status: 503,
      );

    final container = await pumpApp(
      tester,
      overrides: [authRepositoryProvider.overrideWithValue(auth)],
      location: '/sign-in',
    );
    await submitPhone(tester);

    expect(currentLocation(container), '/sign-in');
    expect(
      find.text('تعذّر إرسال رمز التحقق الآن. جرّب بعد قليل.'),
      findsOneWidget,
    );
  });

  testWidgets('رمز صحيح يدخل الحساب ويترك مسار الدخول', (tester) async {
    final auth = FakeAuthRepository();
    final container = await pumpApp(
      tester,
      overrides: [authRepositoryProvider.overrideWithValue(auth)],
      location: '/sign-in',
    );
    await submitPhone(tester);

    await tester.enterText(find.byType(TextField).first, '123456');
    await tester.pump();
    await tester.tap(find.text('تأكيد ودخول'));
    await tester.pumpAndSettle();

    expect(currentLocation(container), '/');
  });

  testWidgets('كود خاطئ يعرض رسالة الخادم ويبقي المستخدم على الشاشة', (
    tester,
  ) async {
    final auth = FakeAuthRepository();
    final container = await pumpApp(
      tester,
      overrides: [authRepositoryProvider.overrideWithValue(auth)],
      location: '/sign-in',
    );
    await submitPhone(tester);

    auth.failure = refusal(code: 'otp_incorrect', message: 'الرمز غير صحيح.');
    await tester.enterText(find.byType(TextField).first, '000000');
    await tester.pump();
    await tester.tap(find.text('تأكيد ودخول'));
    await tester.pumpAndSettle();

    expect(find.text('الرمز غير صحيح.'), findsOneWidget);
    expect(currentLocation(container), '/sign-in/code');
  });

  testWidgets('فشل الإرسال عند إعادة المحاولة يُميَّز عن كود خاطئ', (
    tester,
  ) async {
    // الفرق سلوكيّ لا لفظيّ: رسالة الخادم تظهر كما جاءت، **ولا** تُفرض مهلة
    // انتظار — العطل عندنا، ومنع المستخدم من إعادة المحاولة عقوبة على شيء لم
    // يفعله. شاشة تقول «الكود غلط» والبوابة ساقطة تُبقيه يحاول إلى الأبد.
    final auth = FakeAuthRepository()
      ..delivery = CodeDelivery(
        expiresAt: DateTime.utc(2026, 9, 1, 10, 5),
        resendAfterSeconds: 0,
      );

    await pumpApp(
      tester,
      overrides: [authRepositoryProvider.overrideWithValue(auth)],
      location: '/sign-in',
    );
    await submitPhone(tester);

    auth
      ..failure = refusal(
        code: FailureCodes.smsUndeliverable,
        message: 'تعذّر إرسال رمز التحقق الآن. جرّب بعد قليل.',
        status: 503,
        // حتى لو وصلت ثوانٍ مع العطل، لا تُفرض على المستخدم.
        detail: const <String, Object?>{'retry_after': 30},
      )
      ..oneShotFailure = true;

    await tester.tap(find.text('إعادة إرسال الرمز'));
    await tester.pumpAndSettle();

    expect(
      find.text('تعذّر إرسال رمز التحقق الآن. جرّب بعد قليل.'),
      findsOneWidget,
    );
    expect(find.textContaining('بعد 30 ثانية'), findsNothing);

    final resend = tester.widget<TextButton>(
      find.widgetWithText(TextButton, 'إعادة إرسال الرمز'),
    );
    expect(
      resend.onPressed,
      isNotNull,
      reason: 'إعادة الإرسال تبقى متاحة: العطل عندنا لا عند العميل',
    );
  });

  testWidgets('رقم بلا حساب يُظهر حقل الاسم برسالة الخادم ثم يكمل', (
    tester,
  ) async {
    final auth = FakeAuthRepository();
    final container = await pumpApp(
      tester,
      overrides: [authRepositoryProvider.overrideWithValue(auth)],
      location: '/sign-in',
    );
    await submitPhone(tester);

    auth
      ..failure = refusal(
        code: FailureCodes.registrationNeedsName,
        message: 'أدخل الاسم لإنشاء الحساب.',
      )
      ..oneShotFailure = true;

    await tester.enterText(find.byType(TextField).first, '123456');
    await tester.pump();
    await tester.tap(find.text('تأكيد ودخول'));
    await tester.pumpAndSettle();

    expect(find.text('أدخل الاسم لإنشاء الحساب.'), findsOneWidget);
    expect(find.widgetWithText(TextField, 'الاسم الكامل'), findsOneWidget);

    // الرمز الذي بيد المستخدم ما زال صالحاً: الخادم رفض قبل أن يستهلكه.
    await tester.enterText(
      find.widgetWithText(TextField, 'الاسم الكامل'),
      'عميل جديد',
    );
    await tester.pump();
    await tester.tap(find.text('تأكيد ودخول'));
    await tester.pumpAndSettle();

    expect(auth.lastFullName, 'عميل جديد');
    expect(currentLocation(container), '/');
  });

  testWidgets('شاشة الرمز بلا رمز مُرسَل تعيد إلى الخطوة الأولى', (
    tester,
  ) async {
    final container = await pumpApp(
      tester,
      overrides: [
        authRepositoryProvider.overrideWithValue(FakeAuthRepository()),
      ],
      location: '/sign-in/code',
    );

    expect(currentLocation(container), '/sign-in');
  });
}
