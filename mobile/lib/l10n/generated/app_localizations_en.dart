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
  String countdownDaysOnly(int days) {
    String _temp0 = intl.Intl.pluralLogic(
      days,
      locale: localeName,
      other: '${days}d',
      one: '1d',
    );
    return '$_temp0';
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
  String get searchHint => 'Search for a car';

  @override
  String get homeFilterAll => 'All';

  @override
  String get homeFilterPrice => 'Price';

  @override
  String get homeFilterYearRange => 'From - To';

  @override
  String get homeFilterSoon => 'Filtering is not enabled yet.';

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
  String vehicleLotPosition(String lotNumber) {
    return 'Lot $lotNumber';
  }

  @override
  String get vehicleBidAction => 'Bid';

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
  String get emptyParticipations => 'You have no bids in the current auction.';

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

  @override
  String get vehicleSpecMake => 'Make';

  @override
  String get vehicleSpecModel => 'Model';

  @override
  String get vehicleSpecYear => 'Year';

  @override
  String get vehicleSpecColour => 'Colour';

  @override
  String get vehicleSpecCondition => 'Condition';

  @override
  String get vehicleSpecOdometer => 'Odometer (km)';

  @override
  String get vehicleSpecLocation => 'Location';

  @override
  String get vehicleAdminFee => 'Admin fee';

  @override
  String get vehicleAdminFeeWithVat => 'Admin fee + VAT';

  @override
  String get bidStateStanding => 'Standing';

  @override
  String get bidStateSuperseded => 'Superseded by your later bid';

  @override
  String get bidStateWithdrawn => 'Withdrawn';

  @override
  String get bidStateUnknown => '—';

  @override
  String get auctionVehiclesNotCounted => 'Not counted';

  @override
  String walletHoldSince(DateTime date) {
    final intl.DateFormat dateDateFormat = intl.DateFormat.yMd(localeName);
    final String dateString = dateDateFormat.format(date);

    return 'Held since $dateString';
  }

  @override
  String get navHome => 'Home';

  @override
  String get navActivity => 'Activity';

  @override
  String get navFavourites => 'Favourites';

  @override
  String get navWallet => 'Wallet';

  @override
  String get navAccount => 'Account';

  @override
  String get favouritesTitle => 'Favourites';

  @override
  String get favouritesEmpty =>
      'No saved vehicles yet. Open a vehicle and tap the heart to keep it here.';

  @override
  String get favouriteAdd => 'Add to favourites';

  @override
  String get favouriteRemove => 'Remove from favourites';

  @override
  String get favouriteAdded => 'Added to favourites';

  @override
  String get favouriteRemoved => 'Removed from favourites';

  @override
  String get homeBrand => 'Haraj Auction';

  @override
  String get homeTagline => 'Haraj\'s exclusive auctions gateway';

  @override
  String get homeSubtagline =>
      'Discover your chance to own the best vehicles at the best prices';

  @override
  String get homeNotifications => 'Notifications';

  @override
  String get homeAccountAction => 'My account';

  @override
  String get heroHeadlineLead => 'Discover the best deals in';

  @override
  String get heroHeadline => 'the modern Haraj';

  @override
  String get heroHeadlineAccent => 'auctions';

  @override
  String get heroChipCars => 'Premium cars';

  @override
  String get heroChipTrusted => 'Trusted auctions';

  @override
  String get heroChipOpportunities => 'Exceptional deals';

  @override
  String get homeSortAndFilter => 'Sort and filter';

  @override
  String get filterPhase => 'Auction phase';

  @override
  String get vehicleDetailsAction => 'Auction details';

  @override
  String vehicleOdometerShort(int km) {
    final intl.NumberFormat kmNumberFormat = intl.NumberFormat.decimalPattern(
      localeName,
    );
    final String kmString = kmNumberFormat.format(km);

    return '$kmString km';
  }

  @override
  String get favouriteFailed => 'Could not update favourites';

  @override
  String get vehicleSpecCity => 'City';

  @override
  String get vehicleBidDetails => 'Bidding details';

  @override
  String get vehicleEnterAuction => 'Enter the auction';

  @override
  String get vehicleSpecsAction => 'Vehicle specifications';

  @override
  String get vehiclePrice => 'Price';

  @override
  String get vehiclePriceWithVat => 'Price + VAT';

  @override
  String get vehicleShareCopied => 'Vehicle link copied';

  @override
  String get signInDismiss => 'Close';

  @override
  String get bidPlacedTitle => 'Your bid has been recorded';

  @override
  String get walletTotal => 'Total balance';

  @override
  String get walletAvailable => 'Available';

  @override
  String get walletHeldForAuctions => 'Held for auctions';

  @override
  String get walletLockedForDues => 'Locked for dues';

  @override
  String walletEntryCount(int count) {
    return '$count entries';
  }

  @override
  String get walletStatementAction => 'Statement';

  @override
  String get walletRefundRequests => 'Refund requests';

  @override
  String get walletRefundedAmount => 'Refunded';

  @override
  String get walletTransfers => 'My transfers';

  @override
  String get walletOpenTransfers => 'Tap to view';

  @override
  String get walletInsuranceStatus => 'Deposit status';

  @override
  String get walletInsuranceInactive => 'Inactive — top up the deposit first';

  @override
  String get walletInsuranceActive => 'Active — you can join auctions';

  @override
  String get walletSubscriptionStatus => 'Subscription';

  @override
  String get walletSubscriptionInactive => 'Inactive';

  @override
  String get walletSubscriptionActive => 'Active';

  @override
  String get walletSubscriptionNote =>
      'To join auctions you must subscribe with the full deposit (fixed — partial amounts are not accepted).';

  @override
  String get walletSubscribeAction => 'Subscribe the deposit';

  @override
  String get walletSubscriptionsLog => 'Subscriptions log';

  @override
  String get walletNoSubscriptions => 'You have not subscribed yet.';

  @override
  String get walletInsuranceLog => 'Deposit activity';

  @override
  String get walletNoOperations => 'No activity yet';

  @override
  String get walletCompleteDataTitle => 'Complete your details first';

  @override
  String get walletCompleteDataNote =>
      'To subscribe or pay you must complete and save the missing details.';

  @override
  String get walletAccountType => 'Account type';

  @override
  String get walletFullName => 'Full name';

  @override
  String get walletPhone => 'Phone';

  @override
  String get walletNationalId => 'National ID';

  @override
  String get walletSaveAndContinue => 'Save and continue';

  @override
  String get walletChoosePayment => 'Choose a payment method';

  @override
  String get walletTopUpTitle => 'Top up the wallet';

  @override
  String get walletBankTransfer => 'Bank transfer';

  @override
  String get walletBankTransferNote =>
      'Transfer to the bank account and upload the receipt';

  @override
  String get walletCardMada => 'Card / mada';

  @override
  String get walletCardMadaNote => 'Pay by card or mada — instant';

  @override
  String get walletApplePay => 'Apple Pay';

  @override
  String get walletApplePayNote => 'Fast and secure with Apple Pay';

  @override
  String get walletMethodUnavailable => 'Not available in this release';

  @override
  String get walletMethodSoon => 'Coming soon — this method is not enabled yet';

  @override
  String get profileAccountIndividual => 'Individual account';

  @override
  String get profileAccountCompany => 'Company account';

  @override
  String get profileIdVerified => 'Verified identity';

  @override
  String get accountMenuSection => 'My services';

  @override
  String get accountMenuWallet => 'My wallet';

  @override
  String get accountMenuRefundDeposit => 'Request deposit refund';

  @override
  String get accountMenuPurchases => 'My purchases';

  @override
  String get accountMenuOrders => 'Orders';

  @override
  String get accountMenuEditRequest => 'Request data change';

  @override
  String get accountMenuRegistrationGuide => 'Registration guide';

  @override
  String get accountMenuWalletGuide => 'Wallet top-up guide';

  @override
  String get accountMenuAbout => 'About us';

  @override
  String get accountMenuFaq => 'FAQ';

  @override
  String get accountMenuTerms => 'Terms and conditions';

  @override
  String get accountMenuSupport => 'Contact support';

  @override
  String get accountPageComingSoon => 'Content will be added soon.';

  @override
  String get accountLanguageSection => 'Language';

  @override
  String get accountLanguageSoon => 'This language is not enabled yet';

  @override
  String get refundHeaderTitle => 'Deposit refund';

  @override
  String get refundHeaderSubtitle =>
      'Refund of the insurance deposit — reviewed by admin.';

  @override
  String get refundInsuranceLabel => 'Insurance amount';

  @override
  String get refundNoInsurance =>
      'No refundable insurance right now — refund is available after the full insurance is paid.';

  @override
  String get refundFormSection => 'Request details';

  @override
  String get refundAmountLabel => 'Refund amount';

  @override
  String get refundIbanLabel => 'IBAN';

  @override
  String get refundIbanHint =>
      'Must be 24 characters (uppercase letters and digits).';

  @override
  String get refundIbanImageLabel => 'IBAN image';

  @override
  String get refundChooseFile => 'Choose file';

  @override
  String get refundNoFile => 'No file chosen';

  @override
  String get refundNotesLabel => 'Notes';

  @override
  String get refundSubmit => 'Submit to wallet balance';

  @override
  String get refundSubmitSoon => 'Submission is not enabled yet.';

  @override
  String get refundPreviousSection => 'Previous requests';

  @override
  String get refundPreviousEmpty => 'No previous requests.';

  @override
  String get purchasesEmptyTitle => 'No purchases yet';

  @override
  String get purchasesEmptyBody =>
      'You have not completed any purchases yet. Explore the live auctions and start bidding now!';

  @override
  String get purchasesBrowse => 'Browse auctions';

  @override
  String get purchasesSelectedCount => 'Selected';

  @override
  String get purchasesTotalDue => 'Total due';

  @override
  String get bankTransferTitle => 'Bank transfer';

  @override
  String get bankTransferBeneficiary => 'Beneficiary';

  @override
  String get bankTransferBank => 'Bank';

  @override
  String get bankTransferIban => 'IBAN';

  @override
  String get bankTransferAccount => 'Account no.';

  @override
  String get bankTransferPurpose => 'Transfer purpose';

  @override
  String get bankTransferCopy => 'Copy';

  @override
  String bankTransferCopied(String field) {
    return '$field copied.';
  }

  @override
  String get bankTransferNoteTopUp =>
      'Transfer the amount to the account above; it is added to your deposit once the bank confirms it.';

  @override
  String get bankTransferNoteInvoice =>
      'Transfer the invoice amount to the account above and put its number in the transfer purpose. The invoice settles once the bank confirms, and you may then request your deposit back.';

  @override
  String get bankTransferUnavailable =>
      'Transfer details are unavailable. Please contact support.';

  @override
  String get purchasesTransferAll => 'Transfer details';

  @override
  String get purchasesPayAll => 'Pay all selected';

  @override
  String get purchasesClear => 'Clear selection';

  @override
  String get purchasesPaySoon => 'Payment is not enabled yet.';

  @override
  String purchasesLotNumber(String number) {
    return 'Lot $number';
  }

  @override
  String get ordersSoon => 'Soon';

  @override
  String get ordersHandover => 'Waiver request';

  @override
  String get ordersTransfer => 'Ownership transfer';

  @override
  String get ordersDelivery => 'Delivery request';

  @override
  String get ordersReceive => 'Pickup request';

  @override
  String get supportTitle => 'Support';

  @override
  String get supportSubtitle => 'Pick the way that suits you to reach our team';

  @override
  String get supportWhatsApp => 'WhatsApp us';

  @override
  String get supportNotConfigured => 'Support number is not set yet.';

  @override
  String get supportInfo =>
      'Reach the support team on WhatsApp and we will reply shortly.';

  @override
  String get editRequestInfo =>
      'Editing your data is not available directly from the account. To change your data, open the in-app chat or reach us on WhatsApp and the support team will do it for you.';

  @override
  String get guideHeaderTitle => 'How to register on the auction site';

  @override
  String get guideHeaderSubtitle => 'Follow the simple steps to start bidding';

  @override
  String get guideStep1Title => 'Open the registration page';

  @override
  String get guideStep1Body =>
      'From the home page, tap \"Sign up\" or \"Create new account\".';

  @override
  String get guideStep2Title => 'Enter your details';

  @override
  String get guideStep2Body => 'Type your mobile number.';

  @override
  String get guideStep3Title => 'Confirm your mobile';

  @override
  String get guideStep3Body =>
      'A verification code is sent to your mobile; enter it to activate the account.';

  @override
  String get guideStep4Title => 'Activate and participate';

  @override
  String get guideStep4Body =>
      'After confirming, you can sign in, subscribe to a plan, and take part in auctions.';

  @override
  String get guideVideoSoon => 'The video will be added soon.';

  @override
  String get guideSupportHint =>
      'If you face any problem registering, reach us on support WhatsApp or the contact form.';

  @override
  String get guideContactHint =>
      'For any question, reach us on support WhatsApp or the contact form.';

  @override
  String get walletGuideHeaderTitle => 'How to top up the wallet';

  @override
  String get walletGuideHeaderSubtitle => 'Learn how to manage your wallet';

  @override
  String get walletGuideStep1Title => 'Open the wallet';

  @override
  String get walletGuideStep1Body =>
      'After signing in, from the main menu pick \"Account\", then \"Wallet\" to see the balance and the top-up button.';

  @override
  String get walletGuideStep2Title => 'Choose a payment method';

  @override
  String get walletGuideStep2Body =>
      'You can top up by bank transfer or electronic payment (card / Apple Pay).';

  @override
  String get walletGuideStep3Title => 'Transfer the amount';

  @override
  String get walletGuideStep3Body =>
      'Transfer the required amount to the bank account shown on the top-up page.';

  @override
  String get walletGuideStep4Title => 'Upload the transfer image';

  @override
  String get walletGuideStep4Body =>
      'After transferring, upload the receipt image through the form.';

  @override
  String get walletGuideStep5Title => 'Wait for approval';

  @override
  String get walletGuideStep5Body =>
      'The request is reviewed and the wallet top-up is confirmed shortly.';

  @override
  String get invoicePayAction => 'Pay from my balance';

  @override
  String get invoicePayConfirmTitle => 'Confirm payment';

  @override
  String invoicePayConfirmBody(String amount, String number) {
    return '$amount will be deducted from your deposit balance for invoice $number.';
  }

  @override
  String get topUpCancel => 'Cancel top-up';

  @override
  String get topUpCancelConfirmTitle => 'Cancel the request?';

  @override
  String topUpCancelConfirmBody(String reference) {
    return 'Request $reference will be cancelled and its payment link will stop working.';
  }

  @override
  String get topUpCancelled => 'The top-up request was cancelled.';

  @override
  String get refundSubmitted => 'Your refund request was sent.';

  @override
  String get refundAmountRequired => 'Enter the amount you want refunded.';

  @override
  String get purchasesNothingPayable =>
      'No invoice has been issued yet for what you selected.';

  @override
  String purchasesPaid(int count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$count invoices paid.',
      one: 'One invoice paid.',
    );
    return '$_temp0';
  }

  @override
  String get refundIbanUploaded => 'The IBAN image was uploaded.';

  @override
  String get refundIbanUploading => 'Uploading…';

  @override
  String get walletInsuranceHeld =>
      'محجوزٌ على مزادٍ قائم — يعود متاحاً عند انتهائه';

  @override
  String get walletInsuranceLocked =>
      'مقفولٌ على مستحقّاتٍ غير مسدَّدة — يُفكّ بالسداد';

  @override
  String get walletInsuranceCommitted => 'من تأمينك مرتبطٌ الآن';
}
