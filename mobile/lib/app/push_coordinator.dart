import 'dart:async';

import '../domain/common/failure.dart';
import '../domain/notifications/entities/push_notification.dart';
import '../domain/notifications/repositories/push_service.dart';
import '../domain/notifications/usecases/register_this_device.dart';
import '../domain/notifications/usecases/resolve_push_destination.dart';
import 'routes.dart';

/// يربط الإشعارات بالتنقّل: يسجّل الجهاز، ويفتح الشاشة الصحيحة عند الضغط.
///
/// أرقّ ما فيه هو **الإشعار الذي أقلع منه التطبيق وهو مغلق**: ليس حدثاً في
/// مجرى لأن التطبيق لم يكن يعمل ليسمعه، فيُسأل عنه مرة واحدة عند البدء. وهي
/// أكثر حالات H6 شيوعاً — إشعار يصل والجوال في الجيب.
///
/// إشعار المقدمة **لا يفتح شاشة**: قفزةٌ تحت إصبع مستخدم يزايد الآن تنقله عن
/// شاشته في أسوأ لحظة. يُمرَّر إلى `onForeground` لتعرضه الواجهة، والفتح قراره.
final class PushCoordinator {
  PushCoordinator({
    required PushService push,
    required RegisterThisDevice register,
    required void Function(String location) navigate,
    void Function(PushNotification notification)? onForeground,
  }) : _push = push,
       _register = register,
       _navigate = navigate,
       _onForeground = onForeground;

  final PushService _push;
  final RegisterThisDevice _register;
  final void Function(String location) _navigate;
  final void Function(PushNotification notification)? _onForeground;

  final List<StreamSubscription<Object?>> _subscriptions = [];

  /// يُستدعى مرة واحدة بعد بناء التوجيه.
  ///
  /// يرجع نتيجة التسجيل مسمّاة — «الإشعارات لا تصل» شكوى لا تُشخَّص بدونها.
  Future<PushRegistrationOutcome> start() async {
    _subscriptions
      ..add(_push.notificationTaps().listen(_open))
      ..add(_register.followTokenRotations());

    final onForeground = _onForeground;
    if (onForeground != null) {
      _subscriptions.add(_push.foregroundMessages().listen(onForeground));
    }

    final launcher = await _push.initialNotification();
    if (launcher != null) _open(launcher);

    return registerNow();
  }

  /// يسجّل هذا الجهاز الآن — **ويُنادى ثانيةً بعد كلّ دخول**. T949
  ///
  /// [start] يجري مرّةً واحدةً عند الإقلاع، وترتيبُ [RegisterThisDevice]
  /// يقرأ الجلسةَ أوّلاً: فمن فتح التطبيقَ ولم يدخل بعد يُرجِع `notSignedIn`
  /// وينتهي الأمر. ثمّ يدخل بعد دقيقة — **ولا شيء يُعيد المحاولة**، فيبقى
  /// بلا صفٍّ في `notifications.Device` حتى يُغلق التطبيقَ ويفتحه.
  ///
  /// وهذا بالضبط ما تقرؤه لوحةُ التحكّم «أجهزة مسجَّلة: ٠» بينما العملاء
  /// داخلون: الربطُ سليم، والتوكن موجود، والنداءُ لم يحدث. فصار الدخولُ
  /// نفسُه يُطلق التسجيل (`main.dart`).
  Future<PushRegistrationOutcome> registerNow() async {
    try {
      return await _register();
    } on Failure {
      // فشل التسجيل لا يمنع التطبيق من العمل، ولا يُبتلع: يخرج باسمه.
      return PushRegistrationOutcome.serverRefused;
    }
  }

  void _open(PushNotification message) =>
      _navigate(PushLocations.of(ResolvePushDestination.call(message)));

  Future<void> dispose() async {
    for (final subscription in _subscriptions) {
      await subscription.cancel();
    }
    _subscriptions.clear();
  }
}
