// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'authenticated_user.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

AuthenticatedUser _$AuthenticatedUserFromJson(Map<String, dynamic> json) =>
    AuthenticatedUser(
      id: (json['id'] as num).toInt(),
      phone: json['phone'] as String,
      displayName: json['display_name'] as String,
      accountType: json['account_type'] as String,
      isNew: json['is_new'] as bool,
    );

Map<String, dynamic> _$AuthenticatedUserToJson(AuthenticatedUser instance) =>
    <String, dynamic>{
      'id': instance.id,
      'phone': instance.phone,
      'display_name': instance.displayName,
      'account_type': instance.accountType,
      'is_new': instance.isNew,
    };
