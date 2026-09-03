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

  /// علامة «آخر تحديث» فوق أي شاشة تعرض بيانات من الكاش — معيار H5
  ///
  /// In ar, this message translates to:
  /// **'بيانات محفوظة — آخر تحديث {date} الساعة {time}'**
  String offlineDataNotice(DateTime date, DateTime time);
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
