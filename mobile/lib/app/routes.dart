import 'package:flutter/widgets.dart';
import 'package:go_router/go_router.dart';

import '../domain/notifications/entities/push_destination.dart';

/// مسارات التطبيق وأسماؤها — **تعريف واحد** يقرأ منه التوجيه والإشعارات معاً.
///
/// السبب في وجود الملف منفصلاً عن `router.dart`: معيار H6 يقول إن الإشعار يفتح
/// الشاشة الصحيحة، فصار للمسار قارئان — جدول التوجيه، ومترجم حمولة الإشعار.
/// مسار مكتوب نصّاً في القارئين يفترق فيهما عند أول تعديل، ويظهر الفرق عند
/// المستخدم شاشةَ «مسار غير موجود» بعد ضغطه إشعاراً (المادة ٤-٥).
///
/// شاشات المجموعة ب (T706–T715) تُركَّب على هذه المسارات نفسها ولا تخترع غيرها.
abstract final class Routes {
  static const String seed = 'seed';
  static const String home = 'home';
  static const String signIn = 'signIn';
  static const String verifyCode = 'verifyCode';
  static const String profile = 'profile';
  static const String companyProfile = 'companyProfile';
  static const String changePhone = 'changePhone';
  static const String auction = 'auction';
  static const String auctionVehicles = 'auction-vehicles';
  static const String vehicle = 'vehicle';
  static const String bids = 'bids';
  static const String wallet = 'wallet';
  static const String invoices = 'invoices';
  static const String invoice = 'invoice';

  static const String homePath = '/';
  static const String signInPath = '/sign-in';
  static const String verifyCodePath = '/sign-in/code';
  static const String profilePath = '/profile';
  static const String auctionPath = '/auctions/:auctionId';
  static const String vehiclePath = '/vehicles/:vehicleId';
  static const String bidsPath = '/bids';
  static const String walletPath = '/wallet';
  static const String invoicesPath = '/invoices';
  static const String invoicePath = '/invoices/:invoiceId';

  // بناء العنوان يعيش مع اسمه: شاشة تبني عنوانها بنفسها تفترق عنه عند أول
  // تعديل، فتفتح شاشةً غير التي يفتحها الإشعار (معيار H6).
  static void goToAuctionVehicles(BuildContext context, String auctionId) =>
      GoRouter.of(context).goNamed(
        auctionVehicles,
        pathParameters: <String, String>{'auctionId': auctionId},
      );

  static void goToVehicle(BuildContext context, String vehicleId) =>
      GoRouter.of(context).goNamed(
        vehicle,
        pathParameters: <String, String>{'vehicleId': vehicleId},
      );
}

/// يترجم وجهة إشعار إلى عنوان يفهمه `go_router`.
///
/// الاشتقاق (أي حمولة تعني أي شاشة) قرارٌ نطاقي في
/// `domain/notifications/usecases/resolve_push_destination.dart`؛ وهذا الملف
/// لا يقرّر شيئاً، يترجم فقط.
abstract final class PushLocations {
  static String of(PushDestination destination) {
    final auctionId = destination.auctionId;
    final vehicleId = destination.vehicleId;
    final invoiceId = destination.invoiceId;

    return switch (destination.target) {
      PushTarget.auction when auctionId != null => '/auctions/$auctionId',
      PushTarget.vehicle when vehicleId != null => '/vehicles/$vehicleId',
      PushTarget.bids => Routes.bidsPath,
      PushTarget.wallet => Routes.walletPath,
      PushTarget.invoice when invoiceId != null => '/invoices/$invoiceId',
      PushTarget.invoice => Routes.invoicesPath,
      // يشمل الرئيسية، ويشمل وجهةً بُنيت بلا معرّفها. الأخيرة لا تنتج من
      // المشتقّ (منشئاته تطلب المعرّف)، وتُفتح الرئيسية بدل عنوان مكسور.
      _ => Routes.homePath,
    };
  }
}
