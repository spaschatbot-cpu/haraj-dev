// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, unused_import, invalid_annotation_target, unnecessary_import

import 'package:json_annotation/json_annotation.dart';

import 'ledger_entry_direction.dart';
import 'wallet_bucket_kind.dart';

part 'ledger_entry.g.dart';

@JsonSerializable()
class LedgerEntry {
  const LedgerEntry({
    required this.id,
    required this.description,
    required this.bucketLabel,
    required this.amount,
    required this.currency,
    required this.direction,
    required this.occurredAt,
    this.bucket,
    this.reference,
  });

  factory LedgerEntry.fromJson(Map<String, Object?> json) =>
      _$LedgerEntryFromJson(json);

  final String id;

  /// وصف عربي لنوع المعاملة — لا مفتاح إنجليزي
  final String description;
  final WalletBucketKind? bucket;

  /// اسم الدلو بالعربية من الخادم
  @JsonKey(name: 'bucket_label')
  final String bucketLabel;
  final String amount;
  final String currency;

  /// اتجاه الحركة كما يقوله الخادم: دخل أم خرج. **ليست** `debit/credit` عمداً — معناهما يتبع جهة الحساب، فقراءتهما في الشاشة اجتهاد في اصطلاح محاسبي مكتوب مرة واحدة في `apps/money/models`. نظيره في الخلفية `LedgerEntrySerializer.get_direction`.
  ///
  final LedgerEntryDirection direction;
  @JsonKey(name: 'occurred_at')
  final DateTime occurredAt;
  final String? reference;

  Map<String, Object?> toJson() => _$LedgerEntryToJson(this);
}
