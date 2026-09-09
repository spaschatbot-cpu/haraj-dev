// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, unused_import, invalid_annotation_target, unnecessary_import

import 'package:json_annotation/json_annotation.dart';

import 'auction_card.dart';

part 'auction_page.g.dart';

@JsonSerializable()
class AuctionPage {
  const AuctionPage({required this.total, required this.results});

  factory AuctionPage.fromJson(Map<String, Object?> json) =>
      _$AuctionPageFromJson(json);

  final int total;
  final List<AuctionCard> results;

  Map<String, Object?> toJson() => _$AuctionPageToJson(this);
}
