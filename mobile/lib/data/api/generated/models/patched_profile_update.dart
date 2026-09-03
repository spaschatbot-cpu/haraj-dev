// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, unused_import, invalid_annotation_target, unnecessary_import

import 'package:json_annotation/json_annotation.dart';

part 'patched_profile_update.g.dart';

/// ما يملك العميل تغييره عن نفسه ولا شيء غيره. مفتاح غير معروف يُرفض ولا يُهمَل.
///
@JsonSerializable()
class PatchedProfileUpdate {
  const PatchedProfileUpdate({this.fullName, this.email});

  factory PatchedProfileUpdate.fromJson(Map<String, Object?> json) =>
      _$PatchedProfileUpdateFromJson(json);

  @JsonKey(name: 'full_name')
  final String? fullName;
  final String? email;

  Map<String, Object?> toJson() => _$PatchedProfileUpdateToJson(this);
}
