import 'package:flutter_test/flutter_test.dart';
import 'package:haraj_mobile/app/push_coordinator.dart';
import 'package:haraj_mobile/app/router.dart' show buildRouter;
import 'package:haraj_mobile/app/routes.dart';
import 'package:haraj_mobile/domain/common/failure.dart';
import 'package:haraj_mobile/domain/notifications/entities/push_destination.dart';
import 'package:haraj_mobile/domain/notifications/entities/push_notification.dart';
import 'package:haraj_mobile/domain/notifications/usecases/register_this_device.dart';
import 'package:haraj_mobile/presentation/activity/my_activity_screen.dart'
    show MyActivityTab;

import '../support/fake_push.dart';

/// معيار القبول H6 من طرف التنقّل: الحمولة تصل، فينتقل التطبيق إلى العنوان
/// الصحيح — والعنوان من `Routes` نفسها التي يركّب عليها التوجيه، لا نصّاً حرّاً.
void main() {
  ({
    PushCoordinator coordinator,
    FakePushService push,
    List<String> visited,
    List<PushNotification> foreground,
  })
  build({PushNotification? launcher, bool signedIn = true}) {
    final push = FakePushService(launchNotification: launcher);
    final visited = <String>[];
    final foreground = <PushNotification>[];

    return (
      coordinator: PushCoordinator(
        push: push,
        register: RegisterThisDevice(
          push: push,
          registry: RecordingDeviceRegistry(),
          auth: FakeAuthRepository(signedIn: signedIn),
        ),
        navigate: visited.add,
        onForeground: foreground.add,
      ),
      push: push,
      visited: visited,
      foreground: foreground,
    );
  }

  test('ضغط إشعار مزايدة يفتح المركبة', () async {
    final it = build();
    await it.coordinator.start();

    it.push.tapController.add(
      const PushNotification(
        data: {'type': 'outbid', 'auction_id': '12', 'vehicle_id': '340'},
      ),
    );
    await Future<void>.delayed(Duration.zero);

    expect(it.visited, ['/vehicles/340']);

    await it.coordinator.dispose();
    await it.push.close();
  });

  test('إشعار أقلع منه التطبيق وهو مغلق يفتح شاشته', () async {
    // أكثر حالات H6 شيوعاً: إشعار يصل والجوال في الجيب. ليس حدثاً في مجرى —
    // التطبيق لم يكن يعمل ليسمعه — فيُسأل عنه مرة واحدة عند البدء.
    final it = build(
      launcher: const PushNotification(
        data: {'type': 'invoice_due', 'invoice_id': 'INV-9'},
      ),
    );

    await it.coordinator.start();

    expect(it.visited, [Routes.myActivityTab(MyActivityTab.invoices)]);

    await it.coordinator.dispose();
    await it.push.close();
  });

  test('إشعار المقدمة لا ينقل المستخدم عن شاشته', () async {
    // مستخدم يزايد الآن وإصبعه على الزرّ؛ قفزةٌ تحته تفقده اللحظة التي تعنيه.
    final it = build();
    await it.coordinator.start();

    const message = PushNotification(
      data: {'type': 'outbid', 'vehicle_id': '7'},
      body: 'زُوِّد عليك',
    );
    it.push.foregroundController.add(message);
    await Future<void>.delayed(Duration.zero);

    expect(it.visited, isEmpty);
    expect(it.foreground, [message]);

    await it.coordinator.dispose();
    await it.push.close();
  });

  test('نوع لا نعرفه يفتح الرئيسية ولا يترك المستخدم بلا شيء', () async {
    final it = build();
    await it.coordinator.start();

    it.push.tapController.add(
      const PushNotification(data: {'type': 'not_shipped_yet'}),
    );
    await Future<void>.delayed(Duration.zero);

    expect(it.visited, [Routes.homePath]);

    await it.coordinator.dispose();
    await it.push.close();
  });

  test('البدء يرجع نتيجة التسجيل مسمّاة', () async {
    final it = build(signedIn: false);

    expect(await it.coordinator.start(), PushRegistrationOutcome.notSignedIn);

    await it.coordinator.dispose();
    await it.push.close();
  });

  test('رفض الخادم للتسجيل لا يُسقط الإقلاع', () async {
    // `start()` يُهمَل انتظاره في `main.dart`؛ عطبٌ يخرج منه يصير خطأ غير
    // ملتقَط عند الإقلاع.
    final push = FakePushService();
    final registry = RecordingDeviceRegistry()
      ..failWith = const TransportFailure(TransportProblem.offline);
    final coordinator = PushCoordinator(
      push: push,
      register: RegisterThisDevice(
        push: push,
        registry: registry,
        auth: FakeAuthRepository(),
      ),
      navigate: (_) {},
    );

    expect(await coordinator.start(), PushRegistrationOutcome.serverRefused);

    await coordinator.dispose();
    await push.close();
  });

  test('المسارات التي يفتحها الإشعار هي مسارات التوجيه نفسها', () {
    // مسار مكتوب نصّاً في مكانين يفترق فيهما عند أول تعديل، فيرى المستخدم
    // «مسار غير موجود» بعد ضغطه إشعاراً (المادة ٤-٥).
    expect(PushLocations.of(const PushDestination.home()), Routes.homePath);
    expect(PushLocations.of(const PushDestination.bids()), Routes.bidsPath);
    expect(PushLocations.of(const PushDestination.wallet()), Routes.walletPath);
    expect(
      PushLocations.of(const PushDestination.invoice()),
      Routes.myActivityTab(MyActivityTab.invoices),
    );
    expect(
      PushLocations.of(const PushDestination.auction('12')),
      Routes.auctionPath.replaceAll(':auctionId', '12'),
    );
    expect(
      PushLocations.of(const PushDestination.vehicle('340')),
      Routes.vehiclePath.replaceAll(':vehicleId', '340'),
    );
    expect(
      PushLocations.of(const PushDestination.invoice(invoiceId: 'INV-9')),
      PushLocations.of(const PushDestination.invoice()),
    );
  });

  test('كل عنوان يبنيه الإشعار تجد له شجرة التوجيه مساراً', () {
    // مطابقة النصّ بنصّ ثابت لا تكفي: مقارنة عنوانٍ بثابتٍ في `Routes` تمرّ
    // وإن لم يكن لذلك الثابت مسار مسجَّل أصلاً، فيضغط المستخدم الإشعار
    // ويهبط على صفحة «مسار غير موجود» بدل شاشته. من يسأل هنا هو الموجّه.
    final router = buildRouter();

    const destinations = <PushDestination>[
      PushDestination.home(),
      PushDestination.bids(),
      PushDestination.wallet(),
      PushDestination.invoice(),
      PushDestination.invoice(invoiceId: 'INV-9'),
      PushDestination.auction('12'),
      PushDestination.vehicle('340'),
    ];

    // وجهة جديدة بلا سطر هنا تمرّ صامتة، فيبقى نوع إشعارٍ كاملٌ بلا شاشة.
    expect(
      destinations.map((destination) => destination.target).toSet(),
      PushTarget.values.toSet(),
    );

    for (final destination in destinations) {
      final location = PushLocations.of(destination);
      expect(
        router.configuration.findMatch(Uri.parse(location)).isError,
        isFalse,
        reason: '$destination بنى «$location» ولا مسار له',
      );
    }

    router.dispose();
  });
}
