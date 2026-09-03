// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, unused_import, invalid_annotation_target, unnecessary_import

import 'package:json_annotation/json_annotation.dart';

/// اتجاه الحركة كما يقوله الخادم: دخل أم خرج. **ليست** `debit/credit` عمداً — معناهما يتبع جهة الحساب، فقراءتهما في الشاشة اجتهاد في اصطلاح محاسبي مكتوب مرة واحدة في `apps/money/models`. نظيره في الخلفية `LedgerEntrySerializer.get_direction`.
///
@JsonEnum()
enum LedgerEntryDirection {
  /// The name has been replaced because it contains a keyword. Original name: `in`.
  @JsonValue('in')
  valueIn('in'),
  @JsonValue('out')
  out('out'),

  /// Default value for all unparsed values, allows backward compatibility when adding new values on the backend.
  $unknown(null);

  const LedgerEntryDirection(this.json);

  factory LedgerEntryDirection.fromJson(String json) =>
      values.firstWhere((e) => e.json == json, orElse: () => $unknown);

  final String? json;

  @override
  String toString() => json?.toString() ?? super.toString();

  /// Returns all defined enum values excluding the $unknown value.
  static List<LedgerEntryDirection> get $valuesDefined =>
      values.where((value) => value != $unknown).toList();
}
