import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter/widgets.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:intl/intl.dart' as intl;

import 'app_localizations_ar.dart';
import 'app_localizations_en.dart';

// ignore_for_file: type=lint

/// Callers can lookup localized strings with an instance of AppLocalizations
/// returned by `AppLocalizations.of(context)`.
///
/// Applications need to include `AppLocalizations.delegate()` in their app's
/// `localizationDelegates` list, and the locales they support in the app's
/// `supportedLocales` list. For example:
///
/// ```dart
/// import 'generated/app_localizations.dart';
///
/// return MaterialApp(
///   localizationsDelegates: AppLocalizations.localizationsDelegates,
///   supportedLocales: AppLocalizations.supportedLocales,
///   home: MyApplicationHome(),
/// );
/// ```
///
/// ## Update pubspec.yaml
///
/// Please make sure to update your pubspec.yaml to include the following
/// packages:
///
/// ```yaml
/// dependencies:
///   # Internationalization support.
///   flutter_localizations:
///     sdk: flutter
///   intl: any # Use the pinned version from flutter_localizations
///
///   # Rest of dependencies
/// ```
///
/// ## iOS Applications
///
/// iOS applications define key application metadata, including supported
/// locales, in an Info.plist file that is built into the application bundle.
/// To configure the locales supported by your app, you’ll need to edit this
/// file.
///
/// First, open your project’s ios/Runner.xcworkspace Xcode workspace file.
/// Then, in the Project Navigator, open the Info.plist file under the Runner
/// project’s Runner folder.
///
/// Next, select the Information Property List item, select Add Item from the
/// Editor menu, then select Localizations from the pop-up menu.
///
/// Select and expand the newly-created Localizations item then, for each
/// locale your application supports, add a new item and select the locale
/// you wish to add from the pop-up menu in the Value field. This list should
/// be consistent with the languages listed in the AppLocalizations.supportedLocales
/// property.
abstract class AppLocalizations {
  AppLocalizations(String locale)
    : localeName = intl.Intl.canonicalizedLocale(locale.toString());

  final String localeName;

  static AppLocalizations of(BuildContext context) {
    return Localizations.of<AppLocalizations>(context, AppLocalizations)!;
  }

  static const LocalizationsDelegate<AppLocalizations> delegate =
      _AppLocalizationsDelegate();

  /// A list of this localizations delegate along with the default localizations
  /// delegates.
  ///
  /// Returns a list of localizations delegates containing this delegate along with
  /// GlobalMaterialLocalizations.delegate, GlobalCupertinoLocalizations.delegate,
  /// and GlobalWidgetsLocalizations.delegate.
  ///
  /// Additional delegates can be added by appending to this list in
  /// MaterialApp. This list does not have to be used at all if a custom list
  /// of delegates is preferred or required.
  static const List<LocalizationsDelegate<dynamic>> localizationsDelegates =
      <LocalizationsDelegate<dynamic>>[
        delegate,
        GlobalMaterialLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
      ];

  /// A list of this localizations delegate's supported locales.
  static const List<Locale> supportedLocales = <Locale>[
    Locale('ar'),
    Locale('en'),
  ];

  /// اسم التطبيق كما يظهر في مبدّل التطبيقات
  ///
  /// In ar, this message translates to:
  /// **'حراج واحد'**
  String get appTitle;

  /// عنوان الشاشة المؤقّتة التي تسبق شاشات المجموعة ب
  ///
  /// In ar, this message translates to:
  /// **'بذرة التطبيق'**
  String get seedTitle;

  /// شرح حالة البذرة
  ///
  /// In ar, this message translates to:
  /// **'الأساس جاهز: العربية والاتجاه، والعميل المولَّد، والتخزين المحلي، ومعالجة الأخطاء. الشاشات تبدأ بعد تثبيت مخطط الـAPI.'**
  String get seedBody;

  /// لافتة تظهر في كل بناء غير إنتاجي — المادة ٥-٦
  ///
  /// In ar, this message translates to:
  /// **'بيئة {environment}'**
  String environmentBanner(String environment);

