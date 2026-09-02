// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, unused_import, invalid_annotation_target, unnecessary_import

import 'package:json_annotation/json_annotation.dart';

part 'api_error_body.g.dart';

@JsonSerializable()
class ApiErrorBody {
  const ApiErrorBody({required this.code, required this.message, this.details});

  factory ApiErrorBody.fromJson(Map<String, Object?> json) =>
      _$ApiErrorBodyFromJson(json);

  /// رمز ثابت يفهمه العميل — لا يُترجم ولا يُعرض
  final String code;

  /// رسالة عربية جاهزة للعرض كما جاءت. **ممنوع** على التطبيق استبدالها بنصّ محلي لحالة يعرفها الخادم.
  ///
  final String message;

  /// بيانات إضافية للتشخيص — لا تُعرض للمستخدم
  final dynamic details;

  Map<String, Object?> toJson() => _$ApiErrorBodyToJson(this);
}
