// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, unused_import, invalid_annotation_target, unnecessary_import

import 'dart:convert';
import 'package:dio/dio.dart';
import 'package:retrofit/retrofit.dart';

import '../models/company_profile_read.dart';
import '../models/profile.dart';

part 'profile_api.g.dart';

@RestApi()
abstract class ProfileApi {
  factory ProfileApi(Dio dio, {String? baseUrl}) = _ProfileApi;

  /// ملفي الشخصي.
  ///
  /// `GET`/`PATCH /api/v1/profile/` — the caller's own account.
  @GET('/api/v1/profile/')
  Future<Profile> profileRetrieve();

  /// تعديل الملف الشخصي.
  ///
  /// `GET`/`PATCH /api/v1/profile/` — the caller's own account.
  @MultiPart()
  @PATCH('/api/v1/profile/')
  Future<Profile> profileUpdate({
    @Part(name: 'full_name') String? fullName,
    @Part(name: 'email') dynamic email,
  });

  /// ملف الشركة.
  ///
  /// `GET`/`PUT /api/v1/profile/company/` — the company and its ZATCA address.
  @GET('/api/v1/profile/company/')
  Future<CompanyProfileRead> profileCompanyRetrieve();

  /// حفظ ملف الشركة.
  ///
  /// `GET`/`PUT /api/v1/profile/company/` — the company and its ZATCA address.
  @MultiPart()
  @PUT('/api/v1/profile/company/')
  Future<CompanyProfileRead> profileCompanySave({
    @Part(name: 'name') String? name,
    @Part(name: 'representative_name') String? representativeName,
    @Part(name: 'commercial_register') String? commercialRegister,
    @Part(name: 'vat_number') String? vatNumber,
    @Part(name: 'building_number') String? buildingNumber,
    @Part(name: 'street') String? street,
    @Part(name: 'district') String? district,
    @Part(name: 'city') String? city,
    @Part(name: 'postal_code') String? postalCode,
  });

  /// تثبيت رقم الهوية.
  ///
  /// `PUT /api/v1/profile/national-id/` — set it once it is right.
  ///
  /// A valid id already on the account is refused (`national_id_already_verified`);.
  /// an invalid one may be replaced. `services.set_national_id` says why at.
  /// length — the short version is that a customer who mistyped a digit must be.
  /// able to fix themselves, and a correct id must not be swappable for.
  /// somebody else's.
  @MultiPart()
  @PUT('/api/v1/profile/national-id/')
  Future<Profile> profileSetNationalId({
    @Part(name: 'national_id') required String nationalId,
  });
}
