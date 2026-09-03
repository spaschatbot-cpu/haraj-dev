import 'dart:async';

import 'package:flutter/widgets.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'app/haraj_app.dart';
import 'app/providers.dart';
import 'data/notifications/push_service_factory.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();

  // تهيئة مزوّد الإشعارات قبل الرسم: الجهاز الذي أقلع من إشعار يُسأل عن ذلك
  // الإشعار مرة واحدة، وهي أكثر حالات H6 شيوعاً.
  final container = ProviderContainer(
    overrides: [
      pushServiceProvider.overrideWithValue(await resolvePushService()),
    ],
  );

  runApp(
    UncontrolledProviderScope(container: container, child: const HarajApp()),
  );

  // بعد `runApp` لا قبله: التسجيل والتنقّل يحتاجان توجيهاً مبنيّاً، وانتظارهما
  // قبل الرسم يعرض شاشة بيضاء بقدر ما تأخذ الشبكة. النتيجة مسمّاة في
  // `PushRegistrationOutcome` ولا ترمي، فلا فرع صامت هنا.
  unawaited(container.read(pushCoordinatorProvider).start());
}
