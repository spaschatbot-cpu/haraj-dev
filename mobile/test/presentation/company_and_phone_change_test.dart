import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:haraj_mobile/app/providers.dart';
import 'package:haraj_mobile/domain/common/failure.dart';
import 'package:haraj_mobile/domain/profile/entities/customer_profile.dart';

import '../support/fake_repositories.dart';
import '../support/pump_app.dart';

/// T715 — ملف الشركة والعنوان الوطني، وتغيير الجوال بتأكيد الرقمين.
void main() {
  const phoneLock = LockedField(
    field: 'phone',
    reason: 'رقم الجوال يتغيّر بتأكيد رمزين.',
  );

  const filledCompany = CompanyProfile(
    name: 'شركة الاختبار',
    representativeName: 'مفوَّض',
    commercialRegister: '1010101010',
    vatNumber: '300000000000003',
    buildingNumber: '1234',
    street: 'طريق الملك فهد',
    district: 'العليا',
    city: 'الرياض',
    postalCode: '12345',
    isComplete: true,
  );

  group('ملف الشركة', () {
    Future<FakeProfileRepository> open(
      WidgetTester tester, {
      CompanyProfile? company,
      Failure? writeFailure,
    }) async {
      final profile = FakeProfileRepository(
        profile: sampleProfile(locked: const <LockedField>[phoneLock]),
        company: company,
      )..writeFailure = writeFailure;

      await pumpApp(
        tester,
        overrides: [
          authRepositoryProvider.overrideWithValue(
            FakeAuthRepository(storedSession: true),
          ),
          profileRepositoryProvider.overrideWithValue(profile),
        ],
        location: '/profile/company',
      );
      return profile;
    }

    /// النموذج أطول من شاشة الجوال، فالزرّ تحت الطيّة — والاختبار يمرّر إليه
    /// كما يفعل المستخدم بدل أن يفترض شاشة سطح مكتب.
    Future<void> tapSave(WidgetTester tester) async {
      await tester.ensureVisible(find.text('حفظ بيانات الشركة'));
      await tester.pumpAndSettle();
      await tester.tap(find.text('حفظ بيانات الشركة'));
      await tester.pumpAndSettle();
    }

    testWidgets('حساب بلا شركة يفتح نموذج إنشاء لا رسالة خطأ', (tester) async {
      await open(tester);

      expect(
        find.textContaining('لا يوجد ملف شركة لهذا الحساب'),
        findsOneWidget,
      );
      expect(find.widgetWithText(TextField, 'اسم الشركة'), findsOneWidget);
    });

    testWidgets('الشركة القائمة تفتح بحقولها وبحالة اكتمالها من الخادم', (
      tester,
    ) async {
      await open(tester, company: filledCompany);

      expect(find.text('شركة الاختبار'), findsOneWidget);
      expect(find.text('12345'), findsOneWidget);
      expect(find.text('مكتملة'), findsOneWidget);
    });

    testWidgets('الحفظ يرسل حقول العنوان الوطني كما أُدخلت', (tester) async {
      final profile = await open(tester);

      await tester.enterText(
        find.widgetWithText(TextField, 'اسم الشركة'),
        'شركة جديدة',
      );
      await tester.enterText(
        find.widgetWithText(TextField, 'الرمز البريدي'),
        '12345',
      );
      await tapSave(tester);

      expect(profile.savedCompany?.name, 'شركة جديدة');
      expect(profile.savedCompany?.postalCode, '12345');
    });

    testWidgets('رفض «بيانات الشركة ناقصة» يظهر برسالة الخادم', (tester) async {
      // الشاشة لا تحسب الاكتمال بنفسها: شرطه قاعدة عمل لها تاريخ في الخادم
      // (إعفاء الشركات السابقة على العنوان الوطني)، ونسخة منها هنا تمنع شركة
      // قديمة من حفظ ملفها.
      await open(
        tester,
        writeFailure: const ApiFailure(
          code: 'company_profile_incomplete',
          message: 'بيانات الشركة ناقصة: السجل والرقم الضريبي والعنوان الوطني.',
          statusCode: 409,
        ),
      );

      await tapSave(tester);

      expect(
        find.text('بيانات الشركة ناقصة: السجل والرقم الضريبي والعنوان الوطني.'),
        findsOneWidget,
      );
    });
  });

  group('تغيير رقم الجوال', () {
    Future<(FakeAuthRepository, ProviderContainer)> open(
      WidgetTester tester,
    ) async {
      final auth = FakeAuthRepository(storedSession: true);
      final container = await pumpApp(
        tester,
        overrides: [
          authRepositoryProvider.overrideWithValue(auth),
          profileRepositoryProvider.overrideWithValue(
            FakeProfileRepository(
              profile: sampleProfile(locked: const <LockedField>[phoneLock]),
            ),
          ),
        ],
        location: '/profile/phone',
      );
      return (auth, container);
    }

    Future<void> sendCodes(WidgetTester tester) async {
      await tester.enterText(find.byType(TextField).first, '966500000002');
      await tester.pump();
      await tester.tap(find.text('إرسال الرمزين'));
      await tester.pumpAndSettle();
    }

    testWidgets('حقلا الرمزين لا يظهران قبل إرسالهما', (tester) async {
      await open(tester);

      expect(
        find.widgetWithText(TextField, 'الرمز المُرسَل إلى رقمك الحالي'),
        findsNothing,
      );
      expect(find.text('تأكيد التغيير'), findsNothing);
    });

    testWidgets('رمز واحد لا يكفي: الزرّ معطَّل حتى يُملأ الاثنان', (
      tester,
    ) async {
      await open(tester);
      await sendCodes(tester);

      await tester.enterText(
        find.widgetWithText(TextField, 'الرمز المُرسَل إلى رقمك الحالي'),
        '111111',
      );
      await tester.pump();

      final button = tester.widget<FilledButton>(
        find.widgetWithText(FilledButton, 'تأكيد التغيير'),
      );
      expect(
        button.onPressed,
        isNull,
        reason: 'رمز واحد صحيح لا يغيّر شيئاً — نفس قاعدة الخادم',
      );
    });

    testWidgets('نجاح التغيير ينهي الجلسة ويعيد إلى الدخول', (tester) async {
      final (auth, container) = await open(tester);
      await sendCodes(tester);

      await tester.enterText(
        find.widgetWithText(TextField, 'الرمز المُرسَل إلى رقمك الحالي'),
        '111111',
      );
      await tester.enterText(
        find.widgetWithText(TextField, 'الرمز المُرسَل إلى الرقم الجديد'),
        '222222',
      );
      await tester.pump();
      await tester.tap(find.text('تأكيد التغيير'));
      await tester.pumpAndSettle();

      // الخادم يُلغي كل الجلسات عند النجاح، والتطبيق يتصرّف بموجب ذلك بدل أن
      // ينتظر أول 401.
      expect(auth.storedSession, isFalse);
      expect(currentLocation(container), '/sign-in');
    });

    testWidgets('الرفض لا يقول أي الرمزين أخطأ — رسالة الخادم كما جاءت', (
      tester,
    ) async {
      final (auth, _) = await open(tester);
      await sendCodes(tester);

      auth.failure = const ApiFailure(
        code: 'phone_change_needs_both_codes',
        message:
            'لازم الرمزين الصحيحين — المرسَل للرقم القديم والمرسَل للجديد.',
        statusCode: 409,
      );

      await tester.enterText(
        find.widgetWithText(TextField, 'الرمز المُرسَل إلى رقمك الحالي'),
        '111111',
      );
      await tester.enterText(
        find.widgetWithText(TextField, 'الرمز المُرسَل إلى الرقم الجديد'),
        '000000',
      );
      await tester.pump();
      await tester.tap(find.text('تأكيد التغيير'));
      await tester.pumpAndSettle();

      expect(
        find.text(
          'لازم الرمزين الصحيحين — المرسَل للرقم القديم والمرسَل للجديد.',
        ),
        findsOneWidget,
      );
      expect(auth.storedSession, isTrue);
    });
  });
}
