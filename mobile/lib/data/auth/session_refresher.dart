import 'package:dio/dio.dart';

import '../api/generated/clients/auth_api.dart';
import '../api/generated/models/refresh_request.dart';
import '../local/secure/secure_token_store.dart';

/// يجدّد رمز الوصول برمز التحديث المخزَّن.
///
/// يملك عميل dio **خاصاً به بلا `AuthInterceptor`**: لو مرّ التجديد من نفس
/// الاعتراض لأنتج 401 على التجديد نفسه، فتجديداً آخر، فحلقة لا تنتهي.
final class SessionRefresher {
  const SessionRefresher({
    required AuthApi api,
    required SecureTokenStore tokens,
  }) : _api = api,
       _tokens = tokens;

  final AuthApi _api;
  final SecureTokenStore _tokens;

  /// يرجع `true` إن نجح التجديد وحُفظ الرمزان الجديدان.
  Future<bool> refresh() async {
    final refreshToken = await _tokens.readRefreshToken();
    if (refreshToken == null) return false;

    try {
      final pair = await _api.authTokenRefresh(
        body: RefreshRequest(refresh: refreshToken),
      );
      await _tokens.save(access: pair.access, refresh: pair.refresh);
      return true;
    } on DioException {
      // فشل التجديد ليس خطأً يُعرض: نتيجته «لا جلسة»، ومن يستدعينا يتصرّف.
      return false;
    }
  }
}
