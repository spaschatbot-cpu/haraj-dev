import '../../domain/notifications/repositories/device_registry.dart';
import '../../domain/notifications/repositories/push_service.dart';
import '../api/api_call.dart';
import '../api/generated/clients/devices_api.dart';
import '../api/generated/models/device_registration.dart';
import '../api/generated/models/device_registration_platform.dart';
import '../api/generated/models/device_unregistration.dart';

/// تسجيل الجهاز عند خادمنا، فوق العميل المولَّد من المخطط (T716).
///
/// ⚠️ الجسم `{token, platform}` ولا شيء غيره. المالك يأتي من ترويسة
/// `Authorization` التي يضيفها `AuthInterceptor` — لا من الجسم. هذه هي ثغرة
/// v1 بعينها: كان معرّف الحساب حقلاً في الجسم، فتسجيل جهاز باسم عميل آخر كان
/// بُعد حقلٍ واحد، وإشعارات هذه القناة تقول على ماذا يزايد الرجل وبكم.
///
/// الطراز المولَّد `DeviceRegistration` لا يملك حقل مالك أصلاً، فالمنع في
/// العقد لا في هذه الطبقة — وهذا هو المكان الصحيح له.
final class DeviceRegistryImpl implements DeviceRegistry {
  const DeviceRegistryImpl({required DevicesApi api}) : _api = api;

  final DevicesApi _api;

  @override
  Future<void> register({
    required String token,
    required DevicePlatform platform,
  }) => callApi(
    () => _api.devicesRegister(
      body: DeviceRegistration(token: token, platform: _wire(platform)),
    ),
  );

  @override
  Future<void> unregister({required String token}) => callApi(
    () => _api.devicesUnregister(body: DeviceUnregistration(token: token)),
  );

  static DeviceRegistrationPlatform _wire(DevicePlatform platform) =>
      switch (platform) {
        DevicePlatform.android => DeviceRegistrationPlatform.android,
        DevicePlatform.ios => DeviceRegistrationPlatform.ios,
      };
}
