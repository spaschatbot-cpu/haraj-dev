// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, unused_import, invalid_annotation_target, unnecessary_import

import 'package:dio/dio.dart';
import 'package:retrofit/retrofit.dart';

import '../models/company_profile.dart';
import '../models/company_profile_read.dart';
import '../models/national_id.dart';
import '../models/patched_profile_update.dart';
import '../models/profile.dart';

part 'profile_api.g.dart';

@RestApi()
abstract class ProfileApi {
  factory ProfileApi(Dio dio, {String? baseUrl}) = _ProfileApi;

  /// ملفي الشخصي
  @GET('/api/v1/profile/')
  Future<Profile> profileRetrieve();

  /// تعديل الملف الشخصي
  @PATCH('/api/v1/profile/')
  Future<Profile> profileUpdate({@Body() required PatchedProfileUpdate body});

  /// تثبيت رقم الهوية.
  ///
  /// هوية صحيحة على الحساب لا تتغيّر (national_id_already_verified)، وهوية غير صحيحة يصحّحها صاحبها بنفسه.
  @PUT('/api/v1/profile/national-id/')
  Future<Profile> profileSetNationalId({@Body() required NationalId body});

  /// ملف الشركة.
  ///
  /// 404 حين لا شركة على الحساب — «لا شركة» و«شركة بحقول فارغة» جوابان مختلفان، والشاشة التي لا تفرّق بينهما تعرض نموذج تعديل لشيء غير موجود.
  @GET('/api/v1/profile/company/')
  Future<CompanyProfileRead> profileCompanyRetrieve();

  /// حفظ ملف الشركة
  @PUT('/api/v1/profile/company/')
  Future<CompanyProfileRead> profileCompanySave({
    @Body() required CompanyProfile body,
  });
}
