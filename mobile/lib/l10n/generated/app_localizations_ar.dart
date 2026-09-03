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
}
