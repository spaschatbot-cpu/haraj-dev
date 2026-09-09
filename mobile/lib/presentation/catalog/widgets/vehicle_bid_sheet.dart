import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../app/theme.dart';
import '../../../domain/catalog/entities/vehicle_summary.dart';
import '../../../domain/common/money.dart';
import '../../../l10n/generated/app_localizations.dart';
import '../../bidding/bidding_controllers.dart';
import '../../bidding/lower_bid_confirmation_dialog.dart';
import '../../common/failure_message.dart';
import '../../common/money_text.dart';
import '../favourites_controller.dart';
import 'remote_image.dart';

/// صندوقُ المزايدة — يُفتح من زرّ «مزايدة» في الكرت، على هيئة نافذة v1.
///
/// **نقضٌ مكتوبٌ لقرارٍ سابق**: كان الزرّ يفتح صفحة المركبة، والسببُ أن
/// المزايدة تحتاج الرصيد والحدَّ الأدنى وشروطَ الأهلية وكلُّها هناك. وطلب
/// المالك النافذة في ٩ سبتمبر ٢٠٢٦ على مثال v1 — **والسببُ محفوظ**: لا مزايدةَ
/// تقع من هنا. الصندوقُ يعرض ما يعرفه الكرت، وزرُّه الوحيد ينقل إلى الصفحة.
///
/// **والمزايدةُ تقع من هنا** — بقرار المالك في ٩ سبتمبر ٢٠٢٦، وحُذفت شاشةُ
/// المزايدة التي كانت تستقبلها. والشرطُ الذي حماها يومَ كان الزرُّ ينقل إلى
/// شاشة: لا مزايدةَ بضغطةٍ واحدة على كرتٍ في قائمة — فالمبلغُ يُكتب في الصندوق
/// أوّلاً، وزرٌّ بلا مبلغٍ معطَّل.
///
/// **ولا حكمَ هنا على المبلغ** (معيار J7): لا حدَّ أدنى يُحسب، ولا أهليّةَ
/// تُفحص، ولا مقارنةَ بمزايدةٍ قائمة. الخادمُ وحده يقبل أو يرفض، ونصُّ رفضِه
/// هو ما يُعرض — وأيُّ فرعٍ هنا ينتج سبباً ثانياً يفترق عنه.
Future<void> showVehicleBidSheet(
  BuildContext context, {
  required VehicleSummary vehicle,
}) => showDialog<void>(
  context: context,
  builder: (dialogContext) => _BidSheet(vehicle: vehicle),
);

class _BidSheet extends ConsumerStatefulWidget {
  const _BidSheet({required this.vehicle});

  final VehicleSummary vehicle;

  @override
  ConsumerState<_BidSheet> createState() => _BidSheetState();
}

class _BidSheetState extends ConsumerState<_BidSheet> {
  /// السعرُ الذي يكتبه العميل — **مسوّدتُه هو، لا رقمٌ من الخادم**.
  final TextEditingController _price = TextEditingController();

  /// حالُ القلب بعد ضغطةٍ **نجحت**. `null` يعني «لم يُضغط هنا» فيُقرأ من
  /// المركبة. ولا يُكتب إلا بعد ردّ الخادم: قلبٌ يمتلئ قبل الردّ ثم يفشل
  /// الطلب يترك العميل يظنّ أنه حفظ ما لم يُحفظ.
  bool? _saved;

  /// طلبٌ جارٍ — يمنع ضغطتين متتاليتين تُلغي ثانيتُهما أولاهما.
  bool _busy = false;

  bool get _isFavourite => _saved ?? vehicle.isFavourite;

  Future<void> _toggleFavourite() async {
    if (_busy) return;
    setState(() => _busy = true);
    final was = _isFavourite;
    try {
      await ref.read(toggleFavouriteProvider)(
        vehicleId: vehicle.id,
        isFavourite: was,
      );
      if (!mounted) return;
      setState(() {
        _saved = !was;
        _busy = false;
      });
    } on Object {
      // الفشل يُقال ولا يُبتلع: القلب يبقى على حاله ويظهر سطرٌ يشرح لماذا لم
      // يتغيّر. بلا هذا يضغط العميل ولا يحدث شيء فيظنّ الزرّ معطّلاً.
      if (!mounted) return;
      setState(() => _busy = false);
      _say(AppLocalizations.of(context).favouriteFailed);
    }
  }

