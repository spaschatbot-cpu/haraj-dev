// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, unused_import, invalid_annotation_target, unnecessary_import

import 'package:dio/dio.dart';
import 'package:retrofit/retrofit.dart';

import '../models/authenticated_user.dart';
import '../models/confirm_phone_change.dart';
import '../models/refresh.dart';
import '../models/send_code.dart';
import '../models/send_code_response.dart';
import '../models/start_phone_change.dart';
import '../models/start_phone_change_response.dart';
import '../models/token_pair.dart';
import '../models/verify_code.dart';

part 'auth_api.g.dart';

@RestApi()
abstract class AuthApi {
  factory AuthApi(Dio dio, {String? baseUrl}) = _AuthApi;

  /// إرسال رمز تحقق
  @POST('/api/v1/auth/code/')
  Future<SendCodeResponse> v1AuthCodeCreate({@Body() required SendCode body});

  /// التحقق من الرمز وإصدار الرموز.
  ///
  /// رقم بلا حساب يحتاج full_name، والخادم يرفض قبل أن يستهلك الرمز (registration_needs_name) فلا يضيع الرمز على حقل ناقص.
  @POST('/api/v1/auth/verify/')
  Future<TokenPair> v1AuthVerifyCreate({@Body() required VerifyCode body});

  /// تجديد رمز الوصول
  @POST('/api/v1/auth/refresh/')
  Future<TokenPair> v1AuthRefreshCreate({@Body() required Refresh body});

  /// بدء تغيير رقم الجوال.
  ///
  /// رمزان: واحد للرقم الحالي وواحد للجديد. الرقم الحالي يُقرأ من رمز الوصول لا من جسم الطلب.
  @POST('/api/v1/auth/phone/change/')
  Future<StartPhoneChangeResponse> v1AuthPhoneChangeCreate({
    @Body() required StartPhoneChange body,
  });

  /// تأكيد تغيير الجوال بالرمزين.
  ///
  /// الرمزان معاً أو لا شيء، والرفض لا يقول أيّهما أخطأ. النجاح يُلغي كل الجلسات — بما فيها هذه — فيعود العميل إلى الدخول بالرقم الجديد.
  @POST('/api/v1/auth/phone/change/confirm/')
  Future<AuthenticatedUser> v1AuthPhoneChangeConfirmCreate({
    @Body() required ConfirmPhoneChange body,
  });
}
