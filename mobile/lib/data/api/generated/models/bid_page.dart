// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, unused_import, invalid_annotation_target, unnecessary_import

import 'package:json_annotation/json_annotation.dart';

import 'bid.dart';

part 'bid_page.g.dart';

@JsonSerializable()
class BidPage {
  const BidPage({required this.total, required this.results});

  factory BidPage.fromJson(Map<String, Object?> json) =>
      _$BidPageFromJson(json);

  final int total;
  final List<Bid> results;

  Map<String, Object?> toJson() => _$BidPageToJson(this);
}