  /// المشاركة **نسخُ الرابط** لا ورقةَ نظام: `share_plus` ليست في التبعيّات،
  /// وإضافةُ حزمةٍ لزرٍّ في نافذة أكبرُ من ثمنه. والنسخُ يفعل ما يريده من
  /// ضغط الزرّ: أن يخرج الرابطُ من التطبيق إلى محادثة.
  /// يرسل المبلغَ المكتوب، ويعرض جوابَ الخادم كما وصل.
  ///
  /// **والتأكيدُ على خفض المبلغ يمرّ بحواره** كما في الشاشة المحذوفة: النداءُ
  /// الثاني وحده يحمل `confirmLower`، ولا يحمله إلا بعد أن طلبه الخادمُ
  /// وأقرّه العميل. استنتاجُه هنا يمشي خلال الحارس الذي وُجد له.
  Future<void> _placeBid() async {
    final amount = _price.text.trim();
    if (amount.isEmpty) return;

    final controller = ref.read(
      placeBidControllerProvider(vehicle.id).notifier,
    );
    await controller.submit(amount);
    if (!mounted) return;

    final first = ref.read(placeBidControllerProvider(vehicle.id));
    if (first case final PlaceBidNeedsConfirmation pending) {
      final confirmed = await showDialog<bool>(
        context: context,
        builder: (context) =>
            LowerBidConfirmationDialog(request: pending.request),
      );
      if (!mounted) return;
      if (!(confirmed ?? false)) {
        controller.dismiss();
        return;
      }
      await controller.submit(amount, confirmLower: true);
      if (!mounted) return;
    }

    // **تُقرأ الحالةُ بعد الفرعين معاً**: نداءٌ واحد أو نداءان، والجوابُ
    // المعروض هو الأخير لا الأول.
    final state = ref.read(placeBidControllerProvider(vehicle.id));
    switch (state) {
      case PlaceBidAccepted():
        // **القائمةُ تُبطَل لا تُعدَّل**: «مشاركاتي» تُبنى من مزايدات الخادم،
        // وإضافةُ صفٍّ محلياً تقول «سُجّلت» قبل أن يقولها هو.
        ref.invalidate(myBidsProvider);
        Navigator.of(context).pop();
        await showDialog<void>(
          context: context,
          builder: (context) => _NoticeDialog(
            message: AppLocalizations.of(context).bidPlacedTitle,
            accepted: true,
          ),
        );
      case PlaceBidRefused(:final failure):
        // **حوارٌ في وسط الشاشة لا شريطُ رسالةٍ في قاعها** — بطلب المالك في ٩
        // سبتمبر ٢٠٢٦. الشريطُ يظهر أسفل الصندوق وقد يمرّ قبل أن يُقرأ،
        // ورفضُ مزايدةٍ جوابٌ على فعلٍ مقصود يستحقّ إقراراً بضغطة.
        await showDialog<void>(
          context: context,
          builder: (context) => _NoticeDialog(
            message: failureMessage(context, failure),
            accepted: false,
          ),
        );
      case _:
        break;
    }
  }

  Future<void> _share() async {
    await Clipboard.setData(
      ClipboardData(text: '${vehicle.title} — ${vehicle.reference}'),
    );
    if (!mounted) return;
    _say(AppLocalizations.of(context).vehicleShareCopied);
  }

  void _say(String message) {
    // **`maybeOf` لا `of`**: النافذة قد تُغلق قبل أن يصل الردّ، ولا
    // `ScaffoldMessenger` فوق `Dialog` مغلق.
    ScaffoldMessenger.maybeOf(
      context,
    )?.showSnackBar(SnackBar(content: Text(message)));
  }

  VehicleSummary get vehicle => widget.vehicle;

  @override
  void initState() {
    super.initState();
    // إعادةُ البناء عند كل حرف: «السعر + الضريبة» تحته يتبع ما يُكتب فوقه،
    // وحقلٌ يتغيّر ومجموعٌ لا يتغيّر معه يُقرأ عطلاً.
    _price.addListener(() => setState(() {}));
  }

