// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'bid_submission.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

BidSubmission _$BidSubmissionFromJson(Map<String, dynamic> json) =>
    BidSubmission(
      amount: json['amount'] as String,
      confirmLower: json['confirm_lower'] as bool?,
    );

Map<String, dynamic> _$BidSubmissionToJson(BidSubmission instance) =>
    <String, dynamic>{
      'amount': instance.amount,
      'confirm_lower': instance.confirmLower,
    };
