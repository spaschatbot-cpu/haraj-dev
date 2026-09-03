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
  String get homeTitle => 'Auctions';

  @override
  String get homeRunningSection => 'Live auctions';

  @override
  String get homeUpcomingSection => 'Upcoming auctions';

  @override
  String get homeEmpty => 'There are no live or upcoming auctions right now.';

  @override
  String auctionStartsAt(DateTime date, DateTime time) {
    final intl.DateFormat dateDateFormat = intl.DateFormat.yMd(localeName);
    final String dateString = dateDateFormat.format(date);
    final intl.DateFormat timeDateFormat = intl.DateFormat.Hm(localeName);
    final String timeString = timeDateFormat.format(time);

    return 'Starts $dateString at $timeString';
  }

  @override
  String auctionEndsAt(DateTime date, DateTime time) {
    final intl.DateFormat dateDateFormat = intl.DateFormat.yMd(localeName);
    final String dateString = dateDateFormat.format(date);
    final intl.DateFormat timeDateFormat = intl.DateFormat.Hm(localeName);
    final String timeString = timeDateFormat.format(time);

    return 'Ends $dateString at $timeString';
  }

  @override
  String auctionVehiclesCount(int count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$count vehicles',
      one: '1 vehicle',
      zero: 'No vehicles',
    );
    return '$_temp0';
  }

  @override
  String countdownToStart(String remaining) {
    return 'Starts in $remaining';
  }

  @override
  String countdownToEnd(String remaining) {
    return 'Ends in $remaining';
  }

  @override
  String countdownDaysHours(int days, int hours) {
    return '${days}d ${hours}h';
  }

  @override
  String countdownHoursMinutes(int hours, int minutes) {
    return '${hours}h ${minutes}m';
  }

  @override
  String countdownMinutes(int minutes) {
    return '${minutes}m';
  }

  @override
  String get countdownLessThanMinute => 'Less than a minute';

  @override
  String get countdownElapsed => 'Time is up';

  @override
  String get vehiclesTitle => 'Auction vehicles';

  @override
  String get vehiclesEmpty => 'No matching vehicles.';

  @override
  String vehiclesResultsCount(int count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$count results',
      one: '1 result',
      zero: 'No results',
    );
    return '$_temp0';
  }

  @override
  String get searchHint => 'Make, model or lot number';

  @override
  String get filterMake => 'Make';

  @override
  String get filterYearFrom => 'Year from';

  @override
  String get filterYearTo => 'Year to';

  @override
  String get filterApply => 'Apply filters';

  @override
  String get filterClear => 'Clear filters';

  @override
  String vehicleLot(String lotNumber) {
    return 'Lot $lotNumber';
  }

  @override
  String get vehicleReservePrice => 'Reserve price';

  @override
  String get vehicleReservePriceUnset => 'Not set';

  @override
  String vehicleBidsCount(int count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$count bids',
      one: '1 bid',
      zero: 'No bids',
    );
    return '$_temp0';
  }

  @override
  String get vehicleNoImage => 'No image';

  @override
  String get vehicleNoImages => 'This vehicle has no images.';

  @override
  String get vehicleImageFailed => 'Could not load the image';

  @override
  String vehicleImageCounter(int index, int total) {
    return '$index of $total';
  }

  @override
  String get vehicleSpecifications => 'Specifications';

  @override
  String get vehicleNoSpecifications =>
      'No specifications recorded for this vehicle.';

  @override
  String get vehicleBiddingOpen => 'Bidding is open';

  @override
  String get vehicleBiddingClosed => 'Bidding is closed';
}