  /// No description provided for @environmentDevelopment.
  ///
  /// In ar, this message translates to:
  /// **'تطوير'**
  String get environmentDevelopment;

  /// No description provided for @environmentStaging.
  ///
  /// In ar, this message translates to:
  /// **'تجريب'**
  String get environmentStaging;

  /// لا يظهر في لافتة ولا ختم — موجود كي يبقى تحويل البيئات شاملاً
  ///
  /// In ar, this message translates to:
  /// **'الإنتاج'**
  String get environmentProduction;

  /// كل رسالة تُعرض للمستخدم من بناء غير إنتاجي تحمل اسم بيئتها — المادة ٥-٦
  ///
  /// In ar, this message translates to:
  /// **'[{environment}] {message}'**
  String environmentStampedMessage(String environment, String message);

  /// زرّ على لافتة الإشعار الواصل والتطبيق مفتوح — الفتح قرار المستخدم
  ///
  /// In ar, this message translates to:
  /// **'فتح'**
  String get pushOpen;

  /// No description provided for @retry.
  ///
  /// In ar, this message translates to:
  /// **'إعادة المحاولة'**
  String get retry;

  /// الخادم لم يُسأل أصلاً — حالة لا يعرفها الخادم، فالنصّ محلي
  ///
  /// In ar, this message translates to:
  /// **'لا يوجد اتصال بالإنترنت.'**
  String get errorOffline;

  /// انقضت المهلة قبل ردّ مفهوم
  ///
  /// In ar, this message translates to:
  /// **'تعذّر الوصول إلى الخادم. حاول مرة أخرى.'**
  String get errorTimeout;

  /// ردّ لم يطابق الشكل الموحّد — لا نخترع له رسالة
  ///
  /// In ar, this message translates to:
  /// **'وصل ردّ غير مفهوم من الخادم.'**
  String get errorMalformedResponse;

  /// عطب في التطبيق نفسه، لا في الخادم
  ///
  /// In ar, this message translates to:
  /// **'حدث خطأ غير متوقع في التطبيق.'**
  String get errorUnexpected;

  /// علامة «آخر تحديث» فوق أي شاشة تعرض بيانات من الكاش — معيار H5
  ///
  /// In ar, this message translates to:
  /// **'بيانات محفوظة — آخر تحديث {date} الساعة {time}'**
  String offlineDataNotice(DateTime date, DateTime time);

  /// عنوان شاشة الدخول — نفس المسار للتسجيل والدخول
  ///
  /// In ar, this message translates to:
  /// **'الدخول أو إنشاء حساب'**
  String get signInTitle;

  /// No description provided for @signInIntro.
  ///
  /// In ar, this message translates to:
  /// **'أدخل رقم جوالك ونرسل لك رمز تحقق.'**
  String get signInIntro;

  /// No description provided for @signInPhoneLabel.
  ///
  /// In ar, this message translates to:
  /// **'رقم الجوال'**
  String get signInPhoneLabel;

  /// شكل الرقم كما يقبله الخادم — تلميح لا تحقّق
  ///
  /// In ar, this message translates to:
  /// **'9665xxxxxxxx'**
  String get signInPhoneHint;

  /// No description provided for @signInSendCode.
  ///
  /// In ar, this message translates to:
  /// **'إرسال رمز التحقق'**
  String get signInSendCode;

  /// No description provided for @verifyTitle.
  ///
  /// In ar, this message translates to:
  /// **'رمز التحقق'**
  String get verifyTitle;

  /// No description provided for @verifySentTo.
  ///
  /// In ar, this message translates to:
  /// **'أرسلنا رمزاً إلى {phone}'**
  String verifySentTo(String phone);

  /// No description provided for @verifyCodeLabel.
  ///
  /// In ar, this message translates to:
  /// **'رمز التحقق'**
  String get verifyCodeLabel;

  /// No description provided for @verifySubmit.
  ///
  /// In ar, this message translates to:
  /// **'تأكيد ودخول'**
  String get verifySubmit;

  /// No description provided for @verifyFullNameLabel.
  ///
  /// In ar, this message translates to:
  /// **'الاسم الكامل'**
  String get verifyFullNameLabel;

