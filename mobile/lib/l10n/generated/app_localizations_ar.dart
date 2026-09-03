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
  String offlineDataNotice(DateTime date, DateTime time) {
    final intl.DateFormat dateDateFormat = intl.DateFormat.yMd(localeName);
    final String dateString = dateDateFormat.format(date);
    final intl.DateFormat timeDateFormat = intl.DateFormat.Hm(localeName);
    final String timeString = timeDateFormat.format(time);

    return 'بيانات محفوظة — آخر تحديث $dateString الساعة $timeString';
  }
}
