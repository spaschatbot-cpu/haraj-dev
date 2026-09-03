import 'package:flutter_test/flutter_test.dart';
import 'package:haraj_mobile/domain/notifications/entities/push_destination.dart';
import 'package:haraj_mobile/domain/notifications/entities/push_notification.dart';
import 'package:haraj_mobile/domain/notifications/usecases/resolve_push_destination.dart';

/// معيار القبول H6: «الإشعار يفتح الشاشة الصحيحة مباشرةً»، وقبول T716:
/// «اختبار لكل نوع إشعار».
void main() {
  PushDestination resolve(Map<String, String> data) =>
      ResolvePushDestination.call(PushNotification(data: data));

  group('المزايدة تفتح المركبة نفسها', () {
    test('«زُوِّد عليك» يفتح المركبة ومعها مزادها', () {
      expect(
        resolve({'type': 'outbid', 'auction_id': '12', 'vehicle_id': '340'}),
        const PushDestination.vehicle('340', auctionId: '12'),
      );
    });

    for (final type in ['bid_placed', 'bid_won', 'bid_lost']) {
      test('$type يفتح المركبة', () {
        expect(
          resolve({'type': type, 'vehicle_id': '7'}).target,
          PushTarget.vehicle,
        );
      });
    }

    test('مزايدة بلا رقم مركبة تسقط إلى المزاد لا إلى شاشة خطأ', () {
      // «افتح مركبة بلا رقم» عنوان مكسور يراه المستخدم شاشةَ خطأ بعد ضغطه
      // إشعاراً. المزاد جواب أنقص لكنه صحيح.
      expect(
        resolve({'type': 'outbid', 'auction_id': '12'}),
        const PushDestination.auction('12'),
      );
    });

    test('مزايدة بلا أي معرّف تفتح مزايداتي', () {
      expect(resolve({'type': 'outbid'}), const PushDestination.bids());
    });
  });

  group('المزاد', () {
    for (final type in [
      'auction_starting',
      'auction_ended',
      'auction_updated',
    ]) {
      test('$type يفتح المزاد', () {
        expect(
          resolve({'type': type, 'auction_id': '91'}),
          const PushDestination.auction('91'),
        );
      });
    }

    test('مزاد بلا رقم يفتح الرئيسية', () {
      expect(
        resolve({'type': 'auction_starting'}),
        const PushDestination.home(),
      );
    });
  });

  group('الفواتير', () {
    for (final type in ['invoice_issued', 'invoice_due', 'invoice_paid']) {
      test('$type يفتح الفاتورة بعينها', () {
        expect(
          resolve({'type': type, 'invoice_id': 'INV-5'}),
          const PushDestination.invoice(invoiceId: 'INV-5'),
        );
      });
    }

    test('فاتورة بلا رقم تفتح قائمة الفواتير', () {
      expect(resolve({'type': 'invoice_due'}), const PushDestination.invoice());
    });
  });

  group('المحفظة', () {
    for (final type in [
      'topup_settled',
      'refund_decided',
      'hold_placed',
      'hold_released',
    ]) {
      test('$type يفتح المحفظة', () {
        expect(resolve({'type': type}), const PushDestination.wallet());
      });
    }
  });

  test('bids_summary يفتح مزايداتي', () {
    expect(resolve({'type': 'bids_summary'}), const PushDestination.bids());
  });

  group('ما لا نعرفه لا يُسقط الإشعار', () {
    test('نوع لم نره من قبل يفتح الرئيسية', () {
      // التطبيق المنشور أقدم من الخادم دائماً. يوم يضيف الخادم نوعاً جديداً
      // يبقى إشعاره يفتح شيئاً بدل أن يُبتلع (المادتان ٢-٣ و٣-٥).
      expect(
        resolve({'type': 'something_we_ship_next_year', 'auction_id': '3'}),
        const PushDestination.home(),
      );
    });

    test('إشعار بلا نوع أصلاً يفتح الرئيسية', () {
      expect(resolve(const {}), const PushDestination.home());
    });

    test('معرّف فارغ ليس معرّفاً', () {
      // بدونه يتولّد `/vehicles/` ثم شاشة «مسار غير موجود».
      expect(
        resolve({'type': 'outbid', 'vehicle_id': '  ', 'auction_id': '4'}),
        const PushDestination.auction('4'),
      );
    });
  });
}
