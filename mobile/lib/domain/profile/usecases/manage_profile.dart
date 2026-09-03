import '../../common/snapshot.dart';
import '../entities/customer_profile.dart';
import '../repositories/profile_repository.dart';

/// كل ما تفعله شاشة الملف الشخصي، في نقطة واحدة.
///
/// usecase واحدة لا خمس: العمليات الخمس وجوه لشيء واحد يملكه العميل عن نفسه،
/// وكلها تنتهي بنفس الكيان. تفريقها إلى خمسة أصناف يضاعف الربط في المزوّدات
/// بلا أن يفصل قراراً عن قرار.
final class ManageProfile {
  const ManageProfile(this._repository);

  final ProfileRepository _repository;

  Future<Snapshot<CustomerProfile>> load() => _repository.load();

  Future<CustomerProfile> save({String? fullName, String? email}) =>
      _repository.update(fullName: fullName, email: email);

  Future<CustomerProfile> pinNationalId(String nationalId) =>
      _repository.setNationalId(nationalId);

  Future<CompanyProfile?> loadCompany() => _repository.loadCompany();

  Future<CompanyProfile> saveCompany(CompanyProfile company) =>
      _repository.saveCompany(company);
}
