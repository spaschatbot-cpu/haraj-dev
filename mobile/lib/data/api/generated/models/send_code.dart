// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, unused_import, invalid_annotation_target, unnecessary_import

import 'package:json_annotation/json_annotation.dart';

import 'send_code_purpose_enum.dart';

part 'send_code.g.dart';

@JsonSerializable()
class SendCode {
  const SendCode({required this.phone, this.purpose});

  factory SendCode.fromJson(Map<String, Object?> json) =>
      _$SendCodeFromJson(json);

  final String phone;
  final SendCodePurposeEnum? purpose;

  Map<String, Object?> toJson() => _$SendCodeToJson(this);
}
