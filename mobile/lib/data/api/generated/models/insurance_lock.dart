// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, unused_import, invalid_annotation_target, unnecessary_import

import 'package:json_annotation/json_annotation.dart';

part 'insurance_lock.g.dart';

/// ما تعنيه هذه الفاتورة لتأمين صاحبها. يغيب حين لا يكون على التأمين قفل. نصّه من الخادم لأن **من كتب القاعدة يكتب شرحها**: أكثر ما أربك عملاء v1 رصيد يرونه ولا يستطيعون سحبه بلا سبب معروض.
///
@JsonSerializable()
class InsuranceLock {
  const InsuranceLock({
    required this.amount,
    required this.currency,
    required this.note,
  });

  factory InsuranceLock.fromJson(Map<String, Object?> json) =>
      _$InsuranceLockFromJson(json);

  final String amount;
  final String currency;

  /// شرح عربي جاهز للعرض — يُعرض حرفياً
  final String note;

  Map<String, Object?> toJson() => _$InsuranceLockToJson(this);
}
