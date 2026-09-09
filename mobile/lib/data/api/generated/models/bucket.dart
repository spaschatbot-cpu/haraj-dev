// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, unused_import, invalid_annotation_target, unnecessary_import

import 'package:json_annotation/json_annotation.dart';

part 'bucket.g.dart';

/// One named pot, with the count of entries that add up to it.
@JsonSerializable()
class Bucket {
  const Bucket({
    required this.kind,
    required this.label,
    required this.amount,
    required this.entryCount,
    required this.statement,
  });

  factory Bucket.fromJson(Map<String, Object?> json) => _$BucketFromJson(json);

  final String kind;
  final String label;
  final String amount;
  @JsonKey(name: 'entry_count')
  final int entryCount;

  /// Where to read the exact entries behind this number (Article 1-6).
  final String statement;

  Map<String, Object?> toJson() => _$BucketToJson(this);
}