  /// No description provided for @verifyResend.
  ///
  /// In ar, this message translates to:
  /// **'إعادة إرسال الرمز'**
  String get verifyResend;

  /// No description provided for @verifyChangePhone.
  ///
  /// In ar, this message translates to:
  /// **'تعديل الرقم'**
  String get verifyChangePhone;

  /// بالتوقيت السعودي — التحويل عند حافة العرض وحدها
  ///
  /// In ar, this message translates to:
  /// **'ينتهي الرمز الساعة {time}'**
  String verifyExpiresAt(DateTime time);

  /// عدّاد الانتظار قبل السماح بمحاولة جديدة — الثواني من الخادم
  ///
  /// In ar, this message translates to:
  /// **'بعد {seconds} ثانية'**
  String waitSeconds(int seconds);

  /// No description provided for @profileTitle.
  ///
  /// In ar, this message translates to:
  /// **'ملفي'**
  String get profileTitle;

  /// No description provided for @profileFullName.
  ///
  /// In ar, this message translates to:
  /// **'الاسم'**
  String get profileFullName;

  /// No description provided for @profileEmail.
  ///
  /// In ar, this message translates to:
  /// **'البريد الإلكتروني'**
  String get profileEmail;

  /// No description provided for @profilePhone.
  ///
  /// In ar, this message translates to:
  /// **'رقم الجوال'**
  String get profilePhone;

  /// No description provided for @profileAccountType.
  ///
  /// In ar, this message translates to:
  /// **'نوع الحساب'**
  String get profileAccountType;

  /// No description provided for @profileNationalId.
  ///
  /// In ar, this message translates to:
  /// **'رقم الهوية'**
  String get profileNationalId;

  /// No description provided for @profileNationalIdMissing.
  ///
  /// In ar, this message translates to:
  /// **'لم يُدخل بعد'**
  String get profileNationalIdMissing;

  /// No description provided for @profileNationalIdSave.
  ///
  /// In ar, this message translates to:
  /// **'تثبيت رقم الهوية'**
  String get profileNationalIdSave;

  /// No description provided for @profileSave.
  ///
  /// In ar, this message translates to:
  /// **'حفظ'**
  String get profileSave;

  /// No description provided for @profileSaved.
  ///
  /// In ar, this message translates to:
  /// **'تم الحفظ'**
  String get profileSaved;

  /// No description provided for @profileCompanySection.
  ///
  /// In ar, this message translates to:
  /// **'بيانات الشركة والعنوان الوطني'**
  String get profileCompanySection;

  /// No description provided for @profileCompanyComplete.
  ///
  /// In ar, this message translates to:
  /// **'مكتملة'**
  String get profileCompanyComplete;

  /// No description provided for @profileCompanyIncomplete.
  ///
  /// In ar, this message translates to:
  /// **'ناقصة'**
  String get profileCompanyIncomplete;

  /// No description provided for @profileCompanyMissing.
  ///
  /// In ar, this message translates to:
  /// **'لا يوجد ملف شركة'**
  String get profileCompanyMissing;

  /// No description provided for @profileChangePhone.
  ///
  /// In ar, this message translates to:
  /// **'تغيير رقم الجوال'**
  String get profileChangePhone;

  /// No description provided for @profileSignOut.
  ///
  /// In ar, this message translates to:
  /// **'تسجيل الخروج'**
  String get profileSignOut;

  /// No description provided for @companyTitle.
  ///
  /// In ar, this message translates to:
  /// **'ملف الشركة'**
  String get companyTitle;

  /// No description provided for @companyCreateHint.
  ///
  /// In ar, this message translates to:
  /// **'لا يوجد ملف شركة لهذا الحساب. املأ البيانات لإنشائه.'**
  String get companyCreateHint;

  /// No description provided for @companyName.
  ///
  /// In ar, this message translates to:
  /// **'اسم الشركة'**
  String get companyName;

  /// No description provided for @companyRepresentative.
  ///
  /// In ar, this message translates to:
  /// **'اسم المفوَّض'**
  String get companyRepresentative;

