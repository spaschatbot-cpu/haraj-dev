// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, unused_import, invalid_annotation_target, unnecessary_import

import 'dart:convert';
import 'package:dio/dio.dart';
import 'package:retrofit/retrofit.dart';

import '../models/authenticated_user.dart';
import '../models/send_code_purpose_enum.dart';
import '../models/send_code_response.dart';
import '../models/start_phone_change_response.dart';
import '../models/token_pair.dart';

part 'auth_api.g.dart';

@RestApi()
abstract class AuthApi {
  factory AuthApi(Dio dio, {String? baseUrl}) = _AuthApi;

  /// إرسال رمز تحقق.
  ///
  /// `POST /api/v1/auth/code/` — send a one-time code to a mobile number.
  ///
  /// [purpose] - الافتراضيّ حين لا يُرسَل الحقل: `login`.
  @MultiPart()
  @POST('/api/v1/auth/code/')
  Future<SendCodeResponse> v1AuthCodeCreate({
    @Part(name: 'phone') required String phone,
    @Part(name: 'purpose') SendCodePurposeEnum? purpose,
  });

  /// بدء تغيير رقم الجوال.
  ///
  /// `POST /api/v1/auth/phone/change/` — send a code to both numbers.
  ///
  /// The only path in this file that requires a signed-in caller, and the number.
  /// being left is read **off the token**, never off the request body. Letting the.
  /// body name the current number would make this endpoint a way to move somebody.
  /// else's account, which is the shape of the takeover it exists to close.
  @MultiPart()
  @POST('/api/v1/auth/phone/change/')
  Future<StartPhoneChangeResponse> v1AuthPhoneChangeCreate({
    @Part(name: 'new_phone') required String newPhone,
  });

  /// تأكيد تغيير الجوال بالرمزين.
  ///
  /// `POST /api/v1/auth/phone/change/confirm/` — both codes, or nothing.
  ///
  /// Answers 200 with the caller's own account, whose `phone` is the new number.
  /// Every session — this one included — is revoked by the service, so the client.
  /// signs in again on the new number; that is deliberate, and.
  /// `services.confirm_phone_change` says why.
  ///
  /// [currentCode] - الرمز المُرسَل إلى الرقم الحالي.
  ///
  /// [newCode] - الرمز المُرسَل إلى الرقم الجديد.
  @MultiPart()
  @POST('/api/v1/auth/phone/change/confirm/')
  Future<AuthenticatedUser> v1AuthPhoneChangeConfirmCreate({
    @Part(name: 'new_phone') required String newPhone,
    @Part(name: 'current_code') required String currentCode,
    @Part(name: 'new_code') required String newCode,
  });

  /// تجديد رمز الوصول.
  ///
  /// `POST /api/v1/auth/refresh/` — spend a refresh token for a fresh pair.
  @MultiPart()
  @POST('/api/v1/auth/refresh/')
  Future<TokenPair> v1AuthRefreshCreate({
    @Part(name: 'refresh') required String refresh,
  });

  /// التحقق من الرمز وإصدار الرموز.
  ///
  /// `POST /api/v1/auth/verify/` — exchange a correct code for a token pair.
  ///
  /// [fullName] - يُستعمل عند إنشاء الحساب لأول مرة فقط.
  @MultiPart()
  @POST('/api/v1/auth/verify/')
  Future<TokenPair> v1AuthVerifyCreate({
    @Part(name: 'phone') required String phone,
    @Part(name: 'code') required String code,
    @Part(name: 'full_name') String? fullName,
  });
}
