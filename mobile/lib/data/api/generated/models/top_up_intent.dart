// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, unused_import, invalid_annotation_target, unnecessary_import

import 'package:json_annotation/json_annotation.dart';

import 'top_up_intent_status.dart';

part 'top_up_intent.g.dart';

@JsonSerializable()
class TopUpIntent {
  const TopUpIntent({
    required this.reference,
    required this.amount,
    required this.currency,
    required this.redirectUrl,
    required this.status,
    required this.statusLabel,
  });

  factory TopUpIntent.fromJson(Map<String, Object?> json) =>
      _$TopUpIntentFromJson(json);

  final String reference;

  /// المبلغ يحدّده الخادم ويُعرض كما وصل
  final String amount;
  final String currency;

  /// عنوان البوابة — يفتحه التطبيق ولا يقرأ ما يعود منه
  @JsonKey(name: 'redirect_url')
  final String redirectUrl;
  final TopUpIntentStatus status;

  /// وصف الحالة بالعربية من الخادم. موجود لأن خريطة حالات في التطبيق نسخة ثانية من قاعدة يملكها الخادم (المادة ٤-٥). نظيره في الخلفية `PaymentIntentSerializer.state_label`.
  ///
  @JsonKey(name: 'status_label')
  final String statusLabel;

  Map<String, Object?> toJson() => _$TopUpIntentToJson(this);
}