  @override
  void dispose() {
    _price.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final palette = HarajPalette.of(context);
    final odometer = vehicle.odometerKm;

    return Dialog(
      insetPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 40),
      backgroundColor: palette.cardSurface,
      clipBehavior: Clip.antiAlias,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
      child: ConstrainedBox(
        // **بعرضٍ محدود ٤٤٠** — نفس حدّ الكرت ولوحة الترحيب، فتقف الثلاثةُ
        // على عمودٍ واحد على الشاشة العريضة.
        constraints: const BoxConstraints(maxWidth: 440),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: <Widget>[
            _Header(
              title: vehicle.title,
              palette: palette,
              onShare: _share,
              onFavourite: _busy ? () {} : _toggleFavourite,
              isFavourite: _isFavourite,
            ),
            Flexible(
              // **قابلٌ للتمرير**: عددُ الخانات ثابت، وارتفاعُ الشاشة ليس
              // كذلك — وعلى جوّالٍ قصير كان يفيض.
              child: SingleChildScrollView(
                padding: const EdgeInsets.fromLTRB(14, 0, 14, 14),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: <Widget>[
                    ClipRRect(
                      borderRadius: BorderRadius.circular(12),
                      child: SizedBox(
                        height: 150,
                        child: RemoteImage(
                          url: vehicle.thumbnailUrl,
                          decodeWidth: 800,
                        ),
                      ),
                    ),
                    const SizedBox(height: 12),
                    // **خانتان في السطر لا أربع**: أربعٌ في سطرٍ واحد على شاشة
                    // ٣١٧ تترك لكلٍّ منها سبعين بكسلاً، و«بي ام دبليو اكس 3»
                    // تحت تسميةٍ لا تُقرأ فيها.
                    _SpecRow(
                      first: _Spec(
                        icon: Icons.directions_car_filled_outlined,
                        label: l10n.vehicleSpecModel,
                        value: vehicle.title,
                        palette: palette,
                      ),
                      second: _Spec(
                        icon: Icons.calendar_today_rounded,
                        label: l10n.vehicleSpecYear,
                        value: vehicle.year.toString(),
                        palette: palette,
                      ),
                    ),
                    const SizedBox(height: 8),
                    _SpecRow(
                      first: _Spec(
                        icon: Icons.palette_outlined,
                        label: l10n.vehicleSpecColour,
                        value: vehicle.colourLabel,
                        palette: palette,
                      ),
                      second: _Spec(
                        icon: Icons.speed_rounded,
                        label: l10n.vehicleSpecOdometer,
                        // الغيابُ شرطةٌ لا صفر: «٠ كم» ادّعاءٌ لم يقله أحد.
                        value: odometer == null
                            ? '—'
                            : l10n.vehicleOdometerShort(odometer),
                        palette: palette,
                      ),
                    ),
                    const SizedBox(height: 8),
                    _SpecRow(
                      first: _Spec(
                        icon: Icons.place_outlined,
                        label: l10n.vehicleSpecCity,
                        value: vehicle.location,
                        palette: palette,
                      ),
                      second: _Spec(
                        icon: Icons.report_problem_outlined,
                        label: l10n.vehicleSpecCondition,
                        value: vehicle.conditionLabel,
                        palette: palette,
                      ),
                    ),
                  ],
                ),
              ),
            ),
            // **لوحُ المزايدة خارج التمرير، في قاع النافذة** بطلب المالك في ٩
            // سبتمبر ٢٠٢٦ على مثال v1: هو ما جاء العميلُ من أجله، وبقاؤه في
            // آخر عمودٍ منزلق يعني أن من لم يمرّر لا يراه أصلاً.
            _BidPanel(
              vehicle: vehicle,
              palette: palette,
              l10n: l10n,
              priceController: _price,
              // **معطَّلٌ بلا مبلغ**: زرٌّ يستجيب ولا يرسل شيئاً يُقرأ عطلاً،
              // وزرٌّ يرسل بلا مبلغٍ مزايدةٌ بالخطأ.
              onPlaceBid: _price.text.trim().isEmpty ? null : _placeBid,
              submitting:
                  ref.watch(placeBidControllerProvider(vehicle.id))
                      is PlaceBidSubmitting,
            ),
          ],
        ),
      ),
    );
  }
}

/// شريطُ النافذة: الاسمُ في جهة، وخمسةُ أزرارٍ في الأخرى — هيئةُ v1.
///
/// **وثلاثةٌ منها معطَّلة، ظاهرةً لا مخفيّة**: السابقُ والتالي يحتاجان قائمةَ
/// المركبات التي فُتحت النافذةُ منها، والكرتُ لا يعرف جيرانه — يعرف مركبته
/// وحدها. وزرٌّ معطَّلٌ باهتٌ يقول «ليس الآن»، وزرٌّ يستجيب ولا يفعل شيئاً
/// يُقرأ عطلاً. مفتوحٌ حتى تُمرَّر القائمة.
class _Header extends StatelessWidget {
  const _Header({
    required this.title,
    required this.palette,
    required this.onShare,
    required this.onFavourite,
    required this.isFavourite,
  });

