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
  String get walletTitle => 'My wallet';

  @override
  String walletAsOf(DateTime date, DateTime time) {
    final intl.DateFormat dateDateFormat = intl.DateFormat.yMd(localeName);
    final String dateString = dateDateFormat.format(date);
    final intl.DateFormat timeDateFormat = intl.DateFormat.Hm(localeName);
    final String timeString = timeDateFormat.format(time);

    return 'Per the ledger at $dateString $timeString';
  }

  @override
  String get walletEmpty => 'No balances on your account yet.';

  @override
  String get walletHoldsTitle => 'Why this money is held';

  @override
  String get walletOpenStatement => 'The entries behind this number';

  @override
  String get transactionsTitle => 'Statement';

  @override
  String get transactionsAll => 'Every movement on your account, newest first.';

  @override
  String get transactionsFiltered => 'Filtered to a single bucket.';

  @override
  String get transactionsShowAll => 'Show every movement';

  @override
  String get transactionsEmpty => 'No movements.';

  @override
  String transactionsTotal(int count) {
    return '$count movements';
  }

  @override
  String get transactionsLoadMore => 'Load more';

  @override
  String get movementIncoming => 'In';

  @override
  String get movementOutgoing => 'Out';

  @override
  String movementReference(String reference) {
    return 'Reference $reference';
  }

  @override
  String dateTimeAt(DateTime date, DateTime time) {
    final intl.DateFormat dateDateFormat = intl.DateFormat.yMd(localeName);
    final String dateString = dateDateFormat.format(date);
    final intl.DateFormat timeDateFormat = intl.DateFormat.Hm(localeName);
    final String timeString = timeDateFormat.format(time);

    return '$dateString at $timeString';
  }

  @override
  String offlineDataNotice(DateTime date, DateTime time) {
    final intl.DateFormat dateDateFormat = intl.DateFormat.yMd(localeName);
    final String dateString = dateDateFormat.format(date);
    final intl.DateFormat timeDateFormat = intl.DateFormat.Hm(localeName);
    final String timeString = timeDateFormat.format(time);

    return 'Saved data — last updated $dateString at $timeString';
  }
}
