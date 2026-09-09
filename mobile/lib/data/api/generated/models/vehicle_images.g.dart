// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'vehicle_images.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

VehicleImages _$VehicleImagesFromJson(Map<String, dynamic> json) =>
    VehicleImages(
      total: (json['total'] as num).toInt(),
      results: (json['results'] as List<dynamic>)
          .map((e) => VehicleImage.fromJson(e as Map<String, dynamic>))
          .toList(),
    );

Map<String, dynamic> _$VehicleImagesToJson(VehicleImages instance) =>
    <String, dynamic>{'total': instance.total, 'results': instance.results};
