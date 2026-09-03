// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, unused_import, invalid_annotation_target, unnecessary_import

import 'package:json_annotation/json_annotation.dart';

part 'authenticated_user.g.dart';

@JsonSerializable()
class AuthenticatedUser {
  const AuthenticatedUser({
    required this.id,
    required this.phone,
    required this.displayName,
    required this.accountType,
    required this.isNew,
  });

  factory AuthenticatedUser.fromJson(Map<String, Object?> json) =>
      _$AuthenticatedUserFromJson(json);

  final int id;
  final String phone;
  @JsonKey(name: 'display_name')
  final String displayName;
  @JsonKey(name: 'account_type')
  final String accountType;

  /// أول دخول لهذا الرقم
  @JsonKey(name: 'is_new')
  final bool isNew;

  Map<String, Object?> toJson() => _$AuthenticatedUserToJson(this);
}
