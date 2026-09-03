// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, unused_import, invalid_annotation_target, unnecessary_import

import 'package:json_annotation/json_annotation.dart';

part 'start_phone_change.g.dart';

@JsonSerializable()
class StartPhoneChange {
  const StartPhoneChange({required this.newPhone});

  factory StartPhoneChange.fromJson(Map<String, Object?> json) =>
      _$StartPhoneChangeFromJson(json);

  @JsonKey(name: 'new_phone')
  final String newPhone;

  Map<String, Object?> toJson() => _$StartPhoneChangeToJson(this);
}
