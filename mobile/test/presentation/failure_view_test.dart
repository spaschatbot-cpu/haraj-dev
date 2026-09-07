import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:haraj_mobile/domain/common/failure.dart';
import 'package:haraj_mobile/presentation/common/failure_view.dart';

import '../support/pump_localized.dart';

/// T705 — «اعرض `message` كما جاء».
void main() {
  testWidgets('رسالة الخادم تُعرض حرفياً بلا استبدال', (tester) async {
    const message = 'لا يمكن الاسترداد: تأمينك مقفول على الفاتورة ١٢٣٤.';

    await pumpLocalized(
      tester,
      const FailureView(
        failure: ApiFailure(
          code: 'REFUND_BLOCKED_BY_INVOICE',
          message: message,
        ),
      ),
    );

    expect(find.text(message), findsOneWidget);
  });

  testWidgets('رمز الخطأ لا يظهر للمستخدم', (tester) async {
    await pumpLocalized(
      tester,
      const FailureView(
        failure: ApiFailure(
          code: 'REFUND_BLOCKED_BY_INVOICE',
          message: 'رسالة عربية.',
        ),
      ),
    );

    // الرمز للتفريع البرمجي، لا للعرض.
    expect(find.textContaining('REFUND_BLOCKED_BY_INVOICE'), findsNothing);
  });

  testWidgets('انقطاع الشبكة يستعمل نصّاً محلياً — الخادم لم يُسأل', (
    tester,
  ) async {
    await pumpLocalized(
      tester,
      const FailureView(failure: TransportFailure(TransportProblem.offline)),
    );

    expect(find.text('لا يوجد اتصال بالإنترنت.'), findsOneWidget);
  });

  testWidgets('ردّ غير مفهوم لا يُلبَّس رسالة مخترعة', (tester) async {
    await pumpLocalized(
      tester,
      const FailureView(
        failure: TransportFailure(TransportProblem.malformedResponse),
      ),
    );

    expect(find.text('وصل ردّ غير مفهوم من الخادم.'), findsOneWidget);
  });

  testWidgets('زر إعادة المحاولة يظهر عند تمرير onRetry فقط', (tester) async {
    var retries = 0;

    await pumpLocalized(
      tester,
      const FailureView(failure: TransportFailure(TransportProblem.timeout)),
    );
    expect(find.byType(FilledButton), findsNothing);

    await pumpLocalized(
      tester,
      FailureView(
        failure: const TransportFailure(TransportProblem.timeout),
        onRetry: () => retries++,
      ),
    );
    await tester.tap(find.byType(FilledButton));

    expect(retries, 1);
  });
}
