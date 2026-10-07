// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, unused_import, invalid_annotation_target, unnecessary_import

import 'package:json_annotation/json_annotation.dart';

part 'ledger_entry.g.dart';

/// One line of the statement, read straight off an ``Entry`` row.
@JsonSerializable()
class LedgerEntry {
  const LedgerEntry({
    required this.id,
    required this.transaction,
    required this.kind,
    required this.description,
    required this.bucket,
    required this.bucketLabel,
    required this.amount,
    required this.direction,
    required this.occurredAt,
    required this.memo,
  });

  factory LedgerEntry.fromJson(Map<String, Object?> json) =>
      _$LedgerEntryFromJson(json);

  final int id;
  final String transaction;
  final String kind;
  final String description;
  final String bucket;
  @JsonKey(name: 'bucket_label')
  final String bucketLabel;
  final String amount;
  final String direction;
  @JsonKey(name: 'occurred_at')
  final DateTime occurredAt;
  final String memo;

  Map<String, Object?> toJson() => _$LedgerEntryToJson(this);
}
