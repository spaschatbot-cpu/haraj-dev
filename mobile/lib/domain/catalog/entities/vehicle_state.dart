/// حالة المركبة **كما يقولها الخادم**.
///
/// القائمة واسعة عمداً، ونصُّها في `apps/auctions/states.py`: v1 ضغط هذا
/// التعداد إلى أربع قيم مرّةً فضاع الفرق بين مركبةٍ لم يزايد عليها أحد ومركبةٍ
/// رفض مالكها أعلى مزايدة — حالتان خطوتُهما التالية متعاكستان.
enum VehicleState {
  draft('draft'),
  listed('listed'),
  bidding('bidding'),
  awaitingDecision('awaiting_decision'),
  awarded('awarded'),
  rejected('rejected'),
  invoiced('invoiced'),
  paid('paid'),
  released('released'),
  withdrawn('withdrawn'),
  relisted('relisted'),

  /// حالةٌ لم يعرفها هذا الإصدار.
  ///
  /// المادتان ٢-٣ و٣-٥: قيمة لم نرها من قبل تُحفظ ولا تُسقط الاستجابة التي
  /// تحملها. مركبةٌ بحالةٍ مجهولة تُعرض، وزرُّ المزايدة عليها **معطَّل** — لا
  /// لأننا حكمنا بأنها مغلقة، بل لأن الجهل ليس إذناً؛ والخادم يبقى هو الفاصل
  /// إن حاول أحدٌ رغم ذلك.
  unknown('');

  const VehicleState(this.slug);

  /// الاسم على السلك — نصٌّ واحد للمعنى الواحد.
  final String slug;

  /// الحالتان اللتان تقبلان مزايدة.
  ///
  /// مطابقةٌ لـ`BIDDABLE_VEHICLE_STATES` في `apps/bidding/eligibility.py`،
  /// وهي **نسخةٌ ثانية معترَفٌ بها**: تُستعمل لتعطيل زرّ فتوفير نداء، ولا
  /// تُستعمل لمنح إذن. الإذن ردُّ الخادم وحده، فانحرافُ هذه القائمة يوماً
  /// يُظهر زرّاً يُرفض ضغطُه برسالةٍ مكتوبة — لا مزايدةً تمرّ بلا حق.
  bool get isBiddable => this == listed || this == bidding;

  static VehicleState fromSlug(String? slug) => values.firstWhere(
    (state) => state.slug == slug,
    orElse: () => VehicleState.unknown,
  );
}
