// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'paginated_invoice_list.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

PaginatedInvoiceList _$PaginatedInvoiceListFromJson(
  Map<String, dynamic> json,
) => PaginatedInvoiceList(
  count: (json['count'] as num).toInt(),
  results: (json['results'] as List<dynamic>)
      .map((e) => Invoice.fromJson(e as Map<String, dynamic>))
      .toList(),
  next: json['next'] as String?,
  previous: json['previous'] as String?,
);

Map<String, dynamic> _$PaginatedInvoiceListToJson(
  PaginatedInvoiceList instance,
) => <String, dynamic>{
  'count': instance.count,
  'next': instance.next,
  'previous': instance.previous,
  'results': instance.results,
};
