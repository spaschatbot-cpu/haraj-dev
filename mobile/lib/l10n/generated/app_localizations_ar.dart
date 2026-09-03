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

  @override
  String get homeTitle => 'المزادات';

  @override
  String get homeRunningSection => 'مزادات جارية';

  @override
  String get homeUpcomingSection => 'مزادات قادمة';

  @override
  String get homeEmpty => 'لا توجد مزادات جارية ولا قادمة الآن.';

  @override
  String auctionStartsAt(DateTime date, DateTime time) {
    final intl.DateFormat dateDateFormat = intl.DateFormat.yMd(localeName);
    final String dateString = dateDateFormat.format(date);
    final intl.DateFormat timeDateFormat = intl.DateFormat.Hm(localeName);
    final String timeString = timeDateFormat.format(time);

    return 'يبدأ $dateString الساعة $timeString';
  }

  @override
  String auctionEndsAt(DateTime date, DateTime time) {
    final intl.DateFormat dateDateFormat = intl.DateFormat.yMd(localeName);
    final String dateString = dateDateFormat.format(date);
    final intl.DateFormat timeDateFormat = intl.DateFormat.Hm(localeName);
    final String timeString = timeDateFormat.format(time);

    return 'ينتهي $dateString الساعة $timeString';
  }

  @override
  String auctionVehiclesCount(int count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$count مركبة',
      many: '$count مركبة',
      few: '$count مركبات',
      two: 'مركبتان',
      one: 'مركبة واحدة',
      zero: 'لا مركبات',
    );
    return '$_temp0';
  }

  @override
  String countdownToStart(String remaining) {
    return 'يبدأ بعد $remaining';
  }

  @override
  String countdownToEnd(String remaining) {
    return 'ينتهي بعد $remaining';
  }

  @override
  String countdownDaysHours(int days, int hours) {
    return '$days يوم و$hours ساعة';
  }

  @override
  String countdownHoursMinutes(int hours, int minutes) {
    return '$hours ساعة و$minutes دقيقة';
  }

  @override
  String countdownMinutes(int minutes) {
    return '$minutes دقيقة';
  }

  @override
  String get countdownLessThanMinute => 'أقل من دقيقة';

  @override
  String get countdownElapsed => 'انتهى الوقت';

  @override
  String get vehiclesTitle => 'مركبات المزاد';

  @override
  String get vehiclesEmpty => 'لا مركبات مطابقة.';

  @override
  String vehiclesResultsCount(int count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$count نتيجة',
      many: '$count نتيجة',
      few: '$count نتائج',
      two: 'نتيجتان',
      one: 'نتيجة واحدة',
      zero: 'لا نتائج',
    );
    return '$_temp0';
  }

  @override
  String get searchHint => 'ماركة أو طراز أو رقم لوت';

  @override
  String get filterMake => 'الماركة';

  @override
  String get filterYearFrom => 'من سنة';

  @override
  String get filterYearTo => 'إلى سنة';

  @override
  String get filterApply => 'طبّق الترشيح';

  @override
  String get filterClear => 'إزالة الترشيح';

  @override
  String vehicleLot(String lotNumber) {
    return 'لوت $lotNumber';
  }

  @override
  String get vehicleReservePrice => 'سعر الوقوف';

  @override
  String get vehicleReservePriceUnset => 'لم يُحدَّد';

  @override
  String vehicleBidsCount(int count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$count مزايدة',
      many: '$count مزايدة',
      few: '$count مزايدات',
      two: 'مزايدتان',
      one: 'مزايدة واحدة',
      zero: 'لا مزايدات',
    );
    return '$_temp0';
  }

  @override
  String get vehicleNoImage => 'لا توجد صورة';

  @override
  String get vehicleNoImages => 'لا صور لهذه المركبة.';

  @override
  String get vehicleImageFailed => 'تعذّر تحميل الصورة';

  @override
  String vehicleImageCounter(int index, int total) {
    return '$index من $total';
  }

  @override
  String get vehicleSpecifications => 'المواصفات';

  @override
  String get vehicleNoSpecifications => 'لا مواصفات مسجَّلة لهذه المركبة.';

  @override
  String get vehicleBiddingOpen => 'المزايدة مفتوحة';

  @override
  String get vehicleBiddingClosed => 'المزايدة مقفلة';

  @override
  String get myActivityTitle => 'حسابي';

  @override
  String get tabParticipations => 'مشاركاتي';

  @override
  String get tabPurchases => 'مشترياتي';

  @override
  String get tabInvoices => 'فواتيري';

  @override
  String get emptyParticipations => 'لم تدخل أي مزاد حتى الآن.';

  @override
  String get emptyPurchases => 'لم ترسُ عليك أي مركبة حتى الآن.';

  @override
  String get emptyInvoices => 'لا توجد فواتير على حسابك.';

  @override
  String participationBidsCount(int count) {
    return 'عدد مزايداتي: $count';
  }

  @override
  String participationEndsAt(DateTime date, DateTime time) {
    final intl.DateFormat dateDateFormat = intl.DateFormat.yMd(localeName);
    final String dateString = dateDateFormat.format(date);
    final intl.DateFormat timeDateFormat = intl.DateFormat.Hm(localeName);
    final String timeString = timeDateFormat.format(time);

    return 'ينتهي $dateString الساعة $timeString';
  }

  @override
  String get insuranceInThisAuction => 'تأميني في هذا المزاد';

  @override
  String purchaseLotNumber(String lot) {
    return 'اللوت $lot';
  }

  @override
  String purchaseAwardedAt(DateTime date) {
    final intl.DateFormat dateDateFormat = intl.DateFormat.yMd(localeName);
    final String dateString = dateDateFormat.format(date);

    return 'رسَت عليك $dateString';
  }

  @override
  String get purchaseNoInvoiceYet => 'لم تصدر فاتورة لهذه المركبة بعد.';

  @override
  String invoiceNumber(String number) {
    return 'فاتورة رقم $number';
  }

  @override
  String invoiceIssuedAt(DateTime date) {
    final intl.DateFormat dateDateFormat = intl.DateFormat.yMd(localeName);
    final String dateString = dateDateFormat.format(date);

    return 'صدرت $dateString';
  }

  @override
  String get invoiceTotal => 'الإجمالي';

  @override
  String get invoicePaid => 'المسدَّد';

  @override
  String get invoiceDue => 'المتبقّي';

  @override
  String get invoiceInsuranceEffect => 'أثرها على تأميني';
}
