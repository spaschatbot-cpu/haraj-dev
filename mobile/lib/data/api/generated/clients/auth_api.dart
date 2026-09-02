// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, unused_import, invalid_annotation_target, unnecessary_import

import 'package:dio/dio.dart';
import 'package:retrofit/retrofit.dart';

import '../models/otp_challenge.dart';
import '../models/otp_request.dart';
import '../models/otp_verification.dart';
import '../models/refresh_request.dart';
import '../models/token_pair.dart';

part 'auth_api.g.dart';

@RestApi()
abstract class AuthApi {
  factory AuthApi(Dio dio, {String? baseUrl}) = _AuthApi;

  /// إرسال رمز تحقق إلى جوال
  @POST('/api/v1/auth/otp/request')
  Future<OtpChallenge> authOtpRequest({@Body() required OtpRequest body});

  /// التحقق من الرمز وإصدار الرموز
  @POST('/api/v1/auth/otp/verify')
  Future<TokenPair> authOtpVerify({@Body() required OtpVerification body});

  /// تجديد رمز الوصول
  @POST('/api/v1/auth/token/refresh')
  Future<TokenPair> authTokenRefresh({@Body() required RefreshRequest body});
}
