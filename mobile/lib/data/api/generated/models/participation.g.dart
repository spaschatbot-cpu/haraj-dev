// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'participation.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

Participation _$ParticipationFromJson(Map<String, dynamic> json) =>
    Participation(
      auctionId: json['auction_id'] as String,
      auctionTitle: json['auction_title'] as String,
      auctionStatusLabel: json['auction_status_label'] as String,
      endsAt: DateTime.parse(json['ends_at'] as String),
      bidsCount: (json['bids_count'] as num).toInt(),
      insuranceState: InsuranceState.fromJson(
        json['insurance_state'] as String,
      ),
      insuranceStateLabel: json['insurance_state_label'] as String,
      insuranceAmount: json['insurance_amount'] as String?,
      currency: json['currency'] as String?,
    );

Map<String, dynamic> _$ParticipationToJson(Participation instance) =>
    <String, dynamic>{
      'auction_id': instance.auctionId,
      'auction_title': instance.auctionTitle,
      'auction_status_label': instance.auctionStatusLabel,
      'ends_at': instance.endsAt.toIso8601String(),
      'bids_count': instance.bidsCount,
      'insurance_state': _$InsuranceStateEnumMap[instance.insuranceState]!,
      'insurance_state_label': instance.insuranceStateLabel,
      'insurance_amount': instance.insuranceAmount,
      'currency': instance.currency,
    };

const _$InsuranceStateEnumMap = {
  InsuranceState.none: 'none',
  InsuranceState.held: 'held',
  InsuranceState.locked: 'locked',
  InsuranceState.released: 'released',
  InsuranceState.$unknown: r'$unknown',
};
