// ignore: unused_import
import 'package:intl/intl.dart' as intl;
import 'app_localizations.dart';

// ignore_for_file: type=lint

/// The translations for Arabic (`ar`).
class AppLocalizationsAr extends AppLocalizations {
  AppLocalizationsAr([String locale = 'ar']) : super(locale);

  @override
  String get appTitle => 'حراج واحد';

  @override
  String get seedTitle => 'بذرة التطبيق';

  @override
  String get seedBody =>
      'الأساس جاهز: العربية والاتجاه، والعميل المولَّد، والتخزين المحلي، ومعالجة الأخطاء. الشاشات تبدأ بعد تثبيت مخطط الـAPI.';

  @override
  String environmentBanner(String environment) {
    return 'بيئة $environment';
  }

  @override
  String get environmentDevelopment => 'تطوير';

  @override
  String get environmentStaging => 'تجريب';

  @override
  String get environmentProduction => 'الإنتاج';

  @override
  String environmentStampedMessage(String environment, String message) {
    return '[$environment] $message';
  }

  @override
  String get pushOpen => 'فتح';

  @override
  String get retry => 'إعادة المحاولة';

  @override
  String get errorOffline => 'لا يوجد اتصال بالإنترنت.';

  @override
  String get errorTimeout => 'تعذّر الوصول إلى الخادم. حاول مرة أخرى.';

  @override
  String get errorMalformedResponse => 'وصل ردّ غير مفهوم من الخادم.';

  @override
  String get errorUnexpected => 'حدث خطأ غير متوقع في التطبيق.';

  @override
  String offlineDataNotice(DateTime date, DateTime time) {
    final intl.DateFormat dateDateFormat = intl.DateFormat.yMd(localeName);
    final String dateString = dateDateFormat.format(date);
    final intl.DateFormat timeDateFormat = intl.DateFormat.Hm(localeName);
    final String timeString = timeDateFormat.format(time);

    return 'بيانات محفوظة — آخر تحديث $dateString الساعة $timeString';
  }

  @override
  String get signInTitle => 'الدخول أو إنشاء حساب';

  @override
  String get signInIntro => 'أدخل رقم جوالك ونرسل لك رمز تحقق.';

  @override
  String get signInPhoneLabel => 'رقم الجوال';

  @override
  String get signInPhoneHint => '9665xxxxxxxx';

  @override
  String get signInSendCode => 'إرسال رمز التحقق';

  @override
  String get verifyTitle => 'رمز التحقق';

  @override
  String verifySentTo(String phone) {
    return 'أرسلنا رمزاً إلى $phone';
  }

  @override
  String get verifyCodeLabel => 'رمز التحقق';

  @override
  String get verifySubmit => 'تأكيد ودخول';

  @override
  String get verifyFullNameLabel => 'الاسم الكامل';

  @override
  String get verifyResend => 'إعادة إرسال الرمز';

  @override
  String get verifyChangePhone => 'تعديل الرقم';

  @override
  String verifyExpiresAt(DateTime time) {
    final intl.DateFormat timeDateFormat = intl.DateFormat.Hm(localeName);
    final String timeString = timeDateFormat.format(time);

    return 'ينتهي الرمز الساعة $timeString';
  }

  @override
  String waitSeconds(int seconds) {
    return 'بعد $seconds ثانية';
  }

  @override
  String get profileTitle => 'ملفي';

  @override
  String get profileFullName => 'الاسم';

  @override
  String get profileEmail => 'البريد الإلكتروني';

  @override
  String get profilePhone => 'رقم الجوال';

  @override
  String get profileAccountType => 'نوع الحساب';

  @override
  String get profileNationalId => 'رقم الهوية';

  @override
  String get profileNationalIdMissing => 'لم يُدخل بعد';

  @override
  String get profileNationalIdSave => 'تثبيت رقم الهوية';

  @override
  String get profileSave => 'حفظ';

  @override
  String get profileSaved => 'تم الحفظ';

  @override
  String get profileCompanySection => 'بيانات الشركة والعنوان الوطني';

  @override
  String get profileCompanyComplete => 'مكتملة';

  @override
  String get profileCompanyIncomplete => 'ناقصة';

  @override
  String get profileCompanyMissing => 'لا يوجد ملف شركة';

  @override
  String get profileChangePhone => 'تغيير رقم الجوال';

  @override
  String get profileSignOut => 'تسجيل الخروج';

  @override
  String get companyTitle => 'ملف الشركة';

  @override
  String get companyCreateHint =>
      'لا يوجد ملف شركة لهذا الحساب. املأ البيانات لإنشائه.';

  @override
  String get companyName => 'اسم الشركة';

  @override
  String get companyRepresentative => 'اسم المفوَّض';

  @override
  String get companyRegister => 'السجل التجاري';

  @override
  String get companyVatNumber => 'الرقم الضريبي';

  @override
  String get companyNationalAddress => 'العنوان الوطني';

  @override
  String get companyBuildingNumber => 'رقم المبنى';

  @override
  String get companyStreet => 'الشارع';

  @override
  String get companyDistrict => 'الحي';

  @override
  String get companyCity => 'المدينة';

  @override
  String get companyPostalCode => 'الرمز البريدي';

  @override
  String get companySave => 'حفظ بيانات الشركة';

  @override
  String get changePhoneTitle => 'تغيير رقم الجوال';

  @override
  String get changePhoneIntro =>
      'نرسل رمزاً إلى رقمك الحالي ورمزاً إلى الرقم الجديد. التغيير يحتاج الرمزين معاً.';

  @override
  String get changePhoneNewLabel => 'الرقم الجديد';

  @override
  String get changePhoneSendCodes => 'إرسال الرمزين';

  @override
  String changePhoneSentNotice(String phone) {
    return 'أرسلنا رمزاً إلى رقمك الحالي ورمزاً إلى $phone.';
  }

  @override
  String get changePhoneCurrentCode => 'الرمز المُرسَل إلى رقمك الحالي';

  @override
  String get changePhoneNewCode => 'الرمز المُرسَل إلى الرقم الجديد';

  @override
  String get changePhoneConfirm => 'تأكيد التغيير';

  @override
  String get changePhoneDone =>
      'تغيّر رقمك، وانتهت الجلسات المفتوحة. سجّل الدخول بالرقم الجديد.';

  @override
  String get sessionExpiredNotice => 'انتهت جلستك. سجّل الدخول من جديد.';
}
