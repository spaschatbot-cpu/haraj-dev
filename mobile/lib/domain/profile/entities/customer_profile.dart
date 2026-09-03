/// الملف الشخصي كما يعرضه التطبيق.
///
/// **ما يُقفل وسببه يأتيان من الخادم** (`locked_fields`)، ولا يستنتجهما التطبيق:
/// قاعدة «الهوية الصحيحة تُثبَّت والخاطئة تُصحَّح» (T606) قاعدة عمل واحدة، ونسخة
/// منها في الشاشة تفترق عن الأصل عند أول تعديل — فيسمع العميل جوابين لسؤال
/// واحد (المادة ٤-٥).
library;

/// حقل يُعرض ولا يُعدَّل، ومعه سببه العربي كما كتبه الخادم.
final class LockedField {
  const LockedField({required this.field, required this.reason});

  /// اسم الحقل كما في العقد (`phone`، `national_id`).
  final String field;

  /// سبب عربي جاهز للعرض — يُعرض حرفياً ولا يُعاد صوغه.
  final String reason;
}

/// أسماء الحقول التي تسأل عنها الشاشة. مكتوبة مرة واحدة لأن الخطأ المطبعي في
/// اسم حقل يعطي «غير مقفول» صامتاً.
abstract final class ProfileFields {
  static const String phone = 'phone';
  static const String nationalId = 'national_id';
}

final class CustomerProfile {
  const CustomerProfile({
    required this.displayName,
    required this.fullName,
    required this.phone,
    required this.email,
    required this.accountType,
    required this.nationalId,
    required this.nationalIdVerified,
    required this.hasCompanyProfile,
    required this.companyProfileComplete,
    required this.lockedFields,
  });

  /// الاسم الذي يعرض به الخادم صاحب الحساب — شركةً كان أو فرداً.
  final String displayName;
  final String fullName;
  final String phone;
  final String email;
  final String accountType;

  /// قد يكون فارغاً (لم يُدخل بعد) أو غير صحيح (يجوز تصحيحه).
  final String nationalId;

  /// هوية صحيحة على الحساب — عندها يصل `national_id` ضمن `lockedFields`.
  final bool nationalIdVerified;

  final bool hasCompanyProfile;
  final bool companyProfileComplete;

  final List<LockedField> lockedFields;

  /// سبب قفل [field]، أو `null` إن لم يكن مقفولاً.
  ///
  /// نقطة القراءة الوحيدة: الشاشة تسأل «هل هذا مقفول ولماذا» ولا تقرّر بنفسها.
  LockedField? lockOn(String field) {
    for (final locked in lockedFields) {
      if (locked.field == field) return locked;
    }
    return null;
  }
}

/// ملف الشركة وعنوانها الوطني (ZATCA).
final class CompanyProfile {
  const CompanyProfile({
    required this.name,
    required this.representativeName,
    required this.commercialRegister,
    required this.vatNumber,
    required this.buildingNumber,
    required this.street,
    required this.district,
    required this.city,
    required this.postalCode,
    required this.isComplete,
  });

  /// شركة فارغة — للحساب الذي لا شركة له بعد (الخادم يردّ 404).
  const CompanyProfile.blank()
    : name = '',
      representativeName = '',
      commercialRegister = '',
      vatNumber = '',
      buildingNumber = '',
      street = '',
      district = '',
      city = '',
      postalCode = '',
      isComplete = false;

  final String name;
  final String representativeName;
  final String commercialRegister;
  final String vatNumber;
  final String buildingNumber;
  final String street;
  final String district;
  final String city;
  final String postalCode;

  /// هل تكفي البيانات لإصدار فاتورة ضريبية — **الخادم** يقرّرها.
  ///
  /// شرط الاكتمال قاعدة عمل لها تاريخ (إعفاء الشركات السابقة على العنوان
  /// الوطني)، فحسابها في الشاشة يعني قاعدة ثانية تختلف عن قاعدة الفوترة.
  final bool isComplete;
}
