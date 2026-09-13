// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, unused_import, invalid_annotation_target, unnecessary_import

import 'dart:convert';
import 'package:dio/dio.dart';
import 'package:retrofit/retrofit.dart';

import '../models/company_profile_read.dart';
import '../models/customer_document.dart';
import '../models/kind_enum.dart';
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

  /// الساري من كل نوع — أربعةُ صفوفٍ دائماً، والغائبُ `file: null`.
  ///
  /// الأربعةُ كلُّها لا المرفوعُ منها، لأن الشاشة تسأل «ماذا ينقصني؟» وقائمةٌ.
  /// بما رُفع تجيب عن سؤالٍ آخر.
  @GET('/api/v1/profile/documents/')
  Future<List<CustomerDocument>> v1ProfileDocumentsList();

  /// `GET`/`POST /api/v1/profile/documents/` — وثائقُ صاحب الرمز وحده.
  ///
  /// الوثائقُ الأربع (سجل تجاريّ · شهادة ضريبيّة · هويّة · آيبان) لم يكن لها.
  /// طريقٌ في v2 إطلاقاً، ولا يزال في v1 ثلاثةُ أعمدةِ مسارٍ على صفّ المستخدم.
  /// وصورةُ الآيبان **شرطٌ لفتح طلب الاسترداد** (`request_refund`)، فبلا هذه.
  /// النقطة لا سبيل للعميل إلى استرداده إلا بموظّفٍ يرفع عنه.
  ///
  /// ولا معرّفَ مستخدمٍ في المسار ولا في الجسم — كبقيّة هذا الملفّ. صاحبُ الوثيقة.
  /// هو صاحبُ الرمز، ولا شيء آخر يقرّر ذلك: ثغرةُ محفظة v1 كانت بالضبط معرّفاً.
  /// يُقرأ من الطلب.
  @MultiPart()
  @POST('/api/v1/profile/documents/')
  Future<CustomerDocument> v1ProfileDocumentsCreate({
    @Part(name: 'kind') required KindEnum kind,
    @Part(name: 'file') required String file,
    @Part(name: 'note') String? note,
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
