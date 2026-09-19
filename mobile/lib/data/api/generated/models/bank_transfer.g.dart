// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'bank_transfer.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

BankTransfer _$BankTransferFromJson(Map<String, dynamic> json) => BankTransfer(
  configured: json['configured'] as bool,
  beneficiary: json['beneficiary'] as String,
  bank: json['bank'] as String,
  iban: json['iban'] as String,
  account: json['account'] as String,
);

Map<String, dynamic> _$BankTransferToJson(BankTransfer instance) =>
    <String, dynamic>{
      'configured': instance.configured,
      'beneficiary': instance.beneficiary,
      'bank': instance.bank,
      'iban': instance.iban,
      'account': instance.account,
    };
