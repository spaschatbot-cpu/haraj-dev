// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, unused_import, invalid_annotation_target, unnecessary_import

import 'package:json_annotation/json_annotation.dart';

import 'accent_enum.dart';
import 'mode_enum.dart';

part 'app_appearance.g.dart';

@JsonSerializable()
class AppAppearance {
  const AppAppearance({
    required this.accent,
    required this.mode,
    required this.customersChoose,
  });

  factory AppAppearance.fromJson(Map<String, Object?> json) =>
      _$AppAppearanceFromJson(json);

  final AccentEnum accent;
  final ModeEnum mode;
  @JsonKey(name: 'customers_choose')
  final bool customersChoose;

  Map<String, Object?> toJson() => _$AppAppearanceToJson(this);
}
