// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, unused_import, invalid_annotation_target, unnecessary_import

import 'package:json_annotation/json_annotation.dart';

import 'bid.dart';

part 'paginated_bid_list.g.dart';

@JsonSerializable()
class PaginatedBidList {
  const PaginatedBidList({
    required this.count,
    required this.results,
    this.next,
    this.previous,
  });

  factory PaginatedBidList.fromJson(Map<String, Object?> json) =>
      _$PaginatedBidListFromJson(json);

  final int count;
  final String? next;
  final String? previous;
  final List<Bid> results;

  Map<String, Object?> toJson() => _$PaginatedBidListToJson(this);
}
