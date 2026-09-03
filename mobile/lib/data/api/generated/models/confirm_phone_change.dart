// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, unused_import, invalid_annotation_target, unnecessary_import

import 'package:json_annotation/json_annotation.dart';

part 'confirm_phone_change.g.dart';

@JsonSerializable()
class ConfirmPhoneChange {
  const ConfirmPhoneChange({
    required this.newPhone,
    required this.currentCode,
    required this.newCode,
  });

  factory ConfirmPhoneChange.fromJson(Map<String, Object?> json) =>
      _$ConfirmPhoneChangeFromJson(json);

  @JsonKey(name: 'new_phone')
  final String newPhone;

  /// الرمز المُرسَل إلى الرقم الحالي
  @JsonKey(name: 'current_code')
  final String currentCode;

  /// الرمز المُرسَل إلى الرقم الجديد
  @JsonKey(name: 'new_code')
  final String newCode;

  Map<String, Object?> toJson() => _$ConfirmPhoneChangeToJson(this);
}
