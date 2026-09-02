// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, unused_import, invalid_annotation_target, unnecessary_import

import 'package:json_annotation/json_annotation.dart';

import 'ledger_entry.dart';

part 'paginated_ledger_entry_list.g.dart';

@JsonSerializable()
class PaginatedLedgerEntryList {
  const PaginatedLedgerEntryList({
    required this.count,
    required this.results,
    this.next,
    this.previous,
  });

  factory PaginatedLedgerEntryList.fromJson(Map<String, Object?> json) =>
      _$PaginatedLedgerEntryListFromJson(json);

  final int count;
  final String? next;
  final String? previous;
  final List<LedgerEntry> results;

  Map<String, Object?> toJson() => _$PaginatedLedgerEntryListToJson(this);
}
