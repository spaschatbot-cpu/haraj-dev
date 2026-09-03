/// مزاد كما يظهر في قائمة — لا أكثر.
///
/// **لا يحمل حالته عمداً.** الرئيسية لا تقرّر أي مزاد «جارٍ» وأيّه «قادم»: تسأل
/// الخادم مرتين، مرة بكل حالة، وتعرض ما ردّ به. لو حمل الكيان الحالة لأغرى
/// الشاشةَ بأن تصنّف بنفسها، فصار لـ«جارٍ» تعريفان — واحد هنا وواحد في
/// `apps/auctions/states.py` — يفترقان عند أول حالة جديدة.
final class AuctionSummary {
  const AuctionSummary({
    required this.id,
    required this.title,
    required this.startsAt,
    required this.endsAt,
    required this.vehiclesCount,
  });

  final String id;
  final String title;

  /// بتوقيت UTC — التحويل للعرض عند حافة العرض وحدها (المادة ٣-١).
  final DateTime startsAt;
  final DateTime endsAt;

  /// عدد المركبات كما عدّه الخادم. التطبيق لا يعدّ صفوفاً وصلته صفحةٌ منها.
  final int vehiclesCount;
}

/// ما تعرضه الرئيسية: مزادات جارية ومزادات قادمة، مقسومة كما قسمها الخادم.
final class HomeAuctions {
  const HomeAuctions({required this.running, required this.upcoming});

  final List<AuctionSummary> running;
  final List<AuctionSummary> upcoming;

  bool get isEmpty => running.isEmpty && upcoming.isEmpty;
}
