import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:haraj_mobile/app/providers.dart';
import 'package:haraj_mobile/domain/common/failure.dart';
import 'package:haraj_mobile/domain/profile/entities/customer_profile.dart';

import '../support/fake_repositories.dart';
import '../support/pump_app.dart';

/// T715 — الملف الشخصي، ومعيار قبوله: «الحقول المقفولة تظهر مقفولة بسببها».
void main() {
  const phoneLock = LockedField(
    field: 'phone',
    reason: 'رقم الجوال يتغيّر بتأكيد رمزين — من صفحة تغيير رقم الجوال.',
  );
  const nationalIdLock = LockedField(
    field: 'national_id',
    reason: 'رقم الهوية مثبَّت ولا يمكن تغييره. راجع الدعم لو فيه خطأ.',
  );

  Future<void> openProfile(
    WidgetTester tester, {
    required FakeProfileRepository profile,
    FakeAuthRepository? auth,
  }) async {
    await pumpApp(
      tester,
      overrides: [
        authRepositoryProvider.overrideWithValue(
          auth ?? FakeAuthRepository(storedSession: true),
        ),
        profileRepositoryProvider.overrideWithValue(profile),
      ],
      location: '/profile',
    );
  }

  testWidgets('الحقل المقفول يظهر بسببه كما كتبه الخادم', (tester) async {
    final profile = FakeProfileRepository(
      profile: sampleProfile(
        locked: const <LockedField>[phoneLock, nationalIdLock],
        nationalId: '1000000008',
        nationalIdVerified: true,
      ),
    );

    await openProfile(tester, profile: profile);

    expect(find.text(phoneLock.reason), findsOneWidget);
    expect(find.text(nationalIdLock.reason), findsOneWidget);
    // ولا حقل إدخال للهوية ما دامت مقفولة.
    expect(find.widgetWithText(TextField, 'رقم الهوية'), findsNothing);
  });

  testWidgets('هوية غير مثبَّتة تبقى قابلة للتصحيح من الشاشة', (tester) async {
    // نصف T606 الثاني: من أدخلها خطأً يصحّحها بنفسه. في v1 كان يتصل بالدعم.
    final profile = FakeProfileRepository(
      profile: sampleProfile(
        locked: const <LockedField>[phoneLock],
        nationalId: '1000000001',
      ),
    );

    await openProfile(tester, profile: profile);

    expect(find.widgetWithText(TextField, 'رقم الهوية'), findsOneWidget);
    expect(find.text('تثبيت رقم الهوية'), findsOneWidget);
    expect(find.text(nationalIdLock.reason), findsNothing);
  });

  testWidgets('رفض تثبيت الهوية يظهر برسالة الخادم بلا مسح النموذج', (
    tester,
  ) async {
    final profile =
        FakeProfileRepository(
            profile: sampleProfile(locked: const <LockedField>[phoneLock]),
          )
          ..writeFailure = const ApiFailure(
            code: 'national_id_invalid',
            message: 'رقم الهوية غير صحيح.',
            statusCode: 409,
          );

    await openProfile(tester, profile: profile);
    await tester.enterText(
      find.widgetWithText(TextField, 'رقم الهوية'),
      '1234567890',
    );
    await tester.tap(find.text('تثبيت رقم الهوية'));
    await tester.pumpAndSettle();

    expect(find.text('رقم الهوية غير صحيح.'), findsOneWidget);
    // ما كتبه المستخدم باقٍ ليصحّحه، لا ليعيد كتابته.
    expect(find.text('1234567890'), findsOneWidget);
  });

  testWidgets('حفظ الاسم يرسل ما في الحقل ويقول إنه حُفظ', (tester) async {
    final profile = FakeProfileRepository(
      profile: sampleProfile(locked: const <LockedField>[phoneLock]),
    );

    await openProfile(tester, profile: profile);
    await tester.enterText(
      find.widgetWithText(TextField, 'الاسم'),
      'الاسم الجديد',
    );
    await tester.tap(find.text('حفظ'));
    await tester.pumpAndSettle();

    expect(profile.savedFullName, 'الاسم الجديد');
    // البريد يُرسل كما هو ولا يُمسح لأنه لم يُلمس: PATCH بحقل واحد ناقص
    // يمسح الآخر عند الخادم.
    expect(profile.savedEmail, 'a@b.com');
    expect(find.text('تم الحفظ'), findsOneWidget);
  });

  testWidgets('تثبيت الهوية يرسل ما أُدخل ويعرض ما ردّ به الخادم بعده', (
    tester,
  ) async {
    final profile =
        FakeProfileRepository(
            profile: sampleProfile(
              locked: const <LockedField>[phoneLock],
              nationalId: '1000000001',
            ),
          )
          // القفل قرار الخادم بعد الكتابة، لا تخمين الشاشة أنها ثبّتت شيئاً.
          ..profileAfterWrite = sampleProfile(
            locked: const <LockedField>[phoneLock, nationalIdLock],
            nationalId: '1000000008',
            nationalIdVerified: true,
          );

    await openProfile(tester, profile: profile);
    await tester.enterText(
      find.widgetWithText(TextField, 'رقم الهوية'),
      '1000000008',
    );
    await tester.tap(find.text('تثبيت رقم الهوية'));
    await tester.pumpAndSettle();

    expect(profile.pinnedNationalId, '1000000008');
    expect(find.text(nationalIdLock.reason), findsOneWidget);
    expect(find.widgetWithText(TextField, 'رقم الهوية'), findsNothing);
  });

  testWidgets('بيانات من الكاش تظهر بعلامة آخر تحديث', (tester) async {
    final profile = FakeProfileRepository(
      profile: sampleProfile(locked: const <LockedField>[phoneLock]),
    )..fromCache = true;

    await openProfile(tester, profile: profile);

    // معيار H5: بيانات قديمة **بعلامة**، لا شاشة خطأ ولا رقم بلا تاريخ.
    expect(find.textContaining('بيانات محفوظة'), findsOneWidget);
  });

  testWidgets('تعذّر التحميل بلا كاش يعرض العطب بإعادة محاولة', (tester) async {
    final profile = FakeProfileRepository()
      ..loadFailure = const TransportFailure(TransportProblem.offline);

    await openProfile(tester, profile: profile);

    expect(find.text('لا يوجد اتصال بالإنترنت.'), findsOneWidget);
    expect(find.text('إعادة المحاولة'), findsOneWidget);
  });

  testWidgets('حالة الشركة تُقرأ من الخادم لا من عدّ الحقول', (tester) async {
    final profile = FakeProfileRepository(
      profile: sampleProfile(
        locked: const <LockedField>[phoneLock],
        hasCompanyProfile: true,
      ),
    );

    await openProfile(tester, profile: profile);

    expect(find.text('ناقصة'), findsOneWidget);
  });

  testWidgets('الخروج يعيد إلى شاشة الدخول', (tester) async {
    final auth = FakeAuthRepository(storedSession: true);
    final profile = FakeProfileRepository(
      profile: sampleProfile(locked: const <LockedField>[phoneLock]),
    );

    await pumpApp(
      tester,
      overrides: [
        authRepositoryProvider.overrideWithValue(auth),
        profileRepositoryProvider.overrideWithValue(profile),
      ],
      location: '/profile',
    );
    await tester.tap(find.byIcon(Icons.logout));
    await tester.pumpAndSettle();

    expect(auth.storedSession, isFalse);
  });
}