  /// No description provided for @companyRegister.
  ///
  /// In ar, this message translates to:
  /// **'السجل التجاري'**
  String get companyRegister;

  /// No description provided for @companyVatNumber.
  ///
  /// In ar, this message translates to:
  /// **'الرقم الضريبي'**
  String get companyVatNumber;

  /// No description provided for @companyNationalAddress.
  ///
  /// In ar, this message translates to:
  /// **'العنوان الوطني'**
  String get companyNationalAddress;

  /// No description provided for @companyBuildingNumber.
  ///
  /// In ar, this message translates to:
  /// **'رقم المبنى'**
  String get companyBuildingNumber;

  /// No description provided for @companyStreet.
  ///
  /// In ar, this message translates to:
  /// **'الشارع'**
  String get companyStreet;

  /// No description provided for @companyDistrict.
  ///
  /// In ar, this message translates to:
  /// **'الحي'**
  String get companyDistrict;

  /// No description provided for @companyCity.
  ///
  /// In ar, this message translates to:
  /// **'المدينة'**
  String get companyCity;

  /// No description provided for @companyPostalCode.
  ///
  /// In ar, this message translates to:
  /// **'الرمز البريدي'**
  String get companyPostalCode;

  /// No description provided for @companySave.
  ///
  /// In ar, this message translates to:
  /// **'حفظ بيانات الشركة'**
  String get companySave;

  /// No description provided for @changePhoneTitle.
  ///
  /// In ar, this message translates to:
  /// **'تغيير رقم الجوال'**
  String get changePhoneTitle;

  /// سبب الرمزين — الرقم الجديد وحده كان مسار الاستيلاء على الحساب في v1
  ///
  /// In ar, this message translates to:
  /// **'نرسل رمزاً إلى رقمك الحالي ورمزاً إلى الرقم الجديد. التغيير يحتاج الرمزين معاً.'**
  String get changePhoneIntro;

  /// No description provided for @changePhoneNewLabel.
  ///
  /// In ar, this message translates to:
  /// **'الرقم الجديد'**
  String get changePhoneNewLabel;

  /// No description provided for @changePhoneSendCodes.
  ///
  /// In ar, this message translates to:
  /// **'إرسال الرمزين'**
  String get changePhoneSendCodes;

  /// No description provided for @changePhoneSentNotice.
  ///
  /// In ar, this message translates to:
  /// **'أرسلنا رمزاً إلى رقمك الحالي ورمزاً إلى {phone}.'**
  String changePhoneSentNotice(String phone);

  /// No description provided for @changePhoneCurrentCode.
  ///
  /// In ar, this message translates to:
  /// **'الرمز المُرسَل إلى رقمك الحالي'**
  String get changePhoneCurrentCode;

  /// No description provided for @changePhoneNewCode.
  ///
  /// In ar, this message translates to:
  /// **'الرمز المُرسَل إلى الرقم الجديد'**
  String get changePhoneNewCode;

  /// No description provided for @changePhoneConfirm.
  ///
  /// In ar, this message translates to:
  /// **'تأكيد التغيير'**
  String get changePhoneConfirm;

  /// الخادم يُلغي كل الجلسات عند نجاح التغيير، فالخروج جزء من النجاح لا عطل
  ///
  /// In ar, this message translates to:
  /// **'تغيّر رقمك، وانتهت الجلسات المفتوحة. سجّل الدخول بالرقم الجديد.'**
  String get changePhoneDone;

  /// يُعرض عند إعادة التوجيه بعد 401 لم ينفع معه التجديد
  ///
  /// In ar, this message translates to:
  /// **'انتهت جلستك. سجّل الدخول من جديد.'**
  String get sessionExpiredNotice;

  /// عنوان الرئيسية — T707
  ///
  /// In ar, this message translates to:
  /// **'المزادات'**
  String get homeTitle;

  /// No description provided for @homeRunningSection.
  ///
  /// In ar, this message translates to:
  /// **'مزادات جارية'**
  String get homeRunningSection;

