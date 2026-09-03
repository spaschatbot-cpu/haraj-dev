// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, unused_import, invalid_annotation_target, unnecessary_import

import 'package:json_annotation/json_annotation.dart';

import 'insurance_state.dart';

part 'participation.g.dart';

@JsonSerializable()
class Participation {
  const Participation({
    required this.auctionId,
    required this.auctionTitle,
    required this.auctionStatusLabel,
    required this.endsAt,
    required this.bidsCount,
    required this.insuranceState,
    required this.insuranceStateLabel,
    this.insuranceAmount,
    this.currency,
  });

  factory Participation.fromJson(Map<String, Object?> json) =>
      _$ParticipationFromJson(json);

  @JsonKey(name: 'auction_id')
  final String auctionId;
  @JsonKey(name: 'auction_title')
  final String auctionTitle;

  /// حالة المزاد بالعربية من الخادم. الحالة تصل **مسمّاة** لا مرمَّزة، لأن خريطة حالات في التطبيق نسخة ثانية تفترق عن الأصل.
  ///
  @JsonKey(name: 'auction_status_label')
  final String auctionStatusLabel;
  @JsonKey(name: 'ends_at')
  final DateTime endsAt;

  /// عدد مزايداتي في هذا المزاد — يعدّها الخادم
  @JsonKey(name: 'bids_count')
  final int bidsCount;
  @JsonKey(name: 'insurance_state')
  final InsuranceState insuranceState;

  /// وصف عربي جاهز للعرض — لا خريطة حالات في التطبيق
  @JsonKey(name: 'insurance_state_label')
  final String insuranceStateLabel;

  /// مبلغ المحجوز أو المقفول لهذا المزاد، إن وُجد
  @JsonKey(name: 'insurance_amount')
  final String? insuranceAmount;
  final String? currency;

  Map<String, Object?> toJson() => _$ParticipationToJson(this);
}
