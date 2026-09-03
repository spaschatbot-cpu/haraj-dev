import '../../common/snapshot.dart';
import '../entities/customer_profile.dart';

/// عقد الملف الشخصي كما تراه طبقة النطاق.
abstract interface class ProfileRepository {
  /// الملف من الخادم، أو آخر نسخة معروفة مع لحظتها عند **صمت** الخادم (H5).
  Future<Snapshot<CustomerProfile>> load();

  /// يعدّل ما يملك العميل تغييره عن نفسه، ويرجع الملف بعد التعديل.
  ///
  /// الحقول المرسَلة هي المتغيّرة وحدها: الخادم يرفض جسماً فارغاً، ورفضه
  /// صحيح — طلب لا يغيّر شيئاً هو عطب في العميل غالباً، والردّ عليه بـ200
  /// يخفي العطب خلف نجاح.
  Future<CustomerProfile> update({String? fullName, String? email});

  /// يثبّت رقم الهوية. الخادم يرفض تغيير هوية صحيحة، ويقبل تصحيح خاطئة.
  Future<CustomerProfile> setNationalId(String nationalId);

  /// ملف الشركة، أو `null` حين لا شركة على الحساب.
  ///
  /// `null` هنا ليست خطأً مكتوماً: الخادم يردّ 404 قاصداً «لا شركة»، وهي حالة
  /// تعرضها الشاشة بنموذج إنشاء لا برسالة عطل.
  Future<CompanyProfile?> loadCompany();

  Future<CompanyProfile> saveCompany(CompanyProfile company);
}
