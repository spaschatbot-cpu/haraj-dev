import 'dart:convert';

import '../../domain/common/failure.dart';
import '../../domain/common/snapshot.dart';
import '../../domain/profile/entities/customer_profile.dart';
import '../../domain/profile/repositories/profile_repository.dart';
import '../api/api_call.dart';
import '../api/generated/clients/profile_api.dart';
import '../api/generated/models/national_id.dart';
import '../api/generated/models/patched_profile_update.dart';
import '../api/generated/models/profile.dart' as api;
import '../local/cache/response_cache.dart';
import 'profile_mapper.dart';

/// الملف الشخصي: الخادم أولاً، والكاش شبكة أمان عند **صمت** الخادم وحده.
///
/// نفس قرار `WalletRepositoryImpl`: `TransportFailure` (لا شبكة، مهلة) تسقط
/// إلى آخر نسخة معروفة مع علامة «آخر تحديث» (H5)، و`ApiFailure` تمرّ برسالتها
/// — الخادم **تكلّم**، وإخفاء كلامه خلف بيانات قديمة يكذب على المستخدم.
final class ProfileRepositoryImpl implements ProfileRepository {
  ProfileRepositoryImpl({
    required ProfileApi api,
    required ResponseCache cache,
    DateTime Function()? clock,
  }) : _api = api,
       _cache = cache,
       _clock = clock ?? DateTime.now;

  final ProfileApi _api;
  final ResponseCache _cache;
  final DateTime Function() _clock;

  @override
  Future<Snapshot<CustomerProfile>> load() async {
    try {
      final profile = await callApi(_api.profileRetrieve);
      return Snapshot.fresh(profile.toDomain(), at: await _remember(profile));
    } on TransportFailure {
      final cached = await _readCache();
      if (cached != null) return cached;
      // لا كاش: يُرمى العطب. ملف فارغ يُقرأ على أنه «حسابك بلا بيانات».
      rethrow;
    }
  }

  @override
  Future<CustomerProfile> update({String? fullName, String? email}) async {
    final profile = await callApi(
      () => _api.profileUpdate(
        body: PatchedProfileUpdate(fullName: fullName, email: email),
      ),
    );
    await _remember(profile);
    return profile.toDomain();
  }

  @override
  Future<CustomerProfile> setNationalId(String nationalId) async {
    final profile = await callApi(
      () => _api.profileSetNationalId(body: NationalId(nationalId: nationalId)),
    );
    await _remember(profile);
    return profile.toDomain();
  }

  @override
  Future<CompanyProfile?> loadCompany() async {
    try {
      final company = await callApi(_api.profileCompanyRetrieve);
      return company.toDomain();
    } on ApiFailure catch (failure) {
      // 404 هنا جواب لا عطب: «لا شركة على هذا الحساب». الشاشة تعرض نموذج
      // إنشاء، لا رسالة خطأ — والتمييز يقع هنا مرة واحدة لا في كل شاشة.
      if (failure.statusCode == 404) return null;
      rethrow;
    }
  }

  @override
  Future<CompanyProfile> saveCompany(CompanyProfile company) async {
    final saved = await callApi(
      () => _api.profileCompanySave(body: company.toRequest()),
    );
    return saved.toDomain();
  }

  /// يحفظ آخر ملف معروف ويرجع لحظة الحفظ.
  ///
  /// يُستدعى بعد التعديل أيضاً وليس بعد القراءة فقط: من عدّل اسمه ثم فقد
  /// الشبكة يجب أن يرى اسمه الجديد في النسخة المحفوظة، لا الذي قبله.
  Future<DateTime> _remember(api.Profile profile) async {
    final fetchedAt = _clock().toUtc();
    await _cache.write(
      CacheKeys.profile,
      jsonEncode(profile.toJson()),
      fetchedAtUtc: fetchedAt,
    );
    return fetchedAt;
  }

  Future<Snapshot<CustomerProfile>?> _readCache() async {
    final document = await _cache.read(CacheKeys.profile);
    if (document == null) return null;
    try {
      final profile = api.Profile.fromJson(document.decode());
      return Snapshot.cached(
        profile.toDomain(),
        storedAt: document.fetchedAtUtc,
      );
    } on Object {
      // كاش من نسخة مخطط أقدم لم يعد يُفكّ: يُعامل كغياب كاش، لا كعطب.
      return null;
    }
  }
}
