import '../../common/snapshot.dart';
import '../entities/bid_outcome.dart';
import '../entities/live_bids_update.dart';
import '../entities/placed_bid.dart';

/// عقد المزايدة.
///
/// **ما ليس فيه هو أهم ما فيه:** لا `canBid`، ولا `minimumNextBid`، ولا
/// «هل عنده تأمين». `check_eligibility` في الخلفية نقطة القرار الوحيدة
/// (وللبناء حارسٌ يرفض ثانيةً)، وكل ما يستطيعه التطبيق أن يرسل ويعرض الجواب.
/// في v1 كانت الصفحة الرئيسية وحدها فيها ستة مسارات لإرسال مزايدة، فتسرّبت كل
/// قاعدة جديدة من واحد منها؛ قناة ثالثة تعني السطح نفسه أوسع.
abstract interface class BiddingRepository {
  /// يرسل مزايدة على مركبة.
  ///
  /// [amount] نصّ عشري **كما كتبه العميل** — لا تطبيع ولا تقريب ولا حساب حدّ
  /// أدنى (المادة ٣-٢، ومبدأ الفيز 008 الحاكم).
  ///
  /// [confirmLower] لا يُرسَل `true` إلا بعد رفضٍ صريح من الخادم طلب التأكيد.
  /// استنتاجه في التطبيق («يبدو أقل، خلّينا نضيف العلم») يمشي مباشرةً خلال
  /// الحارس الذي وُجد F3 من أجله.
  ///
  /// يرجع `BidOutcome`؛ ويرمي `Failure` لكل رفض آخر برسالة الخادم العربية.
  Future<BidOutcome> placeBid({
    required String vehicleId,
    required String amount,
    bool confirmLower,
  });

  /// يسحب مزايدة قائمة. الملكية والتوقيت قرار الخادم، لا شرط في الشاشة.
  Future<PlacedBid> withdrawBid(String bidId);

  /// مزايدات العميل نفسه.
  ///
  /// `Snapshot` لا قائمة مجرّدة: العرض يحتاج أن يعرف إن كانت هذه آخر نسخة من
  /// الخادم أم محفوظة، ومتى جُلبت (معيار H5).
  Future<Snapshot<List<PlacedBid>>> myBids();

  /// بثّ حالة مزايدات العميل.
  ///
  /// يعيد الاتصال من تلقائه، ويعلن الانقطاع بدل أن يترك أرقاماً بائتة تبدو
  /// حيّة. البثّ لا يحمل رقم أحد غير المتصل — المزاد مغلق.
  Stream<LiveBidsUpdate> watchLive();
}
