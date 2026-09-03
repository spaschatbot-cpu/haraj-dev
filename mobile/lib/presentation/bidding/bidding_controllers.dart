import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app/providers.dart';
import '../../domain/bidding/entities/bid_outcome.dart';
import '../../domain/bidding/entities/live_bids_update.dart';
import '../../domain/bidding/entities/placed_bid.dart';
import '../../domain/common/failure.dart';
import '../../domain/common/snapshot.dart';

/// حالة صندوق المزايدة.
///
/// نوع مغلق لا حقول اختيارية: «يُرسل الآن» و«رُفض» و«يحتاج تأكيداً» حالات
/// يستحيل اجتماعها، وتمثيلها بأعلام منفصلة يسمح بشاشة تعرض دوّامةً ورسالة
/// خطأ معاً — وهي الشاشة التي لا يعرف قارئها ماذا حدث.
sealed class PlaceBidState {
  const PlaceBidState();
}

/// لم يُرسَل شيء بعد، أو صُرف النظر عن آخر جواب.
final class PlaceBidIdle extends PlaceBidState {
  const PlaceBidIdle();
}

final class PlaceBidSubmitting extends PlaceBidState {
  const PlaceBidSubmitting();
}

final class PlaceBidAccepted extends PlaceBidState {
  const PlaceBidAccepted(this.bid);

  final PlacedBid bid;
}

/// الخادم طلب تأكيد الخفض، ومعه المبلغان اللذان كان الرفض عنهما.
final class PlaceBidNeedsConfirmation extends PlaceBidState {
  const PlaceBidNeedsConfirmation(this.request);

  final BidNeedsLowerConfirmation request;
}

/// رُفضت. `failure` تحمل رسالة الخادم العربية، وتُعرض كما جاءت.
final class PlaceBidRefused extends PlaceBidState {
  const PlaceBidRefused(this.failure);

  final Failure failure;
}

/// يقود إرسال مزايدة واحدة على مركبة واحدة.
///
/// **لا يقرّر شيئاً.** لا يقارن المبلغ بحدّ أدنى، ولا يسأل عن تأمين، ولا
/// يستنتج أن هذه المزايدة «تبدو أقل» فيضيف علم التأكيد من عنده. يرسل، ويصنّف
/// الجواب. علم `confirmLower` لا يُرفع إلا في نداءٍ ثانٍ يطلبه المستخدم بعد
/// رفضٍ صريح من الخادم — وهذا هو معنى F3.
final class PlaceBidController extends Notifier<PlaceBidState> {
  PlaceBidController(this._vehicleId);

  final String _vehicleId;

  @override
  PlaceBidState build() => const PlaceBidIdle();

  Future<void> submit(String amount, {bool confirmLower = false}) async {
    state = const PlaceBidSubmitting();
    try {
      final outcome = await ref.read(placeBidProvider)(
        vehicleId: _vehicleId,
        amount: amount,
        confirmLower: confirmLower,
      );
      state = switch (outcome) {
        BidAccepted(:final bid) => PlaceBidAccepted(bid),
        BidNeedsLowerConfirmation() => PlaceBidNeedsConfirmation(outcome),
      };
    } on Failure catch (failure) {
      state = PlaceBidRefused(failure);
    }
  }

  /// يُنسي الشاشة آخر جواب — بعد إغلاق حوار التأكيد بالإلغاء مثلاً.
  void dismiss() => state = const PlaceBidIdle();
}

final placeBidControllerProvider = NotifierProvider.autoDispose
    .family<PlaceBidController, PlaceBidState, String>(PlaceBidController.new);

/// مزايدات العميل، مع مصدرها ولحظة جلبها (H5).
final myBidsProvider = FutureProvider.autoDispose<Snapshot<List<PlacedBid>>>(
  (ref) => ref.watch(loadMyBidsProvider)(),
);

/// البثّ الحي.
///
/// `autoDispose` مقصود: الاتصال يُغلق حين تُغلق الشاشة. بثّ يبقى مفتوحاً بعد
/// خروج المستخدم من الشاشة يستهلك اتصالاً على الخادم لكل مستخدم فتح الشاشة
/// مرة، وهو ثمن يُدفع بلا قارئ.
final liveBidsProvider = StreamProvider.autoDispose<LiveBidsUpdate>(
  (ref) => ref.watch(watchLiveBidsProvider)(),
);
