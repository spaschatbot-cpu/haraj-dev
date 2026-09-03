import 'dart:async';

import 'package:haraj_mobile/domain/auth/entities/auth_session.dart';
import 'package:haraj_mobile/domain/auth/repositories/auth_repository.dart';
import 'package:haraj_mobile/domain/notifications/entities/push_notification.dart';
import 'package:haraj_mobile/domain/notifications/repositories/device_registry.dart';
import 'package:haraj_mobile/domain/notifications/repositories/push_service.dart';

/// جهاز مزيّف يتحكم فيه الاختبار: الإذن، والرمز، والمجاري الثلاثة.
final class FakePushService implements PushService {
  FakePushService({
    this.permissionGranted = true,
    String? token = 'fcm-token-abcdef',
    this.platform = DevicePlatform.android,
    this.launchNotification,
  }) : _token = token;

  bool permissionGranted;
  String? _token;
  PushNotification? launchNotification;

  @override
  final DevicePlatform platform;

  final tokenRefreshController = StreamController<String>.broadcast();
  final tapController = StreamController<PushNotification>.broadcast();
  final foregroundController = StreamController<PushNotification>.broadcast();

  bool permissionAsked = false;
  bool tokenDeleted = false;

  @override
  Future<bool> requestPermission() async {
    permissionAsked = true;
    return permissionGranted;
  }

  @override
  Future<String?> currentToken() async => _token;

  @override
  Stream<String> tokenRefreshes() => tokenRefreshController.stream;

  @override
  Stream<PushNotification> foregroundMessages() => foregroundController.stream;

  @override
  Stream<PushNotification> notificationTaps() => tapController.stream;

  @override
  Future<PushNotification?> initialNotification() async => launchNotification;

  @override
  Future<void> deleteToken() async {
    tokenDeleted = true;
    _token = null;
  }

  Future<void> close() async {
    await tokenRefreshController.close();
    await tapController.close();
    await foregroundController.close();
  }
}

/// سجلّ يكتب فيه الاختبار ما وصل إلى الخادم، بترتيبه.
final class RecordingDeviceRegistry implements DeviceRegistry {
  RecordingDeviceRegistry({this.onRegister, this.onUnregister});

  /// يُستدعى قبل التسجيل — به يُختبر أن الجلسة ما زالت قائمة لحظة النداء.
  final void Function()? onRegister;
  final void Function()? onUnregister;

  final List<({String token, DevicePlatform platform})> registrations = [];
  final List<String> unregistrations = [];

  Object? failWith;

  @override
  Future<void> register({
    required String token,
    required DevicePlatform platform,
  }) async {
    onRegister?.call();
    if (failWith case final error?) throw error;
    registrations.add((token: token, platform: platform));
  }

  @override
  Future<void> unregister({required String token}) async {
    onUnregister?.call();
    if (failWith case final error?) throw error;
    unregistrations.add(token);
  }
}

/// مصادقة مزيّفة: جلسة قائمة أو لا، ومحو الجلسة مرصود بترتيبه.
final class FakeAuthRepository implements AuthRepository {
  FakeAuthRepository({this.signedIn = true, this.onSignOut});

  bool signedIn;
  final void Function()? onSignOut;

  @override
  Future<bool> hasStoredSession() async => signedIn;

  @override
  Future<void> signOut() async {
    onSignOut?.call();
    signedIn = false;
  }

  @override
  Future<OtpChallenge> requestOtp({required String phone}) =>
      throw UnimplementedError();

  @override
  Future<AuthSession> verifyOtp({
    required String phone,
    required String code,
  }) => throw UnimplementedError();
}
