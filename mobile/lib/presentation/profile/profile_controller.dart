import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app/providers.dart';
import '../../domain/common/snapshot.dart';
import '../../domain/profile/entities/customer_profile.dart';
import '../auth/session_controller.dart';

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
  Future<Snapshot<CustomerProfile>> build() {
    // **يُعاد البناءُ مع كلّ تغيّرٍ في الجلسة.** المتحكّمُ يعيش عمرَ التطبيق،
    // فكان ملفُّ من خرج يبقى في الذاكرة ويُعرض لمن دخل بعده على الجهاز نفسِه —
    // قِيس في نسخة الويب من التطبيق (٢٨ سبتمبر ٢٠٢٦): خرج حسابٌ ودخل آخرُ جديد،
    // فعرضت «أكمل تسجيلك» اسمَ الأوّل ومدينتَه و«ينقص حسابك:» فارغة، ولو حُفظ
    // لكُتب اسمُ الأوّل على الثاني. والخروجُ نفسُه يمسح الكاش (`signOut`) لا
    // حالةَ Riverpod — فالمراقبةُ هنا هي ما يمسحها.
    ref.watch(sessionControllerProvider);
    return ref.watch(manageProfileProvider).load();
  }

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
  Future<void> save({String? fullName, String? email, String? city}) async {
    final updated = await ref
        .read(manageProfileProvider)
        .save(fullName: fullName, email: email, city: city);
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
