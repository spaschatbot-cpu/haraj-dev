import 'package:haraj_mobile/domain/auth/entities/auth_session.dart';
import 'package:haraj_mobile/domain/auth/repositories/auth_repository.dart';
import 'package:haraj_mobile/domain/common/failure.dart';
import 'package:haraj_mobile/domain/common/snapshot.dart';
import 'package:haraj_mobile/domain/profile/entities/customer_profile.dart';
import 'package:haraj_mobile/domain/profile/repositories/profile_repository.dart';

/// مستودعات صورية على **عقود النطاق** — لا على نماذج المخطط.
///
/// اختبار الشاشة يبدّل المستودع لا العميل: هكذا يختبر ما تفعله الشاشة بالجواب،
/// لا ما يفعله dio بالجسم. وأي تغيّر في العقد يسقط هنا عند التصريف.

final class FakeAuthRepository implements AuthRepository {
  FakeAuthRepository({this.storedSession = false, this.onSignOut});

  bool storedSession;

  /// يُستدعى لحظة محو الرمزين — به يُرصد **ترتيب** الخروج.
  ///
  /// الترتيب هو المهم لا الحدث: بعد محو الرمزين لا شيء يثبت للخادم من صاحب
  /// الجهاز، فإلغاء تسجيله بعدهما يُردّ بـ401.
  final void Function()? onSignOut;

  CodeDelivery delivery = CodeDelivery(
    expiresAt: DateTime.utc(2026, 9, 1, 10, 5),
    resendAfterSeconds: 60,
  );

  AuthSession session = AuthSession(
    accessExpiresAt: DateTime.utc(2026, 9, 1, 12),
    isNewAccount: false,
    displayName: 'عميل',
  );

  PhoneChangeCodes phoneChangeCodes = PhoneChangeCodes(
    sentToCurrent: true,
    sentToNew: true,
    delivery: CodeDelivery(
      expiresAt: DateTime.utc(2026, 9, 1, 10, 5),
      resendAfterSeconds: 60,
    ),
  );

  /// عطب يُرمى بدل كل جواب — يُصفَّر بعد رمية واحدة إن كان `oneShot`.
  Failure? failure;
  bool oneShotFailure = false;

  int sendCodeCalls = 0;
  int verifyCalls = 0;
  String? lastFullName;

  Failure? _takeFailure() {
    final current = failure;
    if (current != null && oneShotFailure) failure = null;
    return current;
  }

  @override
  Future<CodeDelivery> sendCode({
    required String phone,
    CodePurpose purpose = CodePurpose.login,
  }) async {
    sendCodeCalls++;
    final refusal = _takeFailure();
    if (refusal != null) throw refusal;
    return delivery;
  }

  @override
  Future<AuthSession> verifyCode({
    required String phone,
    required String code,
    String fullName = '',
  }) async {
    verifyCalls++;
    lastFullName = fullName;
    final refusal = _takeFailure();
    if (refusal != null) throw refusal;
    storedSession = true;
    return session;
  }

  @override
  Future<bool> hasStoredSession() async => storedSession;

  @override
  Future<void> signOut() async {
    onSignOut?.call();
    storedSession = false;
  }

  @override
  Future<PhoneChangeCodes> startPhoneChange({required String newPhone}) async {
    final refusal = _takeFailure();
    if (refusal != null) throw refusal;
    return phoneChangeCodes;
  }

  @override
  Future<void> confirmPhoneChange({
    required String newPhone,
    required String currentCode,
    required String newCode,
  }) async {
    final refusal = _takeFailure();
    if (refusal != null) throw refusal;
    storedSession = false;
  }
}

final class FakeProfileRepository implements ProfileRepository {
  FakeProfileRepository({CustomerProfile? profile, this.company})
    : profile = profile ?? sampleProfile();

  CustomerProfile profile;
  CompanyProfile? company;

  /// نسخة من الكاش لا من الشبكة — لاختبار علامة «آخر تحديث» (H5).
  bool fromCache = false;
  DateTime fetchedAt = DateTime.utc(2026, 9, 1, 10);

  Failure? loadFailure;
  Failure? writeFailure;

  CompanyProfile? savedCompany;
  String? savedFullName;
  String? savedEmail;
  String? pinnedNationalId;

  /// ما يردّ به الخادم **بعد** الكتابة حين يختلف عمّا قبلها — تثبيت الهوية
  /// يقفلها مثلاً. تُترك فارغة حين لا يهمّ الفرق.
  CustomerProfile? profileAfterWrite;

  @override
  Future<Snapshot<CustomerProfile>> load() async {
    final refusal = loadFailure;
    if (refusal != null) throw refusal;
    return fromCache
        ? Snapshot.cached(profile, storedAt: fetchedAt)
        : Snapshot.fresh(profile, at: fetchedAt);
  }

  @override
  Future<CustomerProfile> update({String? fullName, String? email}) async {
    savedFullName = fullName;
    savedEmail = email;
    final refusal = writeFailure;
    if (refusal != null) throw refusal;
    return profile;
  }

  @override
  Future<CustomerProfile> setNationalId(String nationalId) async {
    pinnedNationalId = nationalId;
    final refusal = writeFailure;
    if (refusal != null) throw refusal;
    return profileAfterWrite ?? profile;
  }

  @override
  Future<CompanyProfile?> loadCompany() async {
    final refusal = loadFailure;
    if (refusal != null) throw refusal;
    return company;
  }

  @override
  Future<CompanyProfile> saveCompany(CompanyProfile company) async {
    savedCompany = company;
    final refusal = writeFailure;
    if (refusal != null) throw refusal;
    return company;
  }
}

CustomerProfile sampleProfile({
  List<LockedField> locked = const <LockedField>[
    LockedField(field: 'phone', reason: 'رقم الجوال يتغيّر بتأكيد رمزين.'),
  ],
  String nationalId = '',
  bool nationalIdVerified = false,
  bool hasCompanyProfile = false,
  bool companyProfileComplete = false,
}) => CustomerProfile(
  displayName: 'عميل الاختبار',
  fullName: 'عميل الاختبار',
  phone: '966500000001',
  email: 'a@b.com',
  accountType: 'individual',
  nationalId: nationalId,
  nationalIdVerified: nationalIdVerified,
  hasCompanyProfile: hasCompanyProfile,
  companyProfileComplete: companyProfileComplete,
  lockedFields: locked,
);
