// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, unused_import, invalid_annotation_target, unnecessary_import

import 'package:dio/dio.dart';
import 'package:retrofit/retrofit.dart';

import '../models/device.dart';
import '../models/device_registration.dart';
import '../models/device_unregistration.dart';

part 'devices_api.g.dart';

@RestApi()
abstract class DevicesApi {
  factory DevicesApi(Dio dio, {String? baseUrl}) = _DevicesApi;

  /// تسجيل جهاز للإشعارات — يُربط بالمستخدم من الرمز
  @POST('/api/v1/devices')
  Future<Device> devicesRegister({@Body() required DeviceRegistration body});

  /// إلغاء تسجيل جهاز عند الخروج — بالرمز، وبمالكه من رمز الدخول
  @POST('/api/v1/devices/unregister')
  Future<void> devicesUnregister({@Body() required DeviceUnregistration body});
}