  /// No description provided for @homeUpcomingSection.
  ///
  /// In ar, this message translates to:
  /// **'مزادات قادمة'**
  String get homeUpcomingSection;

  /// الحالة الفارغة للرئيسية — شاشة بلا حالة فارغة تبدو معطوبة
  ///
  /// In ar, this message translates to:
  /// **'لا توجد مزادات جارية ولا قادمة الآن.'**
  String get homeEmpty;

  /// بالتوقيت السعودي — التحويل في SaudiTime وحدها
  ///
  /// In ar, this message translates to:
  /// **'يبدأ {date} الساعة {time}'**
  String auctionStartsAt(DateTime date, DateTime time);

  /// No description provided for @auctionEndsAt.
  ///
  /// In ar, this message translates to:
  /// **'ينتهي {date} الساعة {time}'**
  String auctionEndsAt(DateTime date, DateTime time);

  /// عدد مركبات المزاد كما عدّه الخادم
  ///
  /// In ar, this message translates to:
  /// **'{count, plural, zero{لا مركبات} one{مركبة واحدة} two{مركبتان} few{{count} مركبات} many{{count} مركبة} other{{count} مركبة}}'**
  String auctionVehiclesCount(int count);

  /// العدّاد التنازلي لمزاد لم يبدأ — T707
  ///
  /// In ar, this message translates to:
  /// **'يبدأ بعد {remaining}'**
  String countdownToStart(String remaining);

  /// No description provided for @countdownToEnd.
  ///
  /// In ar, this message translates to:
  /// **'ينتهي بعد {remaining}'**
  String countdownToEnd(String remaining);

  /// No description provided for @countdownDaysHours.
  ///
  /// In ar, this message translates to:
  /// **'{days} يوم و{hours} ساعة'**
  String countdownDaysHours(int days, int hours);

  /// No description provided for @countdownHoursMinutes.
  ///
  /// In ar, this message translates to:
  /// **'{hours} ساعة و{minutes} دقيقة'**
  String countdownHoursMinutes(int hours, int minutes);

  /// No description provided for @countdownMinutes.
  ///
  /// In ar, this message translates to:
  /// **'{minutes} دقيقة'**
  String countdownMinutes(int minutes);

  /// No description provided for @countdownLessThanMinute.
  ///
  /// In ar, this message translates to:
  /// **'أقل من دقيقة'**
  String get countdownLessThanMinute;

  /// الوقت مضى بحسب ساعة الجهاز — إخبار لا قرار: الخادم وحده يقرّر إن كانت المزايدة مفتوحة
  ///
  /// In ar, this message translates to:
  /// **'انتهى الوقت'**
  String get countdownElapsed;

  /// عنوان قائمة مركبات المزاد — T708
  ///
  /// In ar, this message translates to:
  /// **'مركبات المزاد'**
  String get vehiclesTitle;

  /// No description provided for @vehiclesEmpty.
  ///
  /// In ar, this message translates to:
  /// **'لا مركبات مطابقة.'**
  String get vehiclesEmpty;

  /// العدد الكلي من الخادم لا طول الصفحة
  ///
  /// In ar, this message translates to:
  /// **'{count, plural, zero{لا نتائج} one{نتيجة واحدة} two{نتيجتان} few{{count} نتائج} many{{count} نتيجة} other{{count} نتيجة}}'**
  String vehiclesResultsCount(int count);

  /// No description provided for @searchHint.
  ///
  /// In ar, this message translates to:
  /// **'ماركة أو طراز أو رقم لوت'**
  String get searchHint;

  /// No description provided for @filterMake.
  ///
  /// In ar, this message translates to:
  /// **'الماركة'**
  String get filterMake;

  /// No description provided for @filterYearFrom.
  ///
  /// In ar, this message translates to:
  /// **'من سنة'**
  String get filterYearFrom;

  /// No description provided for @filterYearTo.
  ///
  /// In ar, this message translates to:
  /// **'إلى سنة'**
  String get filterYearTo;

  /// No description provided for @filterApply.
  ///
  /// In ar, this message translates to:
  /// **'طبّق الترشيح'**
  String get filterApply;