  final String title;
  final HarajPalette palette;
  final VoidCallback onShare;
  final VoidCallback onFavourite;
  final bool isFavourite;

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsetsDirectional.fromSTEB(12, 8, 8, 6),
    child: Row(
      children: <Widget>[
        Icon(
          Icons.directions_car_filled_outlined,
          size: 17,
          color: palette.gold,
        ),
        const SizedBox(width: 6),
        Expanded(
          child: Text(
            title,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: TextStyle(
              fontFamily: HarajTheme.fontFamily,
              fontSize: 14,
              fontWeight: FontWeight.w700,
              color: palette.ink,
            ),
          ),
        ),
        _RoundButton(
          icon: isFavourite
              ? Icons.favorite_rounded
              : Icons.favorite_border_rounded,
          palette: palette,
          onTap: onFavourite,
        ),
        _RoundButton(
          icon: Icons.share_outlined,
          palette: palette,
          onTap: onShare,
        ),
        // **`chevron_right` للتالي و`chevron_left` للسابق** — والاتجاه يقلبهما
        // بنفسه في `Icon`، فلا يُكتب لهما عكسٌ يدويّ.
        const _RoundButton(icon: Icons.chevron_right_rounded, onTap: null),
        const _RoundButton(icon: Icons.chevron_left_rounded, onTap: null),
        _RoundButton(
          icon: Icons.close_rounded,
          palette: palette,
          onTap: () => Navigator.of(context).pop(),
        ),
      ],
    ),
  );
}

/// زرٌّ دائريٌّ صغير في شريط النافذة.
class _RoundButton extends StatelessWidget {
  const _RoundButton({required this.icon, required this.onTap, this.palette});

  final IconData icon;
  final VoidCallback? onTap;

  /// `null` للزرّ المعطَّل — يُرسم بالرمادي وحده.
  final HarajPalette? palette;

  @override
  Widget build(BuildContext context) {
    final theme = HarajPalette.of(context);
    final enabled = onTap != null;

    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 1),
      child: Material(
        color: enabled
            ? theme.gold.withValues(alpha: 0.14)
            : theme.inkMuted.withValues(alpha: 0.08),
        shape: const CircleBorder(),
        child: InkWell(
          onTap: onTap,
          customBorder: const CircleBorder(),
          child: Padding(
            padding: const EdgeInsets.all(6),
            child: Icon(
              icon,
              size: 16,
              color: enabled
                  ? theme.goldDeep
                  : theme.inkMuted.withValues(alpha: 0.55),
            ),
          ),
        ),
      ),
    );
  }
}

/// صفٌّ من خانتَي مواصفة.
///
/// **`Expanded` لكلٍّ منهما**: خانتان بعرض نصّهما تتركان بينهما فراغاً يتغيّر
/// مع كل مركبة، فيرقص العمودان بين الصفوف الثلاثة.
class _SpecRow extends StatelessWidget {
  const _SpecRow({required this.first, required this.second});

  final Widget first;
  final Widget second;

  @override
  Widget build(BuildContext context) => IntrinsicHeight(
    child: Row(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: <Widget>[
        Expanded(child: first),
        const SizedBox(width: 8),
        Expanded(child: second),
      ],
    ),
  );
}

/// خانةُ مواصفةٍ في النافذة: التسميةُ خافتةٌ فوق القيمة، والأيقونةُ في طرفها.
class _Spec extends StatelessWidget {
  const _Spec({
    required this.icon,
    required this.label,
    required this.value,
    required this.palette,
  });

