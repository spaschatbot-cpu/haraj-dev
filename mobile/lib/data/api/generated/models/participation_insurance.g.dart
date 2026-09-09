// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'participation_insurance.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

ParticipationInsurance _$ParticipationInsuranceFromJson(
  Map<String, dynamic> json,
) => ParticipationInsurance(
  state: json['state'] as String,
  stateLabel: json['state_label'] as String,
  amount: json['amount'] as String?,
  currency: json['currency'] as String?,
);

Map<String, dynamic> _$ParticipationInsuranceToJson(
  ParticipationInsurance instance,
) => <String, dynamic>{
  'state': instance.state,
  'state_label': instance.stateLabel,
  'amount': instance.amount,
  'currency': instance.currency,
};
