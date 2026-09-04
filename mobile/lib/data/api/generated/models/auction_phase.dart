// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, unused_import, invalid_annotation_target, unnecessary_import

import 'package:json_annotation/json_annotation.dart';

/// طور المزاد كما يقوله **الخادم**: مجدول ولم يبدأ، أو جارٍ، أو انتهى.
///
/// ثلاث قيم لا ستّ: `AuctionStatus` حالةُ الكيان الكاملة (مسودة، ملغى، مسوّى…) ويحتاجها من يديره؛ و`AuctionPhase` هو ما يراه المتصفّح، وهو الذي تُبنى عليه التبويبات. اشتقاق الثاني من الأول قرارُ خادم، وحسابه في الواجهة يجعل لـ«منتهي» تعريفاً ثانياً يفترق عند أول حالة جديدة.
///
@JsonEnum()
enum AuctionPhase {
  @JsonValue('upcoming')
  upcoming('upcoming'),
  @JsonValue('active')
  active('active'),
  @JsonValue('ended')
  ended('ended'),

  /// Default value for all unparsed values, allows backward compatibility when adding new values on the backend.
  $unknown(null);

  const AuctionPhase(this.json);

  factory AuctionPhase.fromJson(String json) =>
      values.firstWhere((e) => e.json == json, orElse: () => $unknown);

  final String? json;

  @override
  String toString() => json?.toString() ?? super.toString();

  /// Returns all defined enum values excluding the $unknown value.
  static List<AuctionPhase> get $valuesDefined =>
      values.where((value) => value != $unknown).toList();
}
