// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'app_appearance.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

AppAppearance _$AppAppearanceFromJson(Map<String, dynamic> json) =>
    AppAppearance(
      accent: AccentEnum.fromJson(json['accent'] as String),
      mode: ModeEnum.fromJson(json['mode'] as String),
      customersChoose: json['customers_choose'] as bool,
    );

Map<String, dynamic> _$AppAppearanceToJson(AppAppearance instance) =>
    <String, dynamic>{
      'accent': _$AccentEnumEnumMap[instance.accent]!,
      'mode': _$ModeEnumEnumMap[instance.mode]!,
      'customers_choose': instance.customersChoose,
    };

const _$AccentEnumEnumMap = {
  AccentEnum.azure: 'azure',
  AccentEnum.sea: 'sea',
  AccentEnum.gold: 'gold',
  AccentEnum.violet: 'violet',
  AccentEnum.teal: 'teal',
  AccentEnum.emerald: 'emerald',
  AccentEnum.amber: 'amber',
  AccentEnum.rose: 'rose',
  AccentEnum.$unknown: r'$unknown',
};

const _$ModeEnumEnumMap = {
  ModeEnum.light: 'light',
  ModeEnum.dark: 'dark',
  ModeEnum.auto: 'auto',
  ModeEnum.$unknown: r'$unknown',
};
