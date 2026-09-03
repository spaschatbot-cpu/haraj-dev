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
  String offlineDataNotice(DateTime date, DateTime time) {
    final intl.DateFormat dateDateFormat = intl.DateFormat.yMd(localeName);
    final String dateString = dateDateFormat.format(date);
    final intl.DateFormat timeDateFormat = intl.DateFormat.Hm(localeName);
    final String timeString = timeDateFormat.format(time);

    return 'Saved data — last updated $dateString at $timeString';
  }

  @override
  String get bidPanelTitle => 'Bidding';

  @override
  String get bidAmountLabel => 'Bid amount';

  @override
  String get bidAmountMissing => 'Enter a bid amount.';

  @override
  String get bidSubmit => 'Bid';

  @override
  String get bidPlaced => 'Your bid was recorded.';

  @override
  String get bidServerDecides =>
      'A bid holds a deposit for the auction. The server decides eligibility and the minimum.';

  @override
  String get bidLowerConfirmTitle => 'Confirm lowering your bid';

  @override
  String get bidLowerStandingLabel => 'Your standing bid';

  @override
  String get bidLowerRequestedLabel => 'The new amount';

  @override
  String get bidLowerConfirmCheckbox => 'Yes, I want to lower my bid.';

  @override
  String get bidLowerConfirmAction => 'Confirm the lower bid';

  @override
  String get cancel => 'Cancel';

  @override
  String get myBidsTitle => 'My bids';

  @override
  String get myBidsEmpty => 'You have no bids yet.';

  @override
  String bidPlacedAt(DateTime date, DateTime time) {
    final intl.DateFormat dateDateFormat = intl.DateFormat.yMd(localeName);
    final String dateString = dateDateFormat.format(date);
    final intl.DateFormat timeDateFormat = intl.DateFormat.Hm(localeName);
    final String timeString = timeDateFormat.format(time);

    return 'On $dateString at $timeString';
  }

  @override
  String get bidWithdrawAction => 'Withdraw bid';

  @override
  String get bidWithdrawConfirmTitle => 'Confirm withdrawing your bid';

  @override
  String bidWithdrawConfirmBody(String vehicle) {
    return 'Your bid on $vehicle will be withdrawn. A withdrawal is marked, never deleted.';
  }

  @override
  String get bidWithdrawn => 'Your bid was withdrawn.';

  @override
  String get liveConnecting => 'Connecting…';

  @override
  String get liveConnected => 'Live';

  @override
  String get liveLost => 'Connection lost — the amounts below are stale';

  @override
  String get liveStandingBid => 'Your standing bid';

  @override
  String get liveNoStandingBid => 'You have no standing bid on this vehicle.';
}