  /// No description provided for @filterClear.
  ///
  /// In ar, this message translates to:
  /// **'إزالة الترشيح'**
  String get filterClear;

  /// No description provided for @vehicleLot.
  ///
  /// In ar, this message translates to:
  /// **'لوت {lotNumber}'**
  String vehicleLot(String lotNumber);

  /// الحقل الوحيد لسعر المركبة — دليل النظام §8-3
  ///
  /// In ar, this message translates to:
  /// **'سعر الوقوف'**
  String get vehicleReservePrice;

  /// مركبة بلا سعر وقوف ليست مركبة سعرها صفر
  ///
  /// In ar, this message translates to:
  /// **'لم يُحدَّد'**
  String get vehicleReservePriceUnset;

  /// عدد المزايدات لا مبلغها — المزاد مغلق
  ///
  /// In ar, this message translates to:
  /// **'{count, plural, zero{لا مزايدات} one{مزايدة واحدة} two{مزايدتان} few{{count} مزايدات} many{{count} مزايدة} other{{count} مزايدة}}'**
  String vehicleBidsCount(int count);

  /// No description provided for @vehicleNoImage.
  ///
  /// In ar, this message translates to:
  /// **'لا توجد صورة'**
  String get vehicleNoImage;

  /// No description provided for @vehicleNoImages.
  ///
  /// In ar, this message translates to:
  /// **'لا صور لهذه المركبة.'**
  String get vehicleNoImages;

  /// فشل صورة واحدة لا يُسقط الشاشة
  ///
  /// In ar, this message translates to:
  /// **'تعذّر تحميل الصورة'**
  String get vehicleImageFailed;

  /// No description provided for @vehicleImageCounter.
  ///
  /// In ar, this message translates to:
  /// **'{index} من {total}'**
  String vehicleImageCounter(int index, int total);

  /// No description provided for @vehicleSpecifications.
  ///
  /// In ar, this message translates to:
  /// **'المواصفات'**
  String get vehicleSpecifications;

  /// No description provided for @vehicleNoSpecifications.
  ///
  /// In ar, this message translates to:
  /// **'لا مواصفات مسجَّلة لهذه المركبة.'**
  String get vehicleNoSpecifications;

  /// حالة يقرّرها الخادم ويعرضها التطبيق
  ///
  /// In ar, this message translates to:
  /// **'المزايدة مفتوحة'**
  String get vehicleBiddingOpen;

  /// No description provided for @vehicleBiddingClosed.
  ///
  /// In ar, this message translates to:
  /// **'المزايدة مقفلة'**
  String get vehicleBiddingClosed;

  /// عنوان شاشة مشاركاتي ومشترياتي وفواتيري
  ///
  /// In ar, this message translates to:
  /// **'حسابي'**
  String get myActivityTitle;

  /// No description provided for @tabParticipations.
  ///
  /// In ar, this message translates to:
  /// **'مشاركاتي'**
  String get tabParticipations;

  /// No description provided for @tabPurchases.
  ///
  /// In ar, this message translates to:
  /// **'مشترياتي'**
  String get tabPurchases;

  /// No description provided for @tabInvoices.
  ///
  /// In ar, this message translates to:
  /// **'فواتيري'**
  String get tabInvoices;

  /// الحالة الفارغة — قائمة بلا صفوف ليست عطلاً ولا تُترك بيضاء
  ///
  /// In ar, this message translates to:
  /// **'لم تدخل أي مزاد حتى الآن.'**
  String get emptyParticipations;

  /// No description provided for @emptyPurchases.
  ///
  /// In ar, this message translates to:
  /// **'لم ترسُ عليك أي مركبة حتى الآن.'**
  String get emptyPurchases;

  /// No description provided for @emptyInvoices.
  ///
  /// In ar, this message translates to:
  /// **'لا توجد فواتير على حسابك.'**
  String get emptyInvoices;

  /// عدد المزايدات في مزاد — يعدّها الخادم ولا تُحسب هنا
  ///
  /// In ar, this message translates to:
  /// **'عدد مزايداتي: {count}'**
  String participationBidsCount(int count);

