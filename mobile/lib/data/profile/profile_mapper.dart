import '../../domain/profile/entities/customer_profile.dart';
import '../api/generated/models/company_profile.dart' as api;
import '../api/generated/models/company_profile_read.dart' as api;
import '../api/generated/models/locked_field.dart' as api;
import '../api/generated/models/profile.dart' as api;

/// تحويل نماذج المخطط المولَّدة إلى كيانات النطاق، وبالعكس عند الحفظ.
///
/// طبقة التحويل مقصودة: لولاها لسافر نموذج مولَّد إلى الشاشات، فصار كل تغيير
/// في المخطط تغييراً في كل شاشة.
extension ProfileMapper on api.Profile {
  CustomerProfile toDomain() => CustomerProfile(
    displayName: displayName,
    fullName: fullName,
    phone: phone,
    // حقل نصّي غائب يصل `null` من العقد؛ الشاشة تعرض فراغاً لا كلمة «null».
    email: email ?? '',
    accountType: accountType,
    nationalId: nationalId,
    nationalIdVerified: nationalIdVerified,
    hasCompanyProfile: hasCompanyProfile,
    companyProfileComplete: companyProfileComplete,
    lockedFields: lockedFields
        .map((locked) => locked.toDomain())
        .toList(growable: false),
  );
}

extension LockedFieldMapper on api.LockedField {
  LockedField toDomain() => LockedField(field: field, reason: reason);
}

extension CompanyProfileReadMapper on api.CompanyProfileRead {
  CompanyProfile toDomain() => CompanyProfile(
    name: name ?? '',
    representativeName: representativeName ?? '',
    commercialRegister: commercialRegister ?? '',
    vatNumber: vatNumber ?? '',
    buildingNumber: buildingNumber ?? '',
    street: street ?? '',
    district: district ?? '',
    city: city ?? '',
    postalCode: postalCode ?? '',
    isComplete: isComplete,
  );
}

extension CompanyProfileRequestMapper on CompanyProfile {
  /// `isComplete` لا يُرسَل: الخادم يقرّره ولا يقبله (`readOnly` في العقد).
  api.CompanyProfile toRequest() => api.CompanyProfile(
    name: name,
    representativeName: representativeName,
    commercialRegister: commercialRegister,
    vatNumber: vatNumber,
    buildingNumber: buildingNumber,
    street: street,
    district: district,
    city: city,
    postalCode: postalCode,
  );
}
