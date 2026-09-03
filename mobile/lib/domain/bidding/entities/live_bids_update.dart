/// حالة البثّ الحي، ومعها آخر ما وصل منه.
///
/// **لماذا الحالة والبيانات في كائن واحد:** رقم مزايدة قديم يبدو حياً أسوأ من
/// لا رقم — من يقرأ رقماً بائتاً ويزايد عليه يخسر مالاً حقيقياً. فلا يجوز أن
/// تصل الأرقامُ الشاشةَ بلا الجملة التي تقول كم تُصدَّق. لو كانت الحالة في
/// مزوّد والبيانات في آخر، لظهرت شاشةٌ تعرض الأرقام وتنسى العلامة عند أول
/// إعادة ترتيب.
library;

/// حال الاتصال بالبثّ.
enum LiveConnection {
  /// يحاول الاتصال — أول مرة أو بعد انقطاع.
  connecting,

  /// متصل، وآخر إطار وصل في وقته.
  live,

  /// انقطع أو صمت الخادم عن النبض. ما يُعرض الآن قديم.
  lost,
}

/// مزايدة قائمة للعميل نفسه كما وصلت في البثّ.
///
/// المبلغ نصّ بلا عملة لأن الإطار لا يحمل عملة — والتطبيق لا يخترع واحدة.
final class LiveStandingBid {
  const LiveStandingBid({
    required this.id,
    required this.vehicleId,
    required this.amount,
    required this.isWithdrawn,
    required this.isSuperseded,
  });

  final String id;
  final String vehicleId;

  /// نصّ عشري كما في الدفتر.
  final String amount;

  final bool isWithdrawn;

  /// حلّت محلّها مزايدة أحدث للعميل نفسه.
  final bool isSuperseded;
}

/// لقطة واحدة من البثّ: كيف حال الاتصال، وآخر مزايدات معروفة.
final class LiveBidsUpdate {
  const LiveBidsUpdate({required this.connection, required this.bids});

  final LiveConnection connection;

  /// آخر ما وصل. تبقى كما هي عند الانقطاع — تُعرض مع العلامة، ولا تُمحى:
  /// شاشةٌ تُفرَّغ عند أول انقطاع تخفي عن العميل ما زايد به فعلاً.
  final List<LiveStandingBid> bids;

  /// ما يُعرض الآن ليس مضموناً أنه الحالي.
  bool get isStale => connection != LiveConnection.live;

  /// المزايدة القائمة على مركبة بعينها، إن وُجدت.
  ///
  /// المسحوبة والمستبدَلة ليستا قائمتين: البثّ قد يحملهما (السحب حدثٌ يهمّ
  /// العميل)، والشاشة تسأل عن «مزايدتي الآن».
  LiveStandingBid? standingOn(String vehicleId) {
    for (final bid in bids) {
      if (bid.vehicleId == vehicleId && !bid.isWithdrawn && !bid.isSuperseded) {
        return bid;
      }
    }
    return null;
  }
}