  /// No description provided for @participationEndsAt.
  ///
  /// In ar, this message translates to:
  /// **'ينتهي {date} الساعة {time}'**
  String participationEndsAt(DateTime date, DateTime time);

  /// عنوان سطر حالة التأمين — الحالة نفسها نصّها من الخادم
  ///
  /// In ar, this message translates to:
  /// **'تأميني في هذا المزاد'**
  String get insuranceInThisAuction;

  /// No description provided for @purchaseLotNumber.
  ///
  /// In ar, this message translates to:
  /// **'اللوت {lot}'**
  String purchaseLotNumber(String lot);

  /// No description provided for @purchaseAwardedAt.
  ///
  /// In ar, this message translates to:
  /// **'رسَت عليك {date}'**
  String purchaseAwardedAt(DateTime date);

  /// غياب الفاتورة حالة تُعرض، لا فراغ يُملأ باجتهاد
  ///
  /// In ar, this message translates to:
  /// **'لم تصدر فاتورة لهذه المركبة بعد.'**
  String get purchaseNoInvoiceYet;

  /// No description provided for @invoiceNumber.
  ///
  /// In ar, this message translates to:
  /// **'فاتورة رقم {number}'**
  String invoiceNumber(String number);

  /// No description provided for @invoiceIssuedAt.
  ///
  /// In ar, this message translates to:
  /// **'صدرت {date}'**
  String invoiceIssuedAt(DateTime date);

  /// No description provided for @invoiceTotal.
  ///
  /// In ar, this message translates to:
  /// **'الإجمالي'**
  String get invoiceTotal;

  /// No description provided for @invoicePaid.
  ///
  /// In ar, this message translates to:
  /// **'المسدَّد'**
  String get invoicePaid;

  /// يصل محسوباً من الخادم — لا يُطرح في التطبيق
  ///
  /// In ar, this message translates to:
  /// **'المتبقّي'**
  String get invoiceDue;

  /// عنوان الشرح؛ نصّ الشرح نفسه يأتي من الخادم كما هو
  ///
  /// In ar, this message translates to:
  /// **'أثرها على تأميني'**
  String get invoiceInsuranceEffect;

  /// عنوان شاشة المحفظة — T711
  ///
  /// In ar, this message translates to:
  /// **'محفظتي'**
  String get walletTitle;

  /// لحظة قراءة الدفتر كما أرسلها الخادم
  ///
  /// In ar, this message translates to:
  /// **'بحسب الدفتر في {date} الساعة {time}'**
  String walletAsOf(DateTime date, DateTime time);

  /// No description provided for @walletEmpty.
  ///
  /// In ar, this message translates to:
  /// **'لا أرصدة على حسابك بعد.'**
  String get walletEmpty;

  /// كل حجز مسمّى: أي مزاد أو أي فاتورة
  ///
  /// In ar, this message translates to:
  /// **'لماذا هذا المبلغ محجوز'**
  String get walletHoldsTitle;

  /// المادة ١-٦: كل رقم يُفتح على قيوده
  ///
  /// In ar, this message translates to:
  /// **'الحركات التي تفسّر هذا الرقم'**
  String get walletOpenStatement;

  /// عنوان شاشة الشحن — T713
  ///
  /// In ar, this message translates to:
  /// **'شحن التأمين بالبطاقة'**
  String get topUpTitle;

  /// No description provided for @topUpStart.
  ///
  /// In ar, this message translates to:
  /// **'ابدأ الشحن'**
  String get topUpStart;

  /// لا خانة مبلغ: الخادم يرفض طلباً يسمّي مبلغه
  ///
  /// In ar, this message translates to:
  /// **'المبلغ يحدّده النظام. تُفتح لك صفحة الدفع في المتصفح، ثم نسأل الخادم عن النتيجة.'**
  String get topUpAmountFromServer;

  /// No description provided for @topUpWaiting.
  ///
  /// In ar, this message translates to:
  /// **'بانتظار تأكيد البوابة للخادم.'**
  String get topUpWaiting;

