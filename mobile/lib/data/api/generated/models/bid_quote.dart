// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, unused_import, invalid_annotation_target, unnecessary_import

import 'package:json_annotation/json_annotation.dart';

part 'bid_quote.g.dart';

/// ما يصير عليه المبلغ بعد الضريبة — من `money.tax_added_to` وحدها.
@JsonSerializable()
class BidQuote {
  const BidQuote({
    required this.amount,
    required this.tax,
    required this.total,
  });

  factory BidQuote.fromJson(Map<String, Object?> json) =>
      _$BidQuoteFromJson(json);

  final String amount;
  final String tax;
  final String total;

  Map<String, Object?> toJson() => _$BidQuoteToJson(this);
}
