import '../entities/auth_session.dart';
import '../repositories/auth_repository.dart';

/// تغيير رقم الجوال بتأكيد الرقمين.
///
/// خطوتان في usecase واحدة عمداً: الرمزان يُطلبان معاً ويُؤكَّدان معاً، ولا
/// توجد حالة وسطى «الرقم القديم مُثبَت والجديد لا». تلك الحالة الوسطى هي
/// بالضبط مسار الاستيلاء على الحساب في v1 — من وصل إلى جلسة مفتوحة نقل الحساب
/// إلى رقمه، وجوّال صاحب الحساب لم يرنّ مرة واحدة.
final class ChangePhoneNumber {
  const ChangePhoneNumber(this._repository);

  final AuthRepository _repository;

  Future<PhoneChangeCodes> requestCodes({required String newPhone}) =>
      _repository.startPhoneChange(newPhone: newPhone);

  /// عند النجاح لا تبقى جلسة: الخادم يُلغيها كلها، والتطبيق يمحو رموزه.
  Future<void> confirm({
    required String newPhone,
    required String currentCode,
    required String newCode,
  }) => _repository.confirmPhoneChange(
    newPhone: newPhone,
    currentCode: currentCode,
    newCode: newCode,
  );
}
