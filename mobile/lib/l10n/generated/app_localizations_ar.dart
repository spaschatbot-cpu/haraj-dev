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
  String get homeTabUpcoming => 'قريباً';

  @override
  String get homeTabActive => 'نشط';

  @override
  String get homeTabEnded => 'منتهي';

  @override
  String homeTabWithCount(String label, int count) {
    return '$label ($count)';
  }

  @override
  String get homeEmptyUpcoming => 'لا مزاد قادم الآن.';

  @override
  String get homeEmptyActive => 'لا مزاد نشط الآن.';

  @override
  String get homeEmptyEnded => 'لا مزاد منتهٍ بعد.';

  @override
  String get vehicleAuctionEnded => 'انتهى المزاد';

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
  String get searchHint => 'ابحث عن سيارة';

  @override
  String get homeFilterAll => 'الكل';

  @override
  String get homeFilterPrice => 'السعر';

  @override
  String get homeFilterYearRange => 'من - إلى';

  @override
  String get homeFilterSoon => 'الترشيح لم يُفعَّل بعد.';

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
  String vehicleLotPosition(String lotNumber) {
    return 'الموقف $lotNumber';
  }

  @override
  String get vehicleBidAction => 'مزايدة';

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

  @override
  String get walletTitle => 'محفظتي';

  @override
  String walletAsOf(DateTime date, DateTime time) {
    final intl.DateFormat dateDateFormat = intl.DateFormat.yMd(localeName);
    final String dateString = dateDateFormat.format(date);
    final intl.DateFormat timeDateFormat = intl.DateFormat.Hm(localeName);
    final String timeString = timeDateFormat.format(time);

    return 'بحسب الدفتر في $dateString الساعة $timeString';
  }

  @override
  String get walletEmpty => 'لا أرصدة على حسابك بعد.';

  @override
  String get walletHoldsTitle => 'لماذا هذا المبلغ محجوز';

  @override
  String get walletOpenStatement => 'الحركات التي تفسّر هذا الرقم';

  @override
  String get topUpTitle => 'شحن التأمين بالبطاقة';

  @override
  String get topUpStart => 'ابدأ الشحن';

  @override
  String get topUpAmountFromServer =>
      'المبلغ يحدّده النظام. تُفتح لك صفحة الدفع في المتصفح، ثم نسأل الخادم عن النتيجة.';

  @override
  String get topUpWaiting => 'بانتظار تأكيد البوابة للخادم.';

  @override
  String get topUpCheckStatus => 'تحقّق من حالة الشحن';

  @override
  String get topUpStatusFromServer =>
      'الحالة مقروءة من سجلّ الخادم لا من رابط العودة، ورصيدك يتحرّك حين تؤكّد البوابة الدفع للخادم.';

  @override
  String get topUpGatewayNotOpened =>
      'تعذّر فتح صفحة الدفع. طلب الشحن محفوظ، وتقدر تفتحها من جديد.';

  @override
  String get topUpOpenGateway => 'افتح صفحة الدفع';

  @override
  String get transactionsTitle => 'كشف الحركات';

  @override
  String get transactionsAll => 'كل الحركات على حسابك، الأحدث أولاً.';

  @override
  String get transactionsFiltered => 'مرشَّح على دلو واحد.';

  @override
  String get transactionsShowAll => 'اعرض كل الحركات';

  @override
  String get transactionsEmpty => 'لا حركات.';

  @override
  String transactionsTotal(int count) {
    return '$count حركة';
  }

  @override
  String get transactionsLoadMore => 'تحميل المزيد';

  @override
  String get movementIncoming => 'وارد';

  @override
  String get movementOutgoing => 'صادر';

  @override
  String movementReference(String reference) {
    return 'المرجع $reference';
  }

  @override
  String dateTimeAt(DateTime date, DateTime time) {
    final intl.DateFormat dateDateFormat = intl.DateFormat.yMd(localeName);
    final String dateString = dateDateFormat.format(date);
    final intl.DateFormat timeDateFormat = intl.DateFormat.Hm(localeName);
    final String timeString = timeDateFormat.format(time);

    return '$dateString الساعة $timeString';
  }

  @override
  String get bidPanelTitle => 'المزايدة';

  @override
  String get bidAmountLabel => 'مبلغ المزايدة';

  @override
  String get bidAmountMissing => 'اكتب مبلغ المزايدة.';

  @override
  String get bidSubmit => 'زايد';

  @override
  String get bidPlaced => 'سُجّلت مزايدتك.';

  @override
  String get bidServerDecides =>
      'المزايدة تحجز تأميناً على المزاد. الخادم يقرّر الأهلية والحد الأدنى.';

  @override
  String get bidLowerConfirmTitle => 'تأكيد خفض المزايدة';

  @override
  String get bidLowerStandingLabel => 'مزايدتك القائمة';

  @override
  String get bidLowerRequestedLabel => 'المبلغ الجديد';

  @override
  String get bidLowerConfirmCheckbox => 'نعم، أريد خفض مزايدتي.';

  @override
  String get bidLowerConfirmAction => 'تأكيد الخفض';

  @override
  String get cancel => 'إلغاء';

  @override
  String get myBidsTitle => 'مزايداتي';

  @override
  String get myBidsEmpty => 'لا مزايدات لك بعد.';

  @override
  String bidPlacedAt(DateTime date, DateTime time) {
    final intl.DateFormat dateDateFormat = intl.DateFormat.yMd(localeName);
    final String dateString = dateDateFormat.format(date);
    final intl.DateFormat timeDateFormat = intl.DateFormat.Hm(localeName);
    final String timeString = timeDateFormat.format(time);

    return 'بتاريخ $dateString الساعة $timeString';
  }

  @override
  String get bidWithdrawAction => 'سحب المزايدة';

  @override
  String get bidWithdrawConfirmTitle => 'تأكيد سحب المزايدة';

  @override
  String bidWithdrawConfirmBody(String vehicle) {
    return 'سيُسحب عرضك على $vehicle. السحب يُعلَّم ولا يُحذف.';
  }

  @override
  String get bidWithdrawn => 'سُحبت مزايدتك.';

  @override
  String get liveConnecting => 'جارٍ الاتصال…';

  @override
  String get liveConnected => 'التحديث حي';

  @override
  String get liveLost => 'انقطع الاتصال — الأرقام أدناه قديمة';

  @override
  String get liveStandingBid => 'مزايدتك القائمة';

  @override
  String get liveNoStandingBid => 'لا مزايدة قائمة لك على هذه المركبة.';

  @override
  String get vehicleSpecMake => 'الماركة';

  @override
  String get vehicleSpecModel => 'الطراز';

  @override
  String get vehicleSpecYear => 'سنة الصنع';

  @override
  String get vehicleSpecColour => 'اللون';

  @override
  String get vehicleSpecCondition => 'الحالة';

  @override
  String get vehicleSpecOdometer => 'الممشى (كم)';

  @override
  String get vehicleSpecLocation => 'الموقع';

  @override
  String get vehicleAdminFee => 'الرسوم الإدارية';

  @override
  String get vehicleAdminFeeWithVat => 'الرسوم + الضريبة';

  @override
  String get bidStateStanding => 'قائمة';

  @override
  String get bidStateSuperseded => 'تجاوزتها مزايدةٌ أحدث لك';

  @override
  String get bidStateWithdrawn => 'مسحوبة';

  @override
  String get bidStateUnknown => '—';

  @override
  String get auctionVehiclesNotCounted => 'لم تُعدّ';

  @override
  String walletHoldSince(DateTime date) {
    final intl.DateFormat dateDateFormat = intl.DateFormat.yMd(localeName);
    final String dateString = dateDateFormat.format(date);

    return 'محجوز منذ $dateString';
  }

  @override
  String get navHome => 'الرئيسية';

  @override
  String get navActivity => 'مشاركاتي';

  @override
  String get navFavourites => 'المفضلة';

  @override
  String get navWallet => 'المحفظة';

  @override
  String get navAccount => 'حسابي';

  @override
  String get favouritesTitle => 'المفضلة';

  @override
  String get favouritesEmpty =>
      'لا مركبات في مفضلتك بعد. افتح مركبة واضغط القلب لتحفظها هنا.';

  @override
  String get favouriteAdd => 'أضف إلى المفضلة';

  @override
  String get favouriteRemove => 'أزل من المفضلة';

  @override
  String get favouriteAdded => 'أُضيفت إلى المفضلة';

  @override
  String get favouriteRemoved => 'أُزيلت من المفضلة';

  @override
  String get homeBrand => 'مزاد حراج واحد';

  @override
  String get homeTagline => 'بوابة مزادات حراج الحصرية';

  @override
  String get homeSubtagline =>
      'اكتشف فرصتك لامتلاك أفضل المركبات بأفضل الأسعار';

  @override
  String get homeNotifications => 'الإشعارات';

  @override
  String get homeAccountAction => 'حسابي';

  @override
  String get heroHeadlineLead => 'اكتشف أفضل العروض في';

  @override
  String get heroHeadline => 'بوابة مزادات حراج';

  @override
  String get heroHeadlineAccent => 'العصرية';

  @override
  String get heroChipCars => 'سيارات مميزة';

  @override
  String get heroChipTrusted => 'مزادات موثوقة';

  @override
  String get heroChipOpportunities => 'فرص استثنائية';

  @override
  String get homeSortAndFilter => 'الفرز والتصفية';

  @override
  String get filterPhase => 'طور المزاد';

  @override
  String get vehicleDetailsAction => 'تفاصيل المزاد';

  @override
  String vehicleOdometerShort(int km) {
    final intl.NumberFormat kmNumberFormat = intl.NumberFormat.decimalPattern(
      localeName,
    );
    final String kmString = kmNumberFormat.format(km);

    return '$kmString كم';
  }

  @override
  String get favouriteFailed => 'تعذّر تحديث المفضلة';

  @override
  String get vehicleSpecCity => 'المدينة';

  @override
  String get vehicleBidDetails => 'تفاصيل المزايدة';

  @override
  String get vehicleEnterAuction => 'دخول المزاد';

  @override
  String get vehicleSpecsAction => 'مواصفات المركبة';

  @override
  String get vehiclePrice => 'السعر';

  @override
  String get vehiclePriceWithVat => 'السعر + الضريبة';

  @override
  String get vehicleShareCopied => 'نُسخ رابط المركبة';

  @override
  String get signInDismiss => 'إغلاق';

  @override
  String get bidPlacedTitle => 'تم تسجيل مزايدتك بنجاح';

  @override
  String get walletTotal => 'إجمالي الرصيد';

  @override
  String get walletAvailable => 'المتاح';

  @override
  String get walletHeldForAuctions => 'محجوز للمزادات';

  @override
  String get walletLockedForDues => 'مقفل للمستحقات';

  @override
  String walletEntryCount(int count) {
    return '$count قيداً';
  }

  @override
  String get walletStatementAction => 'كشف الحساب';

  @override
  String get walletRefundRequests => 'مجموع طلبات الاسترداد';

  @override
  String get walletRefundedAmount => 'المبلغ المسترد';

  @override
  String get walletTransfers => 'حوالاتي';

  @override
  String get walletOpenTransfers => 'اضغط للعرض';

  @override
  String get walletInsuranceStatus => 'حالة التأمين';

  @override
  String get walletInsuranceInactive => 'غير مفعّل — يجب شحن التأمين أولاً';

  @override
  String get walletInsuranceActive => 'مفعّل — يمكنك المشاركة في المزادات';

  @override
  String get walletSubscriptionStatus => 'حالة الاشتراك';

  @override
  String get walletSubscriptionInactive => 'غير نشط';

  @override
  String get walletSubscriptionActive => 'نشط';

  @override
  String get walletSubscriptionNote =>
      'للمشاركة في المزادات، يجب الاشتراك بمبلغ التأمين كاملاً (ثابت — لا يقبل مبالغ جزئية).';

  @override
  String get walletSubscribeAction => 'اشتراك التأمين';

  @override
  String get walletSubscriptionsLog => 'سجل الاشتراكات';

  @override
  String get walletNoSubscriptions => 'لم تقم بأي اشتراك بعد.';

  @override
  String get walletInsuranceLog => 'سجل عمليات التأمين';

  @override
  String get walletNoOperations => 'لا توجد عمليات بعد';

  @override
  String get walletCompleteDataTitle => 'أكمل بياناتك أولاً';

  @override
  String get walletCompleteDataNote =>
      'لإتمام الاشتراك أو الدفع لازم تكمّل البيانات الناقصة وتحفظها.';

  @override
  String get walletAccountType => 'نوع الحساب';

  @override
  String get walletFullName => 'الاسم الكامل';

  @override
  String get walletPhone => 'رقم الجوال';

  @override
  String get walletNationalId => 'رقم الهوية';

  @override
  String get walletSaveAndContinue => 'حفظ البيانات والمتابعة';

  @override
  String get walletChoosePayment => 'اختر طريقة الدفع';

  @override
  String get walletTopUpTitle => 'شحن المحفظة';

  @override
  String get walletBankTransfer => 'تحويل بنكي';

  @override
  String get walletBankTransferNote => 'حوّل للحساب البنكي وارفع الإيصال';

  @override
  String get walletCardMada => 'بطاقة بنكية / مدى';

  @override
  String get walletCardMadaNote => 'ادفع ببطاقتك أو مدى — دفع فوري';

  @override
  String get walletApplePay => 'Apple Pay';

  @override
  String get walletApplePayNote => 'دفع سريع وآمن عبر Apple Pay';

  @override
  String get walletMethodUnavailable => 'غير متاح في هذا الإصدار';

  @override
  String get walletMethodSoon => 'قريباً — هذه الطريقة لم تُفعَّل بعد';

  @override
  String get profileAccountIndividual => 'حساب فرد';

  @override
  String get profileAccountCompany => 'حساب شركة';

  @override
  String get profileIdVerified => 'هوية موثّقة';

  @override
  String get accountMenuSection => 'خدماتي';

  @override
  String get accountMenuWallet => 'محفظتي';

  @override
  String get accountMenuRefundDeposit => 'طلب استرداد مبلغ التأمين';

  @override
  String get accountMenuPurchases => 'مشترياتي';

  @override
  String get accountMenuOrders => 'الطلبات';

  @override
  String get accountMenuEditRequest => 'طلب تعديل البيانات';

  @override
  String get accountMenuRegistrationGuide => 'شرح التسجيل';

  @override
  String get accountMenuWalletGuide => 'شرح شحن المحفظة';

  @override
  String get accountMenuAbout => 'من نحن';

  @override
  String get accountMenuFaq => 'الأسئلة الشائعة';

  @override
  String get accountMenuTerms => 'الشروط والأحكام';

  @override
  String get accountMenuSupport => 'تواصل مع الدعم';

  @override
  String get accountPageComingSoon => 'المحتوى سيُضاف قريباً.';

  @override
  String get accountLanguageSection => 'اللغة';

  @override
  String get accountLanguageSoon => 'هذه اللغة لم تُفعَّل بعد';

  @override
  String get refundHeaderTitle => 'طلب استرداد';

  @override
  String get refundHeaderSubtitle =>
      'استرداد مبلغ التأمين — يُراجَع الطلب من الإدارة.';

  @override
  String get refundInsuranceLabel => 'قيمة التأمين';

  @override
  String get refundNoInsurance =>
      'لا يوجد تأمين قابل للاسترداد حالياً — الاسترداد متاح بعد دفع التأمين كاملاً.';

  @override
  String get refundFormSection => 'بيانات الطلب';

  @override
  String get refundAmountLabel => 'المبلغ المسترد';

  @override
  String get refundIbanLabel => 'رقم الآيبان';

  @override
  String get refundIbanHint => 'يجب أن يتكوّن من ٢٤ خانة (أحرف كبيرة وأرقام).';

  @override
  String get refundIbanImageLabel => 'صورة الآيبان';

  @override
  String get refundChooseFile => 'اختيار ملف';

  @override
  String get refundNoFile => 'لم يُختَر أي ملف';

  @override
  String get refundNotesLabel => 'ملاحظات';

  @override
  String get refundSubmit => 'إرسال طلب برصيد المحفظة';

  @override
  String get refundSubmitSoon => 'الإرسال لم يُفعَّل بعد.';

  @override
  String get refundPreviousSection => 'الطلبات السابقة';

  @override
  String get refundPreviousEmpty => 'لا توجد طلبات سابقة.';

  @override
  String get purchasesEmptyTitle => 'لا توجد مشتريات حتى الآن';

  @override
  String get purchasesEmptyBody =>
      'لم تقم بإتمام أي عمليات شراء حتى الآن. استكشف المزادات الحالية وابدأ المزايدة الآن!';

  @override
  String get purchasesBrowse => 'تصفح المزادات';

  @override
  String get purchasesSelectedCount => 'عدد المختارة';

  @override
  String get purchasesTotalDue => 'الإجمالي المستحق';

  @override
  String get purchasesPayAll => 'دفع كامل المختارة';

  @override
  String get purchasesClear => 'مسح التحديد';

  @override
  String get purchasesPaySoon => 'الدفع لم يُفعَّل بعد.';

  @override
  String purchasesLotNumber(String number) {
    return 'رقم اللوت $number';
  }

  @override
  String get ordersSoon => 'قريباً';

  @override
  String get ordersHandover => 'طلب تنازل';

  @override
  String get ordersTransfer => 'طلب نقل ملكية';

  @override
  String get ordersDelivery => 'طلب توصيل';

  @override
  String get ordersReceive => 'طلب استلام';

  @override
  String get supportTitle => 'الدعم الفني';

  @override
  String get supportSubtitle => 'اختر الطريقة المناسبة للتواصل مع فريقنا';

  @override
  String get supportWhatsApp => 'واتساب مباشر';

  @override
  String get supportNotConfigured => 'لم يُضف رقم الدعم بعد.';

  @override
  String get supportInfo =>
      'تواصل مع فريق الدعم عبر واتساب وسنردّ عليك في أقرب وقت.';

  @override
  String get editRequestInfo =>
      'تعديل البيانات غير متاح مباشرة من الحساب. إذا كنت تريد تعديل بياناتك، افتح الشات الداخلي أو تواصل عبر واتساب وسيقوم فريق الدعم بتنفيذ الطلب لك.';

  @override
  String get guideHeaderTitle => 'شرح التسجيل في موقع المزاد';

  @override
  String get guideHeaderSubtitle => 'اتبع الخطوات البسيطة لبدء المزايدة';

  @override
  String get guideStep1Title => 'الدخول إلى صفحة التسجيل';

  @override
  String get guideStep1Body =>
      'من الصفحة الرئيسية، اضغط على زر «تسجيل» أو «إنشاء حساب جديد».';

  @override
  String get guideStep2Title => 'إدخال البيانات الشخصية';

  @override
  String get guideStep2Body => 'قم بكتابة رقم الجوال.';

  @override
  String get guideStep3Title => 'تأكيد رقم الجوال';

  @override
  String get guideStep3Body =>
      'سيتم إرسال كود تحقق إلى رقم جوالك، أدخله لتفعيل الحساب.';

  @override
  String get guideStep4Title => 'تفعيل الحساب والمشاركة';

  @override
  String get guideStep4Body =>
      'بعد التأكيد، يمكنك الدخول، والاشتراك في باقة، والمشاركة في المزادات.';

  @override
  String get guideVideoSoon => 'الفيديو سيُضاف قريباً.';

  @override
  String get guideSupportHint =>
      'إذا واجهت أي مشكلة في التسجيل، تواصل معنا عبر واتساب الدعم أو نموذج المراسلة.';

  @override
  String get guideContactHint =>
      'في حال وجود أي استفسار، تواصل عبر واتساب الدعم أو نموذج المراسلة.';

  @override
  String get walletGuideHeaderTitle => 'شرح شحن المحفظة للمزاد';

  @override
  String get walletGuideHeaderSubtitle =>
      'تعرّف على كيفية إدارة محفظتك المالية';

  @override
  String get walletGuideStep1Title => 'الدخول إلى المحفظة';

  @override
  String get walletGuideStep1Body =>
      'بعد تسجيل الدخول، من القائمة الرئيسية اختر «حسابي»، ثم «المحفظة» لعرض الرصيد وزر الشحن.';

  @override
  String get walletGuideStep2Title => 'اختيار طريقة الدفع';

  @override
  String get walletGuideStep2Body =>
      'يمكنك الشحن عبر التحويل البنكي أو الدفع الإلكتروني (بطاقة / Apple Pay).';

  @override
  String get walletGuideStep3Title => 'تحويل المبلغ';

  @override
  String get walletGuideStep3Body =>
      'حوّل المبلغ المطلوب إلى الحساب البنكي الظاهر في صفحة الشحن.';

  @override
  String get walletGuideStep4Title => 'رفع صورة التحويل';

  @override
  String get walletGuideStep4Body =>
      'بعد التحويل، ارفع صورة الإيصال من خلال النموذج.';

  @override
  String get walletGuideStep5Title => 'انتظار الموافقة';

  @override
  String get walletGuideStep5Body =>
      'يتم مراجعة الطلب وتأكيد شحن المحفظة خلال وقت قصير.';
}
