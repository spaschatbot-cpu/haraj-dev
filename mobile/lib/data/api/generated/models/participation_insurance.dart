// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, unused_import, invalid_annotation_target, unnecessary_import

import 'package:json_annotation/json_annotation.dart';

part 'participation_insurance.g.dart';

/// What this bidder's deposit for this auction is doing, per the ledger.
///
/// Read off `money.Hold` and nothing else. The alternative — the app matching.
/// «مزايداتي» against «المحفظة» — is a rule in a screen, and it is wrong the.
/// moment a hold is released or consumed while the bids stay as they were.
@JsonSerializable()
class ParticipationInsurance {
  const ParticipationInsurance({
    required this.state,
    required this.stateLabel,
    required this.amount,
    required this.currency,
  });

  factory ParticipationInsurance.fromJson(Map<String, Object?> json) =>
      _$ParticipationInsuranceFromJson(json);

  final String state;
  @JsonKey(name: 'state_label')
  final String stateLabel;
  final String? amount;
  final String? currency;

  Map<String, Object?> toJson() => _$ParticipationInsuranceToJson(this);
}
