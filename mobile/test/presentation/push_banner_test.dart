import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:haraj_mobile/core/environment.dart';
import 'package:haraj_mobile/domain/notifications/entities/push_notification.dart';
import 'package:haraj_mobile/l10n/generated/app_localizations.dart';
import 'package:haraj_mobile/presentation/common/push_banner.dart';

/// T718 — «كل رسالة صادرة من بيئة غير الإنتاج تحمل اسمها» (المادة ٥-٦).
///
/// اللافتة في زاوية الشاشة لا تكفي: إشعار المزايدة يصل والتطبيق في الخلفية،
/// فلا شاشة معه ولا لافتة. في v1 وصلت رسالة اختبار إلى عميل حقيقي فتصرّف على
/// أساسها.
void main() {
  const outbid = PushNotification(
    data: {'type': 'outbid', 'vehicle_id': '7'},
    title: 'مزايدة',
    body: 'زُوِّد عليك في مركبة ٧',
  );

  Future<({ScaffoldMessengerState messenger, AppLocalizations l10n})> pumpHost(
    WidgetTester tester,
  ) async {
    late ScaffoldMessengerState messenger;
    late AppLocalizations l10n;

    await tester.pumpWidget(
      MaterialApp(
        locale: const Locale('ar'),
        localizationsDelegates: AppLocalizations.localizationsDelegates,
        supportedLocales: AppLocalizations.supportedLocales,
        home: Builder(
          builder: (context) {
            messenger = ScaffoldMessenger.of(context);
            l10n = AppLocalizations.of(context);
            return const Scaffold(body: SizedBox.shrink());
          },
        ),
      ),
    );

    return (messenger: messenger, l10n: l10n);
  }

  testWidgets('رسالة من بيئة تجريب تحمل اسم بيئتها', (tester) async {
    final it = await pumpHost(tester);

    showPushBanner(
      it.messenger,
      notification: outbid,
      l10n: it.l10n,
      environment: AppEnvironment.staging,
      onOpen: () {},
    );
    await tester.pump();

    expect(
      find.text(
        it.l10n.environmentStampedMessage(
          it.l10n.environmentStaging,
          'زُوِّد عليك في مركبة ٧',
        ),
      ),
      findsOneWidget,
    );
  });

  testWidgets('رسالة الإنتاج بلا ختم — العميل الحقيقي لا يحتاج تحذيراً', (
    tester,
  ) async {
    final it = await pumpHost(tester);

    showPushBanner(
      it.messenger,
      notification: outbid,
      l10n: it.l10n,
      environment: AppEnvironment.production,
      onOpen: () {},
    );
    await tester.pump();

    expect(find.text('زُوِّد عليك في مركبة ٧'), findsOneWidget);
  });

  testWidgets('النصّ يُعرض كما كتبه الخادم بلا صياغة ثانية', (tester) async {
    // من كتب القاعدة كتب نصّها؛ صياغة ثانية في التطبيق تنحرف عنها فيسمع العميل
    // جوابين لحدث واحد.
    final it = await pumpHost(tester);

    showPushBanner(
      it.messenger,
      notification: outbid,
      l10n: it.l10n,
      environment: AppEnvironment.production,
      onOpen: () {},
    );
    await tester.pump();

    expect(find.textContaining('زُوِّد عليك في مركبة ٧'), findsOneWidget);
  });

  testWidgets('الفتح قرار المستخدم لا قفزة تحت إصبعه', (tester) async {
    final it = await pumpHost(tester);
    var opened = 0;

    showPushBanner(
      it.messenger,
      notification: outbid,
      l10n: it.l10n,
      environment: AppEnvironment.production,
      onOpen: () => opened++,
    );
    await tester.pumpAndSettle();

    expect(opened, 0);

    await tester.tap(find.text(it.l10n.pushOpen));
    await tester.pump();

    expect(opened, 1);
  });

  testWidgets('إشعار بيانات صامت لا يعرض شيئاً، والحالة مسمّاة', (
    tester,
  ) async {
    final it = await pumpHost(tester);

    final shown = showPushBanner(
      it.messenger,
      notification: const PushNotification(data: {'type': 'hold_released'}),
      l10n: it.l10n,
      environment: AppEnvironment.staging,
      onOpen: () {},
    );
    await tester.pump();

    expect(shown, isFalse);
    expect(find.byType(SnackBar), findsNothing);
  });
}
