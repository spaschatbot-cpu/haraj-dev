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
  String get environmentProduction => 'Production';

  @override
  String environmentStampedMessage(String environment, String message) {
    return '[$environment] $message';
  }

  @override
  String get pushOpen => 'Open';

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
  String get signInTitle => 'Sign in or register';

  @override
  String get signInIntro =>
      'Enter your mobile number and we will send you a verification code.';

  @override
  String get signInPhoneLabel => 'Mobile number';

  @override
  String get signInPhoneHint => '9665xxxxxxxx';

  @override
  String get signInSendCode => 'Send verification code';

  @override
  String get verifyTitle => 'Verification code';

  @override
  String verifySentTo(String phone) {
    return 'We sent a code to $phone';
  }

  @override
  String get verifyCodeLabel => 'Verification code';

  @override
  String get verifySubmit => 'Confirm and sign in';

  @override
  String get verifyFullNameLabel => 'Full name';

  @override
  String get verifyResend => 'Send the code again';

  @override
  String get verifyChangePhone => 'Edit the number';

  @override
  String verifyExpiresAt(DateTime time) {
    final intl.DateFormat timeDateFormat = intl.DateFormat.Hm(localeName);
    final String timeString = timeDateFormat.format(time);

    return 'The code expires at $timeString';
  }

  @override
  String waitSeconds(int seconds) {
    return 'in ${seconds}s';
  }

  @override
  String get profileTitle => 'My profile';

  @override
  String get profileFullName => 'Name';

  @override
  String get profileEmail => 'Email';

  @override
  String get profilePhone => 'Mobile number';

  @override
  String get profileAccountType => 'Account type';

  @override
  String get profileNationalId => 'National ID';

  @override
  String get profileNationalIdMissing => 'Not entered yet';

  @override
  String get profileNationalIdSave => 'Save national ID';

  @override
  String get profileSave => 'Save';

  @override
  String get profileSaved => 'Saved';

  @override
  String get profileCompanySection => 'Company details and national address';

  @override
  String get profileCompanyComplete => 'Complete';

  @override
  String get profileCompanyIncomplete => 'Incomplete';

  @override
  String get profileCompanyMissing => 'No company profile';

  @override
  String get profileChangePhone => 'Change mobile number';

  @override
  String get profileSignOut => 'Sign out';

  @override
  String get companyTitle => 'Company profile';

  @override
  String get companyCreateHint =>
      'This account has no company profile. Fill the fields to create one.';

  @override
  String get companyName => 'Company name';

  @override
  String get companyRepresentative => 'Authorised representative';

  @override
  String get companyRegister => 'Commercial register';

  @override
  String get companyVatNumber => 'VAT number';

  @override
  String get companyNationalAddress => 'National address';

  @override
  String get companyBuildingNumber => 'Building number';

  @override
  String get companyStreet => 'Street';

  @override
  String get companyDistrict => 'District';

  @override
  String get companyCity => 'City';

  @override
  String get companyPostalCode => 'Postal code';

  @override
  String get companySave => 'Save company details';

  @override
  String get changePhoneTitle => 'Change mobile number';

  @override
  String get changePhoneIntro =>
      'We send one code to your current number and one to the new number. The change needs both.';

  @override
  String get changePhoneNewLabel => 'New number';

  @override
  String get changePhoneSendCodes => 'Send both codes';

  @override
  String changePhoneSentNotice(String phone) {
    return 'We sent a code to your current number and a code to $phone.';
  }

  @override
  String get changePhoneCurrentCode => 'Code sent to your current number';

  @override
  String get changePhoneNewCode => 'Code sent to the new number';

  @override
  String get changePhoneConfirm => 'Confirm the change';

  @override
  String get changePhoneDone =>
      'Your number changed and every open session ended. Sign in with the new number.';

  @override
  String get sessionExpiredNotice =>
      'Your session ended. Please sign in again.';

  @override
  String get homeTitle => 'Auctions';

  @override
  String get homeTabUpcoming => 'Upcoming';

  @override
  String get homeTabActive => 'Live';

  @override
  String get homeTabEnded => 'Ended';

  @override
  String homeTabWithCount(String label, int count) {
    return '$label ($count)';
  }

  @override
  String get homeEmptyUpcoming => 'No upcoming auction right now.';

  @override
  String get homeEmptyActive => 'No live auction right now.';

  @override
  String get homeEmptyEnded => 'No ended auction yet.';

  @override
  String get vehicleAuctionEnded => 'Auction ended';

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
  String get topUpTitle => 'Top up by card';

  @override
  String get topUpStart => 'Start the top-up';

  @override
  String get topUpAmountFromServer =>
      'The system sets the amount. The payment page opens in your browser, then we ask the server what happened.';

  @override
  String get topUpWaiting =>
      'Waiting for the gateway to confirm to the server.';

  @override
  String get topUpCheckStatus => 'Check the top-up status';

  @override
  String get topUpStatusFromServer =>
      'The status is read from the server\'s own record, not from the return link, and your balance moves when the gateway confirms the payment to the server.';

  @override
  String get topUpGatewayNotOpened =>
      'The payment page could not be opened. Your top-up request is saved and you can open it again.';

  @override
  String get topUpOpenGateway => 'Open the payment page';

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
