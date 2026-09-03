// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, unused_import, invalid_annotation_target, unnecessary_import

import 'package:json_annotation/json_annotation.dart';

part 'verify_code.g.dart';

@JsonSerializable()
class VerifyCode {
  const VerifyCode({required this.phone, required this.code, this.fullName});

  factory VerifyCode.fromJson(Map<String, Object?> json) =>
      _$VerifyCodeFromJson(json);

  final String phone;
  final String code;

  /// يُستعمل عند إنشاء الحساب لأول مرة فقط
  @JsonKey(name: 'full_name')
  final String? fullName;

  Map<String, Object?> toJson() => _$VerifyCodeToJson(this);
}
