// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, unused_import, invalid_annotation_target, unnecessary_import

import 'package:json_annotation/json_annotation.dart';

part 'bid_submission.g.dart';

@JsonSerializable()
class BidSubmission {
  const BidSubmission({required this.amount, this.confirmLower});

  factory BidSubmission.fromJson(Map<String, Object?> json) =>
      _$BidSubmissionFromJson(json);

  /// نصّ عشري كما يُدخله المستخدم — لا حساب في التطبيق
  final String amount;

  /// تأكيد صريح لخفض المزايدة بعد 409
  @JsonKey(name: 'confirm_lower')
  final bool? confirmLower;

  Map<String, Object?> toJson() => _$BidSubmissionToJson(this);
}
