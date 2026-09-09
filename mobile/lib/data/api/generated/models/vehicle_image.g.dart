// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'vehicle_image.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

VehicleImage _$VehicleImageFromJson(Map<String, dynamic> json) => VehicleImage(
  id: (json['id'] as num).toInt(),
  thumbnailUrl: json['thumbnail_url'] as String?,
  previewUrl: json['preview_url'] as String?,
  isCover: json['is_cover'] as bool,
);

Map<String, dynamic> _$VehicleImageToJson(VehicleImage instance) =>
    <String, dynamic>{
      'id': instance.id,
      'thumbnail_url': instance.thumbnailUrl,
      'preview_url': instance.previewUrl,
      'is_cover': instance.isCover,
    };
