// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'insurance_lock.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

InsuranceLock _$InsuranceLockFromJson(Map<String, dynamic> json) =>
    InsuranceLock(
      amount: json['amount'] as String,
      currency: json['currency'] as String,
      note: json['note'] as String,
    );

Map<String, dynamic> _$InsuranceLockToJson(InsuranceLock instance) =>
    <String, dynamic>{
      'amount': instance.amount,
      'currency': instance.currency,
      'note': instance.note,
    };
