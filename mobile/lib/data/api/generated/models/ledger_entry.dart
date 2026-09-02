// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, unused_import, invalid_annotation_target, unnecessary_import

import 'package:json_annotation/json_annotation.dart';

import 'ledger_entry_direction.dart';

part 'ledger_entry.g.dart';

@JsonSerializable()
class LedgerEntry {
  const LedgerEntry({
    required this.id,
    required this.description,
    required this.amount,
    required this.currency,
    required this.direction,
    required this.occurredAt,
    this.reference,
  });

  factory LedgerEntry.fromJson(Map<String, Object?> json) =>
      _$LedgerEntryFromJson(json);

  final String id;

  /// وصف عربي لنوع المعاملة — لا مفتاح إنجليزي
  final String description;
  final String amount;
  final String currency;
  final LedgerEntryDirection direction;
  @JsonKey(name: 'occurred_at')
  final DateTime occurredAt;
  final String? reference;

  Map<String, Object?> toJson() => _$LedgerEntryToJson(this);
}