  final IconData icon;
  final String label;
  final String value;
  final HarajPalette palette;

  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
    decoration: BoxDecoration(
      color: palette.pageBackground,
      borderRadius: BorderRadius.circular(11),
      border: Border.all(color: palette.gold.withValues(alpha: 0.35)),
    ),
    // **الأيقونةُ أوّلاً — أي يميناً في العربية** بطلب المالك في ٩ سبتمبر
    // ٢٠٢٦ على هيئة v1، والنصُّ بعدها يمتدّ إلى الطرف الآخر.
    child: Row(
      children: <Widget>[
        Container(
          padding: const EdgeInsets.all(5),
          decoration: BoxDecoration(
            color: palette.gold.withValues(alpha: 0.16),
            borderRadius: BorderRadius.circular(8),
          ),
          child: Icon(icon, size: 14, color: palette.goldDeep),
        ),
        const SizedBox(width: 7),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisAlignment: MainAxisAlignment.center,
            children: <Widget>[
              Text(
                label,
                maxLines: 1,
                style: TextStyle(
                  fontFamily: HarajTheme.fontFamily,
                  fontSize: 10,
                  fontWeight: FontWeight.w600,
                  color: palette.inkMuted,
                ),
              ),
              const SizedBox(height: 2),
              Text(
                value,
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
                style: TextStyle(
                  fontFamily: HarajTheme.fontFamily,
                  fontSize: 12,
                  fontWeight: FontWeight.w700,
                  color: palette.ink,
                  height: 1.25,
                ),
              ),
            ],
          ),
        ),
      ],
    ),
  );
}

/// لوحُ «تفاصيل المزايدة» — **ثابتٌ في قاع النافذة**، والبياناتُ تنزلق خلفه.
///
/// أربعُ خانات: الرسومُ الإداريّة والرسومُ مع الضريبة (كلاهما **من الخادم**)،
/// ثم السعرُ الذي يكتبه العميل والسعرُ مع الضريبة.
class _BidPanel extends StatelessWidget {
  const _BidPanel({
    required this.vehicle,
    required this.palette,
    required this.l10n,
    required this.priceController,
    required this.onPlaceBid,
    required this.submitting,
  });

  final VehicleSummary vehicle;
  final HarajPalette palette;
  final AppLocalizations l10n;
  final TextEditingController priceController;

  /// `null` حين لا مبلغَ مكتوب — الزرُّ معطَّل حينها.
  final VoidCallback? onPlaceBid;

  /// طلبٌ جارٍ: الزرُّ يدور ولا يقبل ضغطةً ثانية.
  final bool submitting;

  /// «السعر + الضريبة» من السعر المكتوب — **بحسابٍ صحيحٍ بالهللات**.
  ///
  /// **ولماذا يُحسب هنا و`Money` مصمَّمٌ بلا عمليات؟** المنعُ في المادة ٣-٢
  /// و١-٦ على **أرقام الدفتر**: كلُّ مبلغٍ يُعرض له قيدٌ يقابله، وأي قاعدةٍ
  /// تُحسب في الشاشة نسخةٌ ثانية تفترق عن الأصل. وهذا الرقمُ ليس منها — هو
  /// معاينةُ ما كتبه العميلُ للتوّ، لا قيدَ له ولا يُرسَل إلى أحد. وv1 تعرضه.
  ///
  /// **ونسبةُ الضريبة تُشتقّ ولا تُكتب**: `adminFeeWithVat ÷ adminFee` كما
  /// أرسلهما الخادم. و«١٥٪» مكتوبةً في التطبيق هي بعينها القاعدةُ الثانية
  /// التي يمنعها الدستور — تفترق عن الخادم في أوّل يومٍ تتغيّر فيه.
  ///
  /// **ولا `double` في المسار**: الهللةُ عددٌ صحيح، والقسمةُ `~/` بجبرِ نصفٍ
  /// للتقريب لأقرب هللة.
  String? get _priceWithVat {
    final price = _halalas(priceController.text);
    final fee = _halalas(vehicle.adminFee.amount);
    final feeWithVat = _halalas(vehicle.adminFeeWithVat.amount);
    if (price == null || fee == null || feeWithVat == null || fee == 0) {
      return null;
    }
    final total = (price * feeWithVat + fee ~/ 2) ~/ fee;
    return '${total ~/ 100}.${(total % 100).toString().padLeft(2, '0')}';
  }

  /// نسبةُ الضريبة كما تقولها أرقامُ الخادم — تُلحَق بالتسمية «(١٥٪)».
  ///
  /// **مشتقّةٌ لا مكتوبة**: `(withVat − fee) ÷ fee`. و«١٥٪» مكتوبةً في
  /// التطبيق قاعدةٌ ثانية تفترق عن الخادم في أوّل يومٍ تتغيّر فيه.
  /// و`null` حين لا تخرج النسبةُ عدداً صحيحاً — كسرٌ في تسميةٍ لا يفيد.
  String? get _vatNote {
    final fee = _halalas(vehicle.adminFee.amount);
    final feeWithVat = _halalas(vehicle.adminFeeWithVat.amount);
    if (fee == null || feeWithVat == null || fee == 0) return null;
    final difference = (feeWithVat - fee) * 100;
    if (difference % fee != 0) return null;
    return '(${difference ~/ fee}%)';
  }

