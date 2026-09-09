// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'participation.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

Participation _$ParticipationFromJson(Map<String, dynamic> json) =>
    Participation(
      auction: AuctionCard.fromJson(json['auction'] as Map<String, dynamic>),
      bidsCount: (json['bids_count'] as num).toInt(),
      insurance: ParticipationInsurance.fromJson(
        json['insurance'] as Map<String, dynamic>,
      ),
    );

Map<String, dynamic> _$ParticipationToJson(Participation instance) =>
    <String, dynamic>{
      'auction': instance.auction,
      'bids_count': instance.bidsCount,
      'insurance': instance.insurance,
    };
