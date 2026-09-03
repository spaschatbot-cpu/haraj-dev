// ignore: unused_import
import 'package:intl/intl.dart' as intl;
import 'app_localizations.dart';

// ignore_for_file: type=lint

/// The translations for English (`en`).
class AppLocalizationsEn extends AppLocalizations {
  AppLocalizationsEn([String locale = 'en']) : super(locale);

  @override
  String get appTitle => 'Haraj Wahed';

  @override
  String get seedTitle => 'App seed';

  @override
  String get seedBody =>
      'The foundation is in place: Arabic and direction, the generated client, local storage, and error handling. Screens start once the API schema is frozen.';

  @override
  String environmentBanner(String environment) {
    return '$environment build';
  }

  @override
  String get environmentDevelopment => 'Development';

  @override
  String get environmentStaging => 'Staging';

  @override
  String get retry => 'Retry';

  @override
  String get errorOffline => 'No internet connection.';

  @override
  String get errorTimeout => 'Could not reach the server. Please try again.';

  @override
  String get errorMalformedResponse =>
      'The server returned a response we could not read.';

  @override
  String get errorUnexpected => 'An unexpected error occurred in the app.';

  @override
  String get myActivityTitle => 'My account';

  @override
  String get tabParticipations => 'My auctions';

  @override
  String get tabPurchases => 'My purchases';

  @override
  String get tabInvoices => 'My invoices';

  @override
  String get emptyParticipations => 'You have not entered any auction yet.';

  @override
  String get emptyPurchases => 'No vehicle has been awarded to you yet.';

  @override
  String get emptyInvoices => 'There are no invoices on your account.';

  @override
  String participationBidsCount(int count) {
    return 'My bids: $count';
  }

  @override
  String participationEndsAt(DateTime date, DateTime time) {
    final intl.DateFormat dateDateFormat = intl.DateFormat.yMd(localeName);
    final String dateString = dateDateFormat.format(date);
    final intl.DateFormat timeDateFormat = intl.DateFormat.Hm(localeName);
    final String timeString = timeDateFormat.format(time);

    return 'Ends $dateString at $timeString';
  }

  @override
  String get insuranceInThisAuction => 'My insurance in this auction';

  @override
  String purchaseLotNumber(String lot) {
    return 'Lot $lot';
  }

  @override
  String purchaseAwardedAt(DateTime date) {
    final intl.DateFormat dateDateFormat = intl.DateFormat.yMd(localeName);
    final String dateString = dateDateFormat.format(date);

    return 'Awarded to you $dateString';
  }

  @override
  String get purchaseNoInvoiceYet =>
      'No invoice has been issued for this vehicle yet.';

  @override
  String invoiceNumber(String number) {
    return 'Invoice $number';
  }

  @override
  String invoiceIssuedAt(DateTime date) {
    final intl.DateFormat dateDateFormat = intl.DateFormat.yMd(localeName);
    final String dateString = dateDateFormat.format(date);

    return 'Issued $dateString';
  }

  @override
  String get invoiceTotal => 'Total';

  @override
  String get invoicePaid => 'Paid';

  @override
  String get invoiceDue => 'Outstanding';

  @override
  String get invoiceInsuranceEffect => 'What it means for my insurance';

  @override
  String offlineDataNotice(DateTime date, DateTime time) {
    final intl.DateFormat dateDateFormat = intl.DateFormat.yMd(localeName);
    final String dateString = dateDateFormat.format(date);
    final intl.DateFormat timeDateFormat = intl.DateFormat.Hm(localeName);
    final String timeString = timeDateFormat.format(time);

    return 'Saved data — last updated $dateString at $timeString';
  }
}
