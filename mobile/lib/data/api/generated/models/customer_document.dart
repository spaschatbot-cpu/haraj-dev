// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, unused_import, invalid_annotation_target, unnecessary_import

import 'package:json_annotation/json_annotation.dart';

part 'customer_document.g.dart';

/// نوعُ وثيقةٍ وحالتُه — صفٌّ لكل نوعٍ من الأربعة، مرفوعاً كان أو لا.
///
/// `document` قد يكون `None`، و`file` حينها `null`. وذلك أصدقُ من إسقاط الصفّ:.
/// شاشةٌ تقرأ أربعةَ صفوفٍ تعرف ما ينقص، وشاشةٌ تقرأ اثنين تعرف ما وُجد فقط.
@JsonSerializable()
class CustomerDocument {
  const CustomerDocument({
    required this.kind,
    required this.label,
    required this.uploadedAt,
    required this.file,
    required this.note,
    required this.uploadedByStaff,
  });

  factory CustomerDocument.fromJson(Map<String, Object?> json) =>
      _$CustomerDocumentFromJson(json);

  final String kind;
  final String label;
  @JsonKey(name: 'uploaded_at')
  final DateTime? uploadedAt;
  final String? file;
  final String note;

  /// هل رفعها موظّفٌ عن العميل؟ — سؤالٌ يسأله العميل نفسُه.
  ///
  /// «لم أرفع هذه» شكوى حقيقية، وجوابُها هنا لا في تخمين.
  @JsonKey(name: 'uploaded_by_staff')
  final bool uploadedByStaff;

  Map<String, Object?> toJson() => _$CustomerDocumentToJson(this);
}
