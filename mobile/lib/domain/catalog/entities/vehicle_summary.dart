import '../../common/money.dart';
import 'auction_phase.dart';
import 'vehicle_state.dart';

/// المركبة كما تظهر في **كرت** — وهذه هي كل حقول الكرت.
///
/// جمعُ الحقول في كيان واحد نصفُ قاعدة «كرت واحد»؛ نصفها الآخر مكوّن عرض واحد
/// (`presentation/catalog/widgets/vehicle_card.dart`) وفحصٌ نصّي يمنع رسم كرت
/// خارجه. في v1 كانت الصفحة الرئيسية وحدها فيها أربعة مسارات لرسم الكرت وثلاث
/// قوائم حقول، فأي حقل جديد يظهر في بعضها ويختفي في الباقي بصمت.
final class VehicleSummary {
  const VehicleSummary({
    required this.id,
    required this.lotNumber,
    required this.title,
    required this.thumbnailUrl,
    required this.reference,
    required this.adminFee,
    required this.adminFeeWithVat,
    required this.auctionId,
    required this.phase,
    required this.state,
    required this.isFavourite,
    required this.auctionEndsAt,
    required this.year,
    required this.odometerKm,
    required this.colourLabel,
    required this.conditionLabel,
    required this.location,
  });

  final String id;
  final String lotNumber;
  final String title;

  /// مصغَّرة فقط — الحجم الكامل في صفحة المركبة (قاعدة التصميم 6 في الفيز 008).
  final String? thumbnailUrl;

  /// الرقم المرجعيّ على الكرت — `#10565` كما في v1.
  final String reference;

  /// الرسوم الإدارية، ومعها الرسوم + الضريبة (١٥٪) — وهما **كل ما يُعرض من
  /// مال على الكرت**.
  ///
  /// **ولا سعرَ وقوفٍ هنا ولا عددَ مزايدات**، وكانا موجودين. المزاد **مغلق**
  /// (قرارٌ في `ce013b9`): لا سعر افتتاحيّ يُنشر ولا أعلى مزايدة، فالخادم لا
  /// يرسل `reserve_price` ولا `bids_count` أصلاً. كان الكرت يعرضهما لأنه بُني
  /// على مخططٍ وهميّ أُضيف إليه `reserve_price` بيد — فكان يعد بما لا يصل، ثم
  /// يسقط على `null` عند أول استجابةٍ حقيقية.
  ///
  /// نصّاً كما وصل، لا `double`: المادة ٣-٢.
  final Money adminFee;
  final Money adminFeeWithVat;

  /// مزاد هذه المركبة.
  ///
  /// يُحمل على الكرت لأن الشبكة المسطّحة تجمع مركبات مزادات شتّى في قائمة
  /// واحدة، فلا يكفي أن يعرفه سياق الشاشة كما كان يكفي في قائمة مزادٍ بعينه.
  final String auctionId;

  /// طور مزادها **كما قاله الخادم** — لا كما يُستنتج من `auctionEndsAt`.
  final AuctionPhase phase;

  /// حالة المركبة نفسها — بها يُفعَّل زرّ المزايدة أو يُعطَّل.
  final VehicleState state;

  /// هل حفظ **هذا العميل** المركبة في مفضّلته.
  ///
  /// الحقل الوحيد على الكرت الذي يخصّ القارئ لا المركبة: نفس السيارة مفضّلةٌ
  /// لواحد وليست لآخر. يأتي من الخادم محسوباً للصفحة كلها، فلا تسأل الشاشة
  /// عنه صفّاً صفّاً — ولا تخمّنه من قائمةٍ حمّلتها، فقائمةٌ من صفحةٍ واحدة
  /// تقول «غير مفضّلة» عن مركبةٍ في الصفحة الثانية.
  final bool isFavourite;

  /// لحظة انتهاء مزادها، بتوقيت UTC.
  ///
  /// تُحمل على الكرت لأن العدّاد التنازلي على الكرت، وطلبها لكل كرت على حدة
  /// يعني طلباً لكل مركبة. والتحويل للعرض يبقى في `SaudiTime` وحدها
  /// (المادة ٣-١)، والعدّ نفسه فرقٌ بين لحظتين UTC لا حسابُ تقويم.
  final DateTime auctionEndsAt;

  /// سنة الصنع، والممشى، واللونُ والحالة **بتسميتيهما المعروضتين**.
  ///
  /// أربعتُها على الكرت لا في صفحة المركبة وحدها: الصفّ الذي تحت الاسم هو ما
  /// يفرّق سيّارةً عن أختها في قائمةٍ من تسعٍ متشابهة، وبدونه يُفتح الكرت
  /// ليُغلق فوراً. وكلُّها في `VehicleCard` من الخادم أصلاً — كانت تصل ولا
  /// تُقرأ.
  ///
  /// **والتسمية من الخادم لا من التطبيق**: `colour_label` و`condition_label`
  /// نصّان جاهزان، وترجمةُ `silver` إلى «فضي» في التطبيق قاموسٌ ثانٍ يفترق عن
  /// الأول عند أول لونٍ يُضاف (المادة ٤-٥).
  final int year;

  /// `null` يعني **لم يُقَس**، لا صفراً: «٠ كم» ادّعاءٌ لم يقله أحد.
  final int? odometerKm;

  final String colourLabel;
  final String conditionLabel;

  /// موقع المركبة كما يعرضه الخادم — «الرياض / طريق الحائر».
  ///
  /// **خامسُ حقلٍ كان يصل ولا يُقرأ**: `location` في `VehicleCard` المولَّد من
  /// المخطط منذ البداية، ولم يكن في هذا الكيان. وهو على الكرت لا في صفحة
  /// المركبة وحدها لأن الاستلام حضوريّ: من يزايد على سيّارةٍ في مدينةٍ أخرى
  /// يعرف ذلك قبل أن يزايد لا بعده.
  ///
  /// نصٌّ واحد لا مدينةٌ وفرعٌ منفصلان: الخادم يرسله مركّباً، وقسمتُه هنا
  /// على `/` تفترض شكلاً لم يَعِد به أحد.
  final String location;
}
