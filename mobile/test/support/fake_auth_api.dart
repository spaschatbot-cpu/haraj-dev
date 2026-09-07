import 'package:haraj_mobile/data/api/generated/clients/auth_api.dart';
import 'package:haraj_mobile/data/api/generated/models/authenticated_user.dart';
import 'package:haraj_mobile/data/api/generated/models/confirm_phone_change.dart';
import 'package:haraj_mobile/data/api/generated/models/refresh.dart';
import 'package:haraj_mobile/data/api/generated/models/send_code.dart';
import 'package:haraj_mobile/data/api/generated/models/send_code_response.dart';
import 'package:haraj_mobile/data/api/generated/models/start_phone_change.dart';
import 'package:haraj_mobile/data/api/generated/models/start_phone_change_response.dart';
import 'package:haraj_mobile/data/api/generated/models/token_pair.dart';
import 'package:haraj_mobile/data/api/generated/models/verify_code.dart';

/// خادم مصادقة صوري يسجّل ما وصله ويردّ بما يُملى عليه.
///
/// يُنفِّذ الواجهة **المولَّدة** لا واجهة مكتوبة بيد: لو تغيّر العقد فتغيّر
/// توقيع دالة، يسقط هذا الملف عند التصريف — وهو المطلوب.
final class FakeAuthApi implements AuthApi {
  FakeAuthApi({
    this.sendResponse,
    this.tokenPair,
    this.startResponse,
    this.confirmResponse,
    this.onCall,
  });

  SendCodeResponse? sendResponse;
  TokenPair? tokenPair;
  StartPhoneChangeResponse? startResponse;
  AuthenticatedUser? confirmResponse;

  /// يُنادى بكل جسم طلب وصل — لاختبار **ما أُرسل** لا ما رُدّ به فقط.
  final void Function(Object body)? onCall;

  final List<Object> bodies = <Object>[];

  @override
  Future<SendCodeResponse> v1AuthCodeCreate({required SendCode body}) async {
    _record(body);
    return sendResponse!;
  }

  @override
  Future<TokenPair> v1AuthVerifyCreate({required VerifyCode body}) async {
    _record(body);
    return tokenPair!;
  }

  @override
  Future<TokenPair> v1AuthRefreshCreate({required Refresh body}) async {
    _record(body);
    return tokenPair!;
  }

  @override
  Future<StartPhoneChangeResponse> v1AuthPhoneChangeCreate({
    required StartPhoneChange body,
  }) async {
    _record(body);
    return startResponse!;
  }

  @override
  Future<AuthenticatedUser> v1AuthPhoneChangeConfirmCreate({
    required ConfirmPhoneChange body,
  }) async {
    _record(body);
    return confirmResponse!;
  }

  void _record(Object body) {
    bodies.add(body);
    onCall?.call(body);
  }
}
