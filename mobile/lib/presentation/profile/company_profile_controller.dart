import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app/providers.dart';
import '../../domain/profile/entities/customer_profile.dart';

final companyProfileControllerProvider =
    AsyncNotifierProvider<CompanyProfileController, CompanyProfile?>(
      CompanyProfileController.new,
    );

/// ملف الشركة، أو `null` حين لا شركة على الحساب.
///
/// `null` حالة معروضة لا خطأ: الخادم يردّ 404 قاصداً «لا شركة»، والشاشة تعرض
/// نموذج إنشاء. لو عاملناها كعطب لرأى صاحبُ حسابٍ فردٍ رسالةَ خطأ كلما فتح
/// الصفحة، ولما استطاع إنشاء شركته أصلاً.
final class CompanyProfileController extends AsyncNotifier<CompanyProfile?> {
  @override
  Future<CompanyProfile?> build() =>
      ref.watch(manageProfileProvider).loadCompany();

  Future<void> refresh() async {
    state = const AsyncLoading();
    state = await AsyncValue.guard(
      () => ref.read(manageProfileProvider).loadCompany(),
    );
  }

  /// يرمي `Failure` كما جاء: «بيانات الشركة ناقصة» رسالة تخصّ النموذج المفتوح،
  /// ومسحُ النموذج لعرضها يجعل المستخدم يكتب كل شيء من أوله.
  Future<void> save(CompanyProfile company) async {
    final saved = await ref.read(manageProfileProvider).saveCompany(company);
    state = AsyncData(saved);
  }
}
