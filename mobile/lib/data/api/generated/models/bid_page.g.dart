// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'bid_page.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

BidPage _$BidPageFromJson(Map<String, dynamic> json) => BidPage(
  total: (json['total'] as num).toInt(),
  results: (json['results'] as List<dynamic>)
      .map((e) => Bid.fromJson(e as Map<String, dynamic>))
      .toList(),
);

Map<String, dynamic> _$BidPageToJson(BidPage instance) => <String, dynamic>{
  'total': instance.total,
  'results': instance.results,
};
