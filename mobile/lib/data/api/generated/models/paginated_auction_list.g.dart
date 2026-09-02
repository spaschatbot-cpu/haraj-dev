// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'paginated_auction_list.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

PaginatedAuctionList _$PaginatedAuctionListFromJson(
  Map<String, dynamic> json,
) => PaginatedAuctionList(
  count: (json['count'] as num).toInt(),
  results: (json['results'] as List<dynamic>)
      .map((e) => Auction.fromJson(e as Map<String, dynamic>))
      .toList(),
  next: json['next'] as String?,
  previous: json['previous'] as String?,
);

Map<String, dynamic> _$PaginatedAuctionListToJson(
  PaginatedAuctionList instance,
) => <String, dynamic>{
  'count': instance.count,
  'next': instance.next,
  'previous': instance.previous,
  'results': instance.results,
};
