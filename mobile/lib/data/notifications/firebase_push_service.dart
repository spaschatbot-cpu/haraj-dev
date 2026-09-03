import 'dart:io' show Platform;

import 'package:firebase_messaging/firebase_messaging.dart';

import '../../domain/notifications/entities/push_notification.dart';
import '../../domain/notifications/repositories/push_service.dart';

/// تنفيذ `PushService` فوق Firebase Cloud Messaging.
///
/// هذا هو **المكان الوحيد** في التطبيق الذي يذكر Firebase. كل ما فوقه —
/// usecases وشاشات وتنقّل — يرى `PushService` وحدها، فتبديل المزوّد يبقى ملفاً
/// واحداً، ويبقى مسار «إشعار ← الشاشة الصحيحة» قابلاً للاختبار بلا جهاز.
final class FirebasePushService implements PushService {
  FirebasePushService(this._messaging, {required this.platform});

  final FirebaseMessaging _messaging;

  @override
  final DevicePlatform platform;

  /// المنصة كما يراها الجهاز نفسه.
  ///
  /// لا تأتي من إعداد بناء ولا من الخادم: بناء أندرويد يوزَّع على أندرويد،
  /// وقيمة يكتبها إنسان في ملف إعداد تفترق عن الواقع يوم يُنسخ الملف.
  static DevicePlatform get currentPlatform =>
      Platform.isIOS ? DevicePlatform.ios : DevicePlatform.android;

  @override
  Future<bool> requestPermission() async {
    final settings = await _messaging.requestPermission();
    return switch (settings.authorizationStatus) {
      // `provisional` إذن iOS الهادئ: الإشعارات تصل إلى مركز الإشعارات بلا
      // صوت. وصولها الصامت وصول، فالجهاز يُسجَّل.
      AuthorizationStatus.authorized || AuthorizationStatus.provisional => true,
      AuthorizationStatus.denied || AuthorizationStatus.notDetermined => false,
    };
  }

  @override
  Future<String?> currentToken() => _messaging.getToken();

  @override
  Stream<String> tokenRefreshes() => _messaging.onTokenRefresh;

  @override
  Stream<PushNotification> foregroundMessages() =>
      FirebaseMessaging.onMessage.map(_toDomain);

  @override
  Stream<PushNotification> notificationTaps() =>
      FirebaseMessaging.onMessageOpenedApp.map(_toDomain);

  @override
  Future<PushNotification?> initialNotification() async {
    final message = await FirebaseMessaging.instance.getInitialMessage();
    return message == null ? null : _toDomain(message);
  }

  @override
  Future<void> deleteToken() => _messaging.deleteToken();

  static PushNotification _toDomain(RemoteMessage message) => PushNotification(
    // حمولة FCM `Map<String, dynamic>` بالتوقيع، ونصّية بالأمر الواقع. التحويل
    // إلى نصّ صريح هنا كي لا يتسرّب `dynamic` إلى النطاق.
    data: message.data.map(
      (key, value) => MapEntry(key, value?.toString() ?? ''),
    ),
    title: message.notification?.title,
    body: message.notification?.body,
  );
}
