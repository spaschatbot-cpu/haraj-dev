// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, unused_import, invalid_annotation_target, unnecessary_import

import 'package:json_annotation/json_annotation.dart';

import 'refund_request_state_enum.dart';

part 'refund_request.g.dart';

@JsonSerializable()
class RefundRequest {
  const RefundRequest({
    required this.id,
    required this.reference,
    required this.amount,
    required this.stateLabel,
    required this.createdAt,
    this.state,
  });

  factory RefundRequest.fromJson(Map<String, Object?> json) =>
      _$RefundRequestFromJson(json);

  final int id;
  final String reference;
  final String amount;
  final RefundRequestStateEnum? state;
  @JsonKey(name: 'state_label')
  final String stateLabel;
  @JsonKey(name: 'created_at')
  final DateTime createdAt;

  Map<String, Object?> toJson() => _$RefundRequestToJson(this);
}
