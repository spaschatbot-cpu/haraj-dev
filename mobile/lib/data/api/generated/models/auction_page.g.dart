// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'auction_page.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

AuctionPage _$AuctionPageFromJson(Map<String, dynamic> json) => AuctionPage(
  total: (json['total'] as num).toInt(),
  results: (json['results'] as List<dynamic>)
      .map((e) => AuctionCard.fromJson(e as Map<String, dynamic>))
      .toList(),
);

Map<String, dynamic> _$AuctionPageToJson(AuctionPage instance) =>
    <String, dynamic>{'total': instance.total, 'results': instance.results};