  /// نصٌّ عشريٌّ بخانتين إلى هللات. `null` لما ليس عدداً.
  static int? _halalas(String raw) {
    final text = raw.trim();
    if (text.isEmpty) return null;
    final parts = text.split('.');
    if (parts.length > 2) return null;
    final riyals = int.tryParse(parts.first);
    if (riyals == null) return null;
    final fraction = parts.length == 2
        ? int.tryParse(parts[1].padRight(2, '0').substring(0, 2))
        : 0;
    if (fraction == null) return null;
    return riyals * 100 + fraction;
  }

  @override
  Widget build(BuildContext context) {
    final withVat = _priceWithVat;
    final vat = _vatNote;

    return Container(
      decoration: BoxDecoration(
        color: palette.pageBackground,
        // **حدٌّ علويٌّ وظلّ**: اللوحُ يقف فوق محتوىً يمرّ تحته، وبلا فاصلٍ
        // يُقرأ آخرَ العمود لا لوحاً ثابتاً.
        border: Border(
          top: BorderSide(color: palette.gold.withValues(alpha: 0.35)),
        ),
        boxShadow: <BoxShadow>[
          BoxShadow(
            color: palette.ink.withValues(alpha: 0.10),
            blurRadius: 10,
            offset: const Offset(0, -3),
          ),
        ],
      ),
      padding: const EdgeInsets.fromLTRB(14, 10, 14, 14),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: <Widget>[
          Row(
            children: <Widget>[
              Icon(Icons.gavel_rounded, size: 15, color: palette.gold),
              const SizedBox(width: 6),
              Text(
                l10n.vehicleBidDetails,
                style: TextStyle(
                  fontFamily: HarajTheme.fontFamily,
                  fontSize: 13,
                  fontWeight: FontWeight.w700,
                  color: palette.ink,
                ),
              ),
            ],
          ),
          const SizedBox(height: 9),
          IntrinsicHeight(
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: <Widget>[
                Expanded(
                  child: _MoneyBox(
                    label: l10n.vehicleAdminFee,
                    amount: vehicle.adminFee,
                    palette: palette,
                    emphasised: false,
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: _MoneyBox(
                    label: l10n.vehicleAdminFeeWithVat,
                    note: vat,
                    amount: vehicle.adminFeeWithVat,
                    palette: palette,
                    emphasised: true,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 8),
          IntrinsicHeight(
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: <Widget>[
                Expanded(
                  child: _PriceField(
                    label: l10n.vehiclePrice,
                    controller: priceController,
                    currency: vehicle.adminFee.currency,
                    palette: palette,
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: _MoneyBox(
                    label: l10n.vehiclePriceWithVat,
                    note: vat,
                    // **شرطةٌ قبل أن يُكتب سعر، لا صفر**: «٠ ر.س» جوابٌ عن
                    // سؤالٍ لم يُسأل بعد.
                    amount: withVat == null
                        ? null
                        : Money(
                            amount: withVat,
                            currency: vehicle.adminFee.currency,
                          ),
                    palette: palette,
                    emphasised: true,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 12),
          _EnterButton(
            label: l10n.bidSubmit,
            palette: palette,
            onTap: submitting ? null : onPlaceBid,
            busy: submitting,
          ),
          const SizedBox(height: 8),
          // **«الخادم يقرّر» مكتوبةٌ تحت الزرّ** كما كانت في الشاشة المحذوفة:
          // من يضغط يجب أن يعرف أن المبلغ طلبٌ لا نتيجة.
          Text(
            l10n.bidServerDecides,
            textAlign: TextAlign.center,
            style: TextStyle(
              fontFamily: HarajTheme.fontFamily,
              fontSize: 10.5,
              color: palette.inkMuted,
            ),
          ),
        ],
      ),
    );
  }
}

/// خانةُ السعر — الحقلُ الوحيد الذي يكتبه العميل في النافذة.
class _PriceField extends StatelessWidget {
  const _PriceField({
    required this.label,
    required this.controller,
    required this.currency,
    required this.palette,
  });

  final String label;
  final TextEditingController controller;
  final String currency;
  final HarajPalette palette;

  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
    decoration: BoxDecoration(
      color: palette.cardSurface,
      borderRadius: BorderRadius.circular(10),
      border: Border.all(color: palette.gold.withValues(alpha: 0.55)),
    ),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: <Widget>[
        Text(
          label,
          maxLines: 1,
          style: TextStyle(
            fontFamily: HarajTheme.fontFamily,
            fontSize: 10,
            fontWeight: FontWeight.w600,
            color: palette.inkMuted,
          ),
        ),
        TextField(
          controller: controller,
          // **`autofocus` لا**: لوحةُ المفاتيح تفتح فوق اللوح فور فتح
          // النافذة، فتُخفي ما جاء العميلُ ليقرأه.
          keyboardType: const TextInputType.numberWithOptions(decimal: true),
          // أرقامٌ ونقطةٌ عشريّة بخانتين لا أكثر: العملةُ تصل بخانتين، وحرفٌ
          // في مسارٍ ماليّ يجعل الحقل يقرأ عدداً حيث لا عدد.
          inputFormatters: <TextInputFormatter>[
            FilteringTextInputFormatter.allow(RegExp(r'[0-9.]')),
          ],
          textDirection: TextDirection.ltr,
          decoration: InputDecoration(
            isDense: true,
            border: InputBorder.none,
            contentPadding: EdgeInsets.zero,
            // تلميحٌ بخانتين: الحقلُ الفارغ بلا تلميحٍ لا يقول إنه حقل.
            hintText: '0.00',
            hintStyle: TextStyle(
              fontFamily: HarajTheme.fontFamily,
              fontSize: 14,
              fontWeight: FontWeight.w700,
              color: palette.inkMuted.withValues(alpha: 0.5),
            ),
            suffixText: currency,
            suffixStyle: TextStyle(
              fontFamily: HarajTheme.fontFamily,
              fontSize: 11,
              color: palette.inkMuted,
            ),
          ),
          style: TextStyle(
            fontFamily: HarajTheme.fontFamily,
            fontSize: 14,
            fontWeight: FontWeight.w700,
            color: palette.ink,
          ),
        ),
      ],
    ),
  );
}

class _MoneyBox extends StatelessWidget {
  const _MoneyBox({
    required this.label,
    required this.amount,
    required this.palette,
    required this.emphasised,
    this.note,
  });

  final String label;

  /// «(١٥٪)» بجانب التسمية، أو `null` حيث لا ضريبة في التسمية.
  final String? note;

  /// `null` قبل أن يُكتب سعر — تُعرض شرطةٌ لا صفر.
  final Money? amount;

  final HarajPalette palette;

  /// المجموعُ هو ما يدفعه العميل فعلاً، فيُبرز بأرضيّةٍ ذهبيّة خفيفة.
  final bool emphasised;

  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 9),
    decoration: BoxDecoration(
      color: emphasised
          ? Color.alphaBlend(
              palette.gold.withValues(alpha: 0.14),
              palette.cardSurface,
            )
          : palette.cardSurface,
      borderRadius: BorderRadius.circular(10),
      border: Border.all(
        color: palette.gold.withValues(alpha: emphasised ? 0.55 : 0.25),
      ),
    ),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        Text(
          note == null ? label : '$label $note',
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
          style: TextStyle(
            fontFamily: HarajTheme.fontFamily,
            fontSize: 10,
            fontWeight: FontWeight.w600,
            color: palette.inkMuted,
          ),
        ),
        const SizedBox(height: 3),
        // **`MoneyText` لا تنسيقٌ هنا**: المبلغ يُعرض كما وصل نصّاً، ولا
        // يُعاد حسابُه ولا تنسيقُه في الشاشة.
        if (amount case final Money money)
          MoneyText(
            money,
            style: TextStyle(
              fontFamily: HarajTheme.fontFamily,
              fontSize: 14,
              fontWeight: FontWeight.w700,
              color: emphasised ? palette.goldDeep : palette.ink,
            ),
          )
        else
          Text(
            '—',
            style: TextStyle(
              fontFamily: HarajTheme.fontFamily,
              fontSize: 14,
              fontWeight: FontWeight.w700,
              color: palette.inkMuted,
            ),
          ),
      ],
    ),
  );
}

/// زرُّ «دخول المزاد» — ذهبيٌّ ممتدّ، ينقل إلى صفحة المركبة.
class _EnterButton extends StatelessWidget {
  const _EnterButton({
    required this.label,
    required this.palette,
    required this.onTap,
    this.busy = false,
  });

