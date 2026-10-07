// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, unused_import, invalid_annotation_target, unnecessary_import

import 'dart:convert';
import 'package:dio/dio.dart';
import 'package:retrofit/retrofit.dart';

import '../models/device.dart';
import '../models/platform_enum.dart';

part 'devices_api.g.dart';

@RestApi()
abstract class DevicesApi {
  factory DevicesApi(Dio dio, {String? baseUrl}) = _DevicesApi;

  /// أجهزتي.
  ///
  /// `POST`/`GET /api/v1/devices/` — register this handset, or list mine.
  @GET('/api/v1/devices/')
  Future<List<Device>> devicesList();

  /// تسجيل جهاز للإشعارات.
  ///
  /// `POST`/`GET /api/v1/devices/` — register this handset, or list mine.
  @MultiPart()
  @POST('/api/v1/devices/')
  Future<Device> devicesRegister({
    @Part(name: 'token') required String token,
    @Part(name: 'platform') required PlatformEnum platform,
  });

  /// إلغاء تسجيل جهاز.
  ///
  /// `POST /api/v1/devices/unregister/` — this handset stops receiving mine.
  ///
  /// The app calls it on sign-out. Deleting the provider token on the handset is.
  /// not enough on its own: the row here would keep a stranger's account name.
  /// attached to a phone that changed hands, and a delivery report would still.
  /// read as if the previous owner were reachable — the absence of a send is not.
  /// evidence he was not told (Article 2-4).
  ///
  /// `POST` rather than `DELETE /devices/{token}`: the token is a credential for.
  /// sending to the handset, and a path segment lands in every access log and.
  /// proxy cache on the way.
  @MultiPart()
  @POST('/api/v1/devices/unregister/')
  Future<void> devicesUnregister({@Part(name: 'token') required String token});
}
