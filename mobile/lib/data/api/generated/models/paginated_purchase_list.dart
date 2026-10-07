// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, unused_import, invalid_annotation_target, unnecessary_import

import 'package:json_annotation/json_annotation.dart';

import 'purchase.dart';

part 'paginated_purchase_list.g.dart';

@JsonSerializable()
class PaginatedPurchaseList {
  const PaginatedPurchaseList({
    required this.count,
    required this.results,
    this.next,
    this.previous,
  });

  factory PaginatedPurchaseList.fromJson(Map<String, Object?> json) =>
      _$PaginatedPurchaseListFromJson(json);

  final int count;
  final String? next;
  final String? previous;
  final List<Purchase> results;

  Map<String, Object?> toJson() => _$PaginatedPurchaseListToJson(this);
}
