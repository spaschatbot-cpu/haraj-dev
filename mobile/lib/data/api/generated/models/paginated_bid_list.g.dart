// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'paginated_bid_list.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

PaginatedBidList _$PaginatedBidListFromJson(Map<String, dynamic> json) =>
    PaginatedBidList(
      count: (json['count'] as num).toInt(),
      results: (json['results'] as List<dynamic>)
          .map((e) => Bid.fromJson(e as Map<String, dynamic>))
          .toList(),
      next: json['next'] as String?,
      previous: json['previous'] as String?,
    );

Map<String, dynamic> _$PaginatedBidListToJson(PaginatedBidList instance) =>
    <String, dynamic>{
      'count': instance.count,
      'next': instance.next,
      'previous': instance.previous,
      'results': instance.results,
    };
