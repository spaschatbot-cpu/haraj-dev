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
  String offlineDataNotice(DateTime date, DateTime time) {
    final intl.DateFormat dateDateFormat = intl.DateFormat.yMd(localeName);
    final String dateString = dateDateFormat.format(date);
    final intl.DateFormat timeDateFormat = intl.DateFormat.Hm(localeName);
    final String timeString = timeDateFormat.format(time);

    return 'بيانات محفوظة — آخر تحديث $dateString الساعة $timeString';
  }
}
