// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, unused_import, invalid_annotation_target, unnecessary_import

import 'package:json_annotation/json_annotation.dart';

part 'bank_transfer.g.dart';

/// حسابُ الشركة كما يُعرَض للعميل ليحوّل إليه. T954.
///
/// أربعةُ نصوص، **ولا مبلغ**: الحوالةُ يقرّر مبلغَها العميل — يشحن تأميناً.
/// أو يسدّد فاتورة — والخادمُ لا يعرف أيّهما حتى تصل.
///
/// و`configured` علمٌ صريحٌ لا استنتاجٌ من فراغ الحقول: شاشةٌ تقرأ أربعةَ.
/// نصوصٍ فارغةٍ ترسمها أربعةَ أسطرٍ فارغةٍ وتظنّها بياناتٍ ناقصة، وعلمٌ.
/// واحدٌ يقول «لم يُضبَط بعد» فتعرض الرسالةَ الصحيحة.
@JsonSerializable()
class BankTransfer {
  const BankTransfer({
    required this.configured,
    required this.beneficiary,
    required this.bank,
    required this.iban,
    required this.account,
  });

  factory BankTransfer.fromJson(Map<String, Object?> json) =>
      _$BankTransferFromJson(json);

  final bool configured;
  final String beneficiary;
  final String bank;
  final String iban;
  final String account;

  Map<String, Object?> toJson() => _$BankTransferToJson(this);
}
