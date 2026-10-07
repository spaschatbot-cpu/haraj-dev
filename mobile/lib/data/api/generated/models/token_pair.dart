// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, unused_import, invalid_annotation_target, unnecessary_import

import 'package:json_annotation/json_annotation.dart';

import 'authenticated_user.dart';

part 'token_pair.g.dart';

@JsonSerializable()
class TokenPair {
  const TokenPair({
    required this.access,
    required this.refresh,
    required this.expiresIn,
    required this.expiresAt,
    this.user,
  });

  factory TokenPair.fromJson(Map<String, Object?> json) =>
      _$TokenPairFromJson(json);

  final String access;
  final String refresh;

  /// عمر رمز الوصول بالثواني
  @JsonKey(name: 'expires_in')
  final int expiresIn;
  @JsonKey(name: 'expires_at')
  final DateTime expiresAt;
  final AuthenticatedUser? user;

  Map<String, Object?> toJson() => _$TokenPairToJson(this);
}
