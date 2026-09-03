import '../../domain/notifications/entities/push_notification.dart';
import '../../domain/notifications/repositories/push_service.dart';

/// بناء بلا إعداد Firebase: لا رمز، ولا إشعارات، ولا انهيار.
///
/// المادة ٥-٣ تُبقي إعداد المزوّد خارج المستودع، فالبناء المحلي وبناء المساهم
/// الجديد لا يجدان `google-services.json`. الخياران عندئذٍ: أن يسقط التطبيق عند
/// الإقلاع، أو أن تُطفأ الإشعارات وحدها ويبقى كل شيء آخر يعمل. الثاني هو
/// الصحيح — ويتّسق مع المادة ٢-٦: التكامل مطفأ افتراضياً.
///
/// وهو **ليس** فرعاً صامتاً: `RegisterThisDevice` يرجع `noToken` باسمها، فتُقرأ
/// الحالة في السجلّ بدل أن تُقرأ «الإشعارات لا تصل ولا نعرف لماذا».
final class UnconfiguredPushService implements PushService {
  const UnconfiguredPushService({this.platform = DevicePlatform.android});

  @override
  final DevicePlatform platform;

  @override
  Future<bool> requestPermission() async => false;

  @override
  Future<String?> currentToken() async => null;

  @override
  Stream<String> tokenRefreshes() => const Stream<String>.empty();

  @override
  Stream<PushNotification> foregroundMessages() =>
      const Stream<PushNotification>.empty();

  @override
  Stream<PushNotification> notificationTaps() =>
      const Stream<PushNotification>.empty();

  @override
  Future<PushNotification?> initialNotification() async => null;

  @override
  Future<void> deleteToken() async {}
}
