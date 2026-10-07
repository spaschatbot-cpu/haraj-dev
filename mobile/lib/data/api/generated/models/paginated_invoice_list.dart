// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, unused_import, invalid_annotation_target, unnecessary_import

import 'package:json_annotation/json_annotation.dart';

import 'invoice.dart';

part 'paginated_invoice_list.g.dart';

@JsonSerializable()
class PaginatedInvoiceList {
  const PaginatedInvoiceList({
    required this.count,
    required this.results,
    this.next,
    this.previous,
  });

  factory PaginatedInvoiceList.fromJson(Map<String, Object?> json) =>
      _$PaginatedInvoiceListFromJson(json);

  final int count;
  final String? next;
  final String? previous;
  final List<Invoice> results;

  Map<String, Object?> toJson() => _$PaginatedInvoiceListToJson(this);
}
