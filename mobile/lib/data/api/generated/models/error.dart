// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, unused_import, invalid_annotation_target, unnecessary_import

import 'package:json_annotation/json_annotation.dart';

part 'error.g.dart';

@JsonSerializable()
class Error {
  const Error({
    required this.code,
    required this.message,
    required this.detail,
  });

  factory Error.fromJson(Map<String, Object?> json) => _$ErrorFromJson(json);

  /// رمزٌ ثابت يفرّق سببَ الرفض عن سببٍ آخر. **هو ما يُفرَّع عليه في العميل**، لا الرسالة ولا رمز HTTP.
  final String code;

  /// جملةٌ عربية جاهزة للعرض كما هي. لا يُترجمها العميل ولا يستبدلها: نصٌّ واحد للسبب الواحد (المادة ٤-٥).
  final String message;

  /// حقولٌ تخصّ هذا الرفض بعينه — مبلغٌ قائم، حقلٌ ناقص. كائنٌ فارغ حين لا تفصيل، لا `null`.
  final dynamic detail;

  Map<String, Object?> toJson() => _$ErrorToJson(this);
}
