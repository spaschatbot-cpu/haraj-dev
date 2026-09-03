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
}