  final String label;
  final HarajPalette palette;
  final VoidCallback? onTap;

  /// طلبٌ جارٍ — مؤشّرٌ مكان النصّ بنفس ارتفاع الزرّ، فلا ينكمش تحت الإصبع.
  final bool busy;

  @override
  Widget build(BuildContext context) => Material(
    borderRadius: BorderRadius.circular(11),
    clipBehavior: Clip.antiAlias,
    color: Colors.transparent,
    child: Ink(
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(11),
        gradient: LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: <Color>[palette.gold, palette.goldDeep],
        ),
      ),
      child: InkWell(
        onTap: onTap,
        child: SizedBox(
          height: 44,
          child: busy
              ? Center(
                  child: SizedBox.square(
                    dimension: 18,
                    child: CircularProgressIndicator(
                      strokeWidth: 2,
                      color: palette.heroBottom,
                    ),
                  ),
                )
              : Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: <Widget>[
                    Icon(
                      Icons.gavel_rounded,
                      size: 17,
                      color: palette.heroBottom,
                    ),
                    const SizedBox(width: 8),
                    Text(
                      label,
                      style: TextStyle(
                        fontFamily: HarajTheme.fontFamily,
                        fontSize: 15,
                        fontWeight: FontWeight.w700,
                        // شبه أسود على الذهبيّ لا أبيض: الأبيض على `#B8860B`
                        // نسبتُه ٣٫٣:١ وهي دون الحدّ، وهذا نحو ٧:١.
                        color: palette.heroBottom,
                      ),
                    ),
                  ],
                ),
        ),
      ),
    ),
  );
}

