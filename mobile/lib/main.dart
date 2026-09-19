import 'dart:async';

import 'package:flutter/widgets.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'app/haraj_app.dart';
import 'app/providers.dart';
import 'data/notifications/push_service_factory.dart';
import 'presentation/auth/session_controller.dart';

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
  final coordinator = container.read(pushCoordinatorProvider);
  unawaited(coordinator.start());

  // **والدخولُ يُسجّل الجهازَ كذلك.** T949
  //
  // السطرُ أعلاه وحدَه كان يعني أن من فتح التطبيقَ ثمّ دخل لا يُسجَّل حتى
  // يُغلقه ويفتحه: `RegisterThisDevice` يقرأ الجلسةَ أوّلاً فيُرجِع
  // `notSignedIn`، ولا شيء يُعيد المحاولة. ولوحةُ التحكّم تقرأ ذلك
  // «أجهزة مسجَّلة: ٠» فيُظنّ العطلُ في FCM وهو في التوقيت.
  //
  // و`signedOut`/`expired` وحدَهما لا `unknown`: الانتقالُ من `unknown` هو
  // استرجاعُ جلسةٍ محفوظةٍ عند الإقلاع، و[PushCoordinator.start] يغطّيه —
  // فإدراجُه هنا طلبٌ ثانٍ بالتوكن نفسِه في كلّ إقلاع.
  container.listen<SessionState>(sessionControllerProvider, (
    previous,
    next,
  ) {
    final justSignedIn =
        next == SessionState.signedIn &&
        (previous == SessionState.signedOut ||
            previous == SessionState.expired);
    if (justSignedIn) unawaited(coordinator.registerNow());
  });
}
