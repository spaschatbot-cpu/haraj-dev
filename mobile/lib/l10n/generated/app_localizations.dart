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