/// حوارٌ صغير في وسط الشاشة — جوابُ الخادم على المزايدة، قبولاً أو رفضاً.
///
/// **حوارٌ لا شريطُ رسالة**: الشريط يمرّ ويختفي ويظهر في قاع الشاشة بعيداً عن
/// موضع النظر، وجوابُ المزايدة خبرٌ على فعلٍ مقصود يستحقّ إقراراً بضغطة.
///
/// **وواحدٌ للجوابين**: نصُّه ولونُ أيقونته يفترقان، وبنيتُه واحدة — حوارانِ
/// متطابقان إلا في أيقونةٍ يفترقان عند أول تعديل (المادة ٤-٥).
class _NoticeDialog extends StatelessWidget {
  const _NoticeDialog({required this.message, required this.accepted});

  final String message;

  /// قبولٌ أم رفض — يقرّر الأيقونةَ ولونَها وحدهما.
  final bool accepted;

  @override
  Widget build(BuildContext context) {
    final palette = HarajPalette.of(context);
    // **أحمرُ الثيم للرفض لا لونٌ مكتوب**: الرفضُ حالةُ خطأ، ولونُها في
    // `ColorScheme` واحدٌ لكل الشاشات.
    final tint = accepted
        ? palette.goldDeep
        : Theme.of(context).colorScheme.error;

    return AlertDialog(
      backgroundColor: palette.cardSurface,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(18)),
      content: Column(
        mainAxisSize: MainAxisSize.min,
        children: <Widget>[
          Container(
            padding: const EdgeInsets.all(10),
            decoration: BoxDecoration(
              color: tint.withValues(alpha: 0.14),
              shape: BoxShape.circle,
            ),
            child: Icon(
              accepted ? Icons.check_rounded : Icons.info_outline_rounded,
              size: 28,
              color: tint,
            ),
          ),
          const SizedBox(height: 12),
          Text(
            message,
            textAlign: TextAlign.center,
            style: TextStyle(
              fontFamily: HarajTheme.fontFamily,
              fontSize: 14.5,
              fontWeight: FontWeight.w700,
              color: palette.ink,
              height: 1.45,
            ),
          ),
        ],
      ),
      actionsAlignment: MainAxisAlignment.center,
      actions: <Widget>[
        FilledButton(
          onPressed: () => Navigator.of(context).pop(),
          style: FilledButton.styleFrom(
            backgroundColor: palette.goldDeep,
            foregroundColor: Colors.white,
          ),
          child: Text(MaterialLocalizations.of(context).okButtonLabel),
        ),
      ],
    );
  }
}
