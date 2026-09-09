// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'bid_quote.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

BidQuote _$BidQuoteFromJson(Map<String, dynamic> json) => BidQuote(
  amount: json['amount'] as String,
  tax: json['tax'] as String,
  total: json['total'] as String,
);

Map<String, dynamic> _$BidQuoteToJson(BidQuote instance) => <String, dynamic>{
  'amount': instance.amount,
  'tax': instance.tax,
  'total': instance.total,
};