  /// No description provided for @topUpCheckStatus.
  ///
  /// In ar, this message translates to:
  /// **'تحقّق من حالة الشحن'**
  String get topUpCheckStatus;

  /// يشرح للعميل لماذا لا تتغيّر الحالة بمجرّد عودته
  ///
  /// In ar, this message translates to:
  /// **'الحالة مقروءة من سجلّ الخادم لا من رابط العودة، ورصيدك يتحرّك حين تؤكّد البوابة الدفع للخادم.'**
  String get topUpStatusFromServer;

  /// تعذّر الفتح على الجهاز — حالة لا يعرفها الخادم فالنصّ محلي
  ///
  /// In ar, this message translates to:
  /// **'تعذّر فتح صفحة الدفع. طلب الشحن محفوظ، وتقدر تفتحها من جديد.'**
  String get topUpGatewayNotOpened;

  /// No description provided for @topUpOpenGateway.
  ///
  /// In ar, this message translates to:
  /// **'افتح صفحة الدفع'**
  String get topUpOpenGateway;

  /// عنوان شاشة الحركات — T712
  ///
  /// In ar, this message translates to:
  /// **'كشف الحركات'**
  String get transactionsTitle;

  /// No description provided for @transactionsAll.
  ///
  /// In ar, this message translates to:
  /// **'كل الحركات على حسابك، الأحدث أولاً.'**
  String get transactionsAll;

  /// يظهر حين يُفتح الكشف من رقم في المحفظة — المادة ١-٦
  ///
  /// In ar, this message translates to:
  /// **'مرشَّح على دلو واحد.'**
  String get transactionsFiltered;

  /// No description provided for @transactionsShowAll.
  ///
  /// In ar, this message translates to:
  /// **'اعرض كل الحركات'**
  String get transactionsShowAll;

  /// No description provided for @transactionsEmpty.
  ///
  /// In ar, this message translates to:
  /// **'لا حركات.'**
  String get transactionsEmpty;

  /// عدد الحركات كما قاله الخادم — عدد لا مبلغ
  ///
  /// In ar, this message translates to:
  /// **'{count} حركة'**
  String transactionsTotal(int count);

  /// No description provided for @transactionsLoadMore.
  ///
  /// In ar, this message translates to:
  /// **'تحميل المزيد'**
  String get transactionsLoadMore;

  /// اتجاه الحركة كما قاله الخادم — لقارئ الشاشة
  ///
  /// In ar, this message translates to:
  /// **'وارد'**
  String get movementIncoming;

  /// No description provided for @movementOutgoing.
  ///
  /// In ar, this message translates to:
  /// **'صادر'**
  String get movementOutgoing;

  /// No description provided for @movementReference.
  ///
  /// In ar, this message translates to:
  /// **'المرجع {reference}'**
  String movementReference(String reference);

  /// عرض لحظة بالتوقيت السعودي — التحويل في saudi_time وحدها
  ///
  /// In ar, this message translates to:
  /// **'{date} الساعة {time}'**
  String dateTimeAt(DateTime date, DateTime time);
}

class _AppLocalizationsDelegate
    extends LocalizationsDelegate<AppLocalizations> {
  const _AppLocalizationsDelegate();

  @override
  Future<AppLocalizations> load(Locale locale) {
    return SynchronousFuture<AppLocalizations>(lookupAppLocalizations(locale));
  }

  @override
  bool isSupported(Locale locale) =>
      <String>['ar', 'en'].contains(locale.languageCode);

  @override
  bool shouldReload(_AppLocalizationsDelegate old) => false;
}

AppLocalizations lookupAppLocalizations(Locale locale) {
  // Lookup logic when only language code is specified.
  switch (locale.languageCode) {
    case 'ar':
      return AppLocalizationsAr();
    case 'en':
      return AppLocalizationsEn();
  }

  throw FlutterError(
    'AppLocalizations.delegate failed to load unsupported locale "$locale". This is likely '
    'an issue with the localizations generation tool. Please file an issue '
    'on GitHub with a reproducible sample app and the gen-l10n configuration '
    'that was used.',
  );
}
