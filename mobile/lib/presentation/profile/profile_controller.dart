import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app/providers.dart';
import '../../domain/common/snapshot.dart';
import '../../domain/profile/entities/customer_profile.dart';

final profileControllerProvider =
    AsyncNotifierProvider<ProfileController, Snapshot<CustomerProfile>>(
      ProfileController.new,
    );

/// حالة شاشة الملف الشخصي: تحميل، أو ملف بمصدره ولحظته، أو عطب.
///
/// الملف يصل داخل `Snapshot` لا عارياً: الشاشة تعمل بلا اتصال بآخر نسخة معروفة
/// **مع علامة «آخر تحديث»** (قاعدة العرض 7 ومعيار H5)، وبلا حمل اللحظة إلى
/// العرض تكون العلامة تخميناً.
final class ProfileController extends AsyncNotifier<Snapshot<CustomerProfile>> {
  @override
  Future<Snapshot<CustomerProfile>> build() =>
      ref.watch(manageProfileProvider).load();

  Future<void> refresh() async {
    state = const AsyncLoading();
    state = await AsyncValue.guard(
      () => ref.read(manageProfileProvider).load(),
    );
  }

  /// يحفظ ما يملك العميل تغييره، ويرمي `Failure` كما جاء ليعرضه من استدعى.
  ///
  /// الرمي لا الابتلاع: رفض الخادم رسالةٌ عربية تخصّ هذا الحقل، وابتلاعها في
  /// `AsyncError` يمسح النموذج المملوء من الشاشة ويترك المستخدم بلا سبب.
  Future<void> save({String? fullName, String? email}) async {
    final updated = await ref
        .read(manageProfileProvider)
        .save(fullName: fullName, email: email);
    _replaceWith(updated);
  }

  Future<void> pinNationalId(String nationalId) async {
    final updated = await ref
        .read(manageProfileProvider)
        .pinNationalId(nationalId);
    _replaceWith(updated);
  }

  /// الردّ على الكتابة هو الملف بعد الكتابة — نسخة طازجة من الخادم لا تخمين
  /// محلي لما صار عليه الحساب.
  void _replaceWith(CustomerProfile profile) {
    state = AsyncData(Snapshot.fresh(profile, at: DateTime.now().toUtc()));
  }
}
