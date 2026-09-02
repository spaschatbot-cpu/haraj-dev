// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'paginated_ledger_entry_list.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

PaginatedLedgerEntryList _$PaginatedLedgerEntryListFromJson(
  Map<String, dynamic> json,
) => PaginatedLedgerEntryList(
  count: (json['count'] as num).toInt(),
  results: (json['results'] as List<dynamic>)
      .map((e) => LedgerEntry.fromJson(e as Map<String, dynamic>))
      .toList(),
  next: json['next'] as String?,
  previous: json['previous'] as String?,
);

Map<String, dynamic> _$PaginatedLedgerEntryListToJson(
  PaginatedLedgerEntryList instance,
) => <String, dynamic>{
  'count': instance.count,
  'next': instance.next,
  'previous': instance.previous,
  'results': instance.results,
};
