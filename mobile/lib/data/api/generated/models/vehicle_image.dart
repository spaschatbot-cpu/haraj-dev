// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, unused_import, invalid_annotation_target, unnecessary_import

import 'package:json_annotation/json_annotation.dart';

part 'vehicle_image.g.dart';

/// صورةٌ واحدة بطبقاتها — **وليست كرتاً**.
///
/// ثلاثة حقول لا يحمل أيّها اسمَ عمودٍ على المركبة، فلا يخلطها.
/// `ops/checks/one_vehicle_card.py` بكرت. وهي منفصلة عن الكرت عمداً:.
/// T609 يقول «التفاصيل نفس حقول القائمة»، وقائمةٌ من خمسين سيارة تحمل كلٌّ.
/// منها تسع صور بثلاث طبقات هي حمولةٌ تُرسَل كلَّ مرّة لتُقرأ مرّةً واحدة.
/// (وهذا هو HR-12ب: الطبقة موجودة على القرص ولا قناة تصل إليها).
@JsonSerializable()
class VehicleImage {
  const VehicleImage({
    required this.id,
    required this.thumbnailUrl,
    required this.previewUrl,
    required this.isCover,
  });

  factory VehicleImage.fromJson(Map<String, Object?> json) =>
      _$VehicleImageFromJson(json);

  final int id;
  @JsonKey(name: 'thumbnail_url')
  final String? thumbnailUrl;
  @JsonKey(name: 'preview_url')
  final String? previewUrl;
  @JsonKey(name: 'is_cover')
  final bool isCover;

  Map<String, Object?> toJson() => _$VehicleImageToJson(this);
}
