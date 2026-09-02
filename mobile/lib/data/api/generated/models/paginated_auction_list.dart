// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, unused_import, invalid_annotation_target, unnecessary_import

import 'package:json_annotation/json_annotation.dart';

import 'auction.dart';

part 'paginated_auction_list.g.dart';

@JsonSerializable()
class PaginatedAuctionList {
  const PaginatedAuctionList({
    required this.count,
    required this.results,
    this.next,
    this.previous,
  });

  factory PaginatedAuctionList.fromJson(Map<String, Object?> json) =>
      _$PaginatedAuctionListFromJson(json);

  final int count;
  final String? next;
  final String? previous;
  final List<Auction> results;

  Map<String, Object?> toJson() => _$PaginatedAuctionListToJson(this);
}
