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
