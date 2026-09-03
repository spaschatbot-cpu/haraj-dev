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

  /// علامة «آخر تحديث» فوق أي شاشة تعرض بيانات من الكاش — معيار H5
  ///
  /// In ar, this message translates to:
  /// **'بيانات محفوظة — آخر تحديث {date} الساعة {time}'**
  String offlineDataNotice(DateTime date, DateTime time);

  /// عنوان صندوق المزايدة في صفحة المركبة
  ///
  /// In ar, this message translates to:
  /// **'المزايدة'**
  String get bidPanelTitle;

  /// No description provided for @bidAmountLabel.
  ///
  /// In ar, this message translates to:
  /// **'مبلغ المزايدة'**
  String get bidAmountLabel;

  /// حقل فارغ — نقص في النموذج لا رفض من الخادم، فالنصّ محلي
  ///
  /// In ar, this message translates to:
  /// **'اكتب مبلغ المزايدة.'**
  String get bidAmountMissing;

  /// No description provided for @bidSubmit.
  ///
  /// In ar, this message translates to:
  /// **'زايد'**
  String get bidSubmit;

  /// نفس جملة الويب حرفياً — القناتان تقولان الشيء نفسه
  ///
  /// In ar, this message translates to:
  /// **'سُجّلت مزايدتك.'**
  String get bidPlaced;

  /// يشرح للعميل لماذا يظهر الصندوق قبل أن يُعرف إن كان مؤهلاً
  ///
  /// In ar, this message translates to:
  /// **'المزايدة تحجز تأميناً على المزاد. الخادم يقرّر الأهلية والحد الأدنى.'**
  String get bidServerDecides;

  /// No description provided for @bidLowerConfirmTitle.
  ///
  /// In ar, this message translates to:
  /// **'تأكيد خفض المزايدة'**
  String get bidLowerConfirmTitle;

  /// No description provided for @bidLowerStandingLabel.
  ///
  /// In ar, this message translates to:
  /// **'مزايدتك القائمة'**
  String get bidLowerStandingLabel;

  /// No description provided for @bidLowerRequestedLabel.
  ///
  /// In ar, this message translates to:
  /// **'المبلغ الجديد'**
  String get bidLowerRequestedLabel;

  /// غير مؤشَّر عند الفتح — المؤشَّر سلفاً ليس تأكيداً
  ///
  /// In ar, this message translates to:
  /// **'نعم، أريد خفض مزايدتي.'**
  String get bidLowerConfirmCheckbox;

  /// No description provided for @bidLowerConfirmAction.
  ///
  /// In ar, this message translates to:
  /// **'تأكيد الخفض'**
  String get bidLowerConfirmAction;

  /// No description provided for @cancel.
  ///
  /// In ar, this message translates to:
  /// **'إلغاء'**
  String get cancel;

  /// No description provided for @myBidsTitle.
  ///
  /// In ar, this message translates to:
  /// **'مزايداتي'**
  String get myBidsTitle;

  /// حالة فارغة صريحة — لا شاشة بيضاء
  ///
  /// In ar, this message translates to:
  /// **'لا مزايدات لك بعد.'**
  String get myBidsEmpty;

  /// لحظة المزايدة بالتوقيت السعودي
  ///
  /// In ar, this message translates to:
  /// **'بتاريخ {date} الساعة {time}'**
  String bidPlacedAt(DateTime date, DateTime time);

  /// No description provided for @bidWithdrawAction.
  ///
  /// In ar, this message translates to:
  /// **'سحب المزايدة'**
  String get bidWithdrawAction;

  /// No description provided for @bidWithdrawConfirmTitle.
  ///
  /// In ar, this message translates to:
  /// **'تأكيد سحب المزايدة'**
  String get bidWithdrawConfirmTitle;

  /// No description provided for @bidWithdrawConfirmBody.
  ///
  /// In ar, this message translates to:
  /// **'سيُسحب عرضك على {vehicle}. السحب يُعلَّم ولا يُحذف.'**
  String bidWithdrawConfirmBody(String vehicle);

  /// No description provided for @bidWithdrawn.
  ///
  /// In ar, this message translates to:
  /// **'سُحبت مزايدتك.'**
  String get bidWithdrawn;

  /// No description provided for @liveConnecting.
  ///
  /// In ar, this message translates to:
  /// **'جارٍ الاتصال…'**
  String get liveConnecting;

  /// No description provided for @liveConnected.
  ///
  /// In ar, this message translates to:
  /// **'التحديث حي'**
  String get liveConnected;

  /// نفس جملة الويب — رقم بائت يبدو حياً أسوأ من لا رقم
  ///
  /// In ar, this message translates to:
  /// **'انقطع الاتصال — الأرقام أدناه قديمة'**
  String get liveLost;

  /// No description provided for @liveStandingBid.
  ///
  /// In ar, this message translates to:
  /// **'مزايدتك القائمة'**
  String get liveStandingBid;

  /// No description provided for @liveNoStandingBid.
  ///
  /// In ar, this message translates to:
  /// **'لا مزايدة قائمة لك على هذه المركبة.'**
  String get liveNoStandingBid;
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
