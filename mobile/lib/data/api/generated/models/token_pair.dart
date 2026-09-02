// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, unused_import, invalid_annotation_target, unnecessary_import

import 'package:json_annotation/json_annotation.dart';

part 'token_pair.g.dart';

@JsonSerializable()
class TokenPair {
  const TokenPair({
    required this.access,
    required this.refresh,
    required this.accessExpiresAt,
    required this.isNewUser,
  });

  factory TokenPair.fromJson(Map<String, Object?> json) =>
      _$TokenPairFromJson(json);

  final String access;
  final String refresh;
  @JsonKey(name: 'access_expires_at')
  final DateTime accessExpiresAt;
  @JsonKey(name: 'is_new_user')
  final bool isNewUser;

  Map<String, Object?> toJson() => _$TokenPairToJson(this);
}
