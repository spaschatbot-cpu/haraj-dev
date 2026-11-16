// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, unused_import, invalid_annotation_target, unnecessary_import

import 'package:dio/dio.dart';
import 'package:retrofit/retrofit.dart';

import '../models/app_appearance.dart';

part 'appearance_api.g.dart';

@RestApi()
abstract class AppearanceApi {
  factory AppearanceApi(Dio dio, {String? baseUrl}) = _AppearanceApi;

  /// مظهر التطبيق.
  ///
  /// `GET /api/v1/appearance/` — اللونُ والإضاءةُ وهل يغيّرهما العميل.
  ///
  /// **بلا دخول**: شاشةُ البدء والترحيب تُرسَمان قبل أن يدخل أحد، ومظهرُهما.
  /// من هنا. ولا شيءَ فيه يخصّ عميلاً — إعدادٌ واحدٌ للجميع.
  @GET('/api/v1/appearance/')
  Future<AppAppearance> appearanceRetrieve();
}
