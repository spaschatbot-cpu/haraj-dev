// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, unused_import, invalid_annotation_target, unnecessary_import

import 'package:json_annotation/json_annotation.dart';

part 'refund_request_input.g.dart';

@JsonSerializable()
class RefundRequestInput {
  const RefundRequestInput({required this.amount});

  factory RefundRequestInput.fromJson(Map<String, Object?> json) =>
      _$RefundRequestInputFromJson(json);

  final String amount;

  Map<String, Object?> toJson() => _$RefundRequestInputToJson(this);
}
