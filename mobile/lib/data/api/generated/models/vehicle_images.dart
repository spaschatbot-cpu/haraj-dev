// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, unused_import, invalid_annotation_target, unnecessary_import

import 'package:json_annotation/json_annotation.dart';

import 'vehicle_image.dart';

part 'vehicle_images.g.dart';

/// صور مركبةٍ واحدة، وعددها — والعدّاد `1 / 9` في v1 يقرأ `total`.
@JsonSerializable()
class VehicleImages {
  const VehicleImages({required this.total, required this.results});

  factory VehicleImages.fromJson(Map<String, Object?> json) =>
      _$VehicleImagesFromJson(json);

  final int total;
  final List<VehicleImage> results;

  Map<String, Object?> toJson() => _$VehicleImagesToJson(this);
}
