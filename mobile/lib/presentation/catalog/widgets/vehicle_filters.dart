import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../../../app/theme.dart';
import '../../../domain/catalog/entities/auction_phase.dart';
import '../../../domain/catalog/entities/vehicle_feed.dart';
import '../../../domain/catalog/entities/vehicle_query.dart';
import '../../../l10n/generated/app_localizations.dart';

/// حقل البحث — **وحده في الشاشة**، وبقيّةُ المعايير خلف زرّ.
///
/// البحث بالنصّ هو ما يفعله تسعةٌ من عشرة، والماركةُ والسنتان ما يفعله العاشر.
/// وكانت الأربعة معروضةً في صفَّين فوق القائمة، فيأكلان من الشاشة كرتاً ونصفاً
/// قبل أن يُرى أول سيّارة.
class VehicleSearchField extends StatefulWidget {
  const VehicleSearchField({
    required this.search,
    required this.onSubmitted,
    super.key,
  });

  /// النصّ القائم في المعايير. يُقرأ مرّةً عند البناء الأول: من كتب «كامري»
  /// ثم بدّل التبويب يجب أن يجد كلمته مكتوبةً كما تركها.
  final String? search;

  final void Function(String search) onSubmitted;

  @override
  State<VehicleSearchField> createState() => _VehicleSearchFieldState();
}

class _VehicleSearchFieldState extends State<VehicleSearchField> {
  late final TextEditingController _controller = TextEditingController(
    text: widget.search ?? '',
  );

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final palette = HarajPalette.of(context);
    final theme = Theme.of(context);

    return TextField(
      controller: _controller,
      textInputAction: TextInputAction.search,
      onSubmitted: widget.onSubmitted,
      style: theme.textTheme.bodyMedium?.copyWith(color: palette.ink),
      decoration: InputDecoration(
        hintText: l10n.searchHint,
        hintStyle: theme.textTheme.bodyMedium?.copyWith(
          color: palette.inkMuted,
        ),
        filled: true,
        fillColor: palette.cardSurface,
        // **`suffixIcon` لا `prefixIcon`:** البادئة في RTL تُرسم على اليمين
        // حيث يبدأ النصّ، فتزاحم أول حرفٍ يكتبه. والعدسة في الطرف الفارغ.
        suffixIcon: IconButton(
          icon: Icon(Icons.search_rounded, color: palette.gold),
          tooltip: l10n.searchHint,
          onPressed: () => widget.onSubmitted(_controller.text),
        ),
        isDense: true,
        // **١١ رأسياً لا ١٤**: الحقلُ صار داخل شريحةٍ ثابتة ارتفاعُها ٤٨،
        // و١٤+١٤+سطرٌ بحجم ١٤ تبلغ الثمانيةَ والأربعين بالضبط — فتفيض عند
        // أول جهازٍ يكبّر خطّه.
        contentPadding: const EdgeInsets.symmetric(
          horizontal: 20,
          vertical: 11,
        ),
        border: _border(palette.gold.withValues(alpha: 0.30)),
        enabledBorder: _border(palette.gold.withValues(alpha: 0.30)),
        focusedBorder: _border(palette.gold, width: 1.4),
      ),
    );
  }

  /// **نصفُ القطر ١٣ لا ٣٠** بطلب المالك في ٩ سبتمبر ٢٠٢٦: الثلاثون تُقصّ
  /// الحافّةَ كبسولةً كاملة، ومفتاحُ الأطوار تحته حوضٌ نصفُ قطره ١٣ — فكان
  /// الاثنان شكلين مختلفين في كتلةٍ واحدة.
  OutlineInputBorder _border(Color colour, {double width = 1}) =>
      OutlineInputBorder(
        borderRadius: BorderRadius.circular(13),
        borderSide: BorderSide(color: colour, width: width),
      );
}

/// زرّ الفرز والتصفية — يفتح ورقةً فيها الطور والماركة والسنتان.
///
/// **الطور داخل الورقة لا تبويباتٍ فوق القائمة.** كان شريطَ تبويباتٍ ثالثاً
/// أسفل الهيدر، وحذفُه كان سيحذف معه `?phase=` من العنوان — والرابطُ المشارَك
/// والإشعارُ يفتحان تبويبهما به (H6). فبقي في العنوان كما هو، وانتقل مقبضُه
/// إلى هنا: نفس المسار، بمساحةٍ أقلّ.
class VehicleFiltersButton extends StatelessWidget {
  const VehicleFiltersButton({
    required this.query,
    required this.phase,
    required this.counts,
    required this.onApply,
    required this.onPhase,
    super.key,
  });

  final VehicleQuery query;

  /// الطور المعروض، أو `null` في قائمة مزادٍ بعينه.
  ///
  /// **الطور ليس ترشيحاً هناك:** المزاد معروفٌ وطورُه معه، وسؤال «أي طور؟»
  /// في قائمة مزادٍ واحد سؤالٌ عن شيءٍ محسوم — واختيارُ طورٍ آخر فيه كان
  /// سينقل العميل خارج المزاد الذي فتحه. فتغيب الخانات الثلاث من الورقة،
  /// وتبقى الماركة والسنتان.
  final AuctionPhase? phase;

  /// `null` قبل وصول أول ردّ: الطور يظهر باسمه بلا رقم.
  ///
  /// **لا صفر مكانه.** «منتهي (٠)» جوابٌ لم يقله أحد، ومن قرأه لن يضغطه أصلاً.
  /// الاسم وحده يقول «لا أعرف بعد»، وهو الصدق المتاح.
  final PhaseCounts? counts;

  final void Function(VehicleQuery query) onApply;
  final void Function(AuctionPhase phase)? onPhase;

  Future<void> _open(BuildContext context) async {
    await showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (sheetContext) => _FiltersSheet(
        query: query,
        phase: phase,
        counts: counts,
        onApply: onApply,
        onPhase: onPhase,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final palette = HarajPalette.of(context);

    return DecoratedBox(
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topRight,
          end: Alignment.bottomLeft,
          colors: <Color>[palette.pillTop, palette.pillBottom],
        ),
        borderRadius: BorderRadius.circular(22),
      ),
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: () => _open(context),
          borderRadius: BorderRadius.circular(22),
          splashColor: palette.goldMuted,
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 9),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: <Widget>[
                Icon(Icons.gavel_rounded, size: 15, color: palette.goldOnDark),
                const SizedBox(width: 6),
                Text(
                  l10n.homeSortAndFilter,
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 12,
                    fontWeight: FontWeight.w700,
                    fontFamily: HarajTheme.fontFamily,
                  ),
                ),
                // نقطةٌ ذهبيّة حين يكون ترشيحٌ قائماً: بدونها لا شيء في الشاشة
                // يقول إن النتائج مُضيَّقة، فيقرأ العميل «لا نتائج» على أنها
                // خبرٌ عن المزاد وهي خبرٌ عن بحثه.
                if (query.isFiltered) ...<Widget>[
                  const SizedBox(width: 6),
                  Container(
                    width: 6,
                    height: 6,
                    decoration: BoxDecoration(
                      color: palette.goldOnDark,
                      shape: BoxShape.circle,
                    ),
                  ),
                ],
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _FiltersSheet extends StatefulWidget {
  const _FiltersSheet({
    required this.query,
    required this.phase,
    required this.counts,
    required this.onApply,
    required this.onPhase,
  });

  final VehicleQuery query;
  final AuctionPhase? phase;
  final PhaseCounts? counts;
  final void Function(VehicleQuery query) onApply;
  final void Function(AuctionPhase phase)? onPhase;

  @override
  State<_FiltersSheet> createState() => _FiltersSheetState();
}

class _FiltersSheetState extends State<_FiltersSheet> {
  late final TextEditingController _make = TextEditingController(
    text: widget.query.make ?? '',
  );
  late final TextEditingController _yearFrom = TextEditingController(
    text: widget.query.yearFrom?.toString() ?? '',
  );
  late final TextEditingController _yearTo = TextEditingController(
    text: widget.query.yearTo?.toString() ?? '',
  );

  @override
  void dispose() {
    _make.dispose();
    _yearFrom.dispose();
    _yearTo.dispose();
    super.dispose();
  }

  /// المعايير تُطبَّق **والبحثُ يبقى كما هو**: من كتب «كامري» ثم فتح الورقة
  /// ليحدّد السنة لا يقصد أن يمحو كلمته.
  void _apply() {
    widget.onApply(
      VehicleQuery(
        search: widget.query.search,
        make: _make.text.trim(),
        // `int.tryParse` لا `double`: سنة الصنع عددٌ صحيح، ولا شيء في هذا
        // النموذج مبلغٌ أصلاً (المادة ٣-٢).
        yearFrom: int.tryParse(_yearFrom.text.trim()),
        yearTo: int.tryParse(_yearTo.text.trim()),
      ),
    );
    Navigator.of(context).pop();
  }

  void _clear() {
    widget.onApply(const VehicleQuery());
    Navigator.of(context).pop();
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final palette = HarajPalette.of(context);
    final theme = Theme.of(context);

    return Padding(
      // حشوةُ لوحة المفاتيح: بدونها تختفي خانتا السنة تحتها فور لمسهما.
      padding: EdgeInsets.only(bottom: MediaQuery.viewInsetsOf(context).bottom),
      child: Container(
        decoration: BoxDecoration(
          color: palette.pageBackground,
          borderRadius: const BorderRadius.vertical(top: Radius.circular(26)),
        ),
        padding: const EdgeInsets.fromLTRB(20, 10, 20, 20),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Center(
              child: Container(
                width: 42,
                height: 4,
                decoration: BoxDecoration(
                  color: palette.inkMuted.withValues(alpha: 0.45),
                  borderRadius: BorderRadius.circular(2),
                ),
              ),
            ),
            const SizedBox(height: 16),
            Text(
              l10n.homeSortAndFilter,
              style: theme.textTheme.titleMedium?.copyWith(
                color: palette.ink,
                fontWeight: FontWeight.w700,
              ),
            ),
            const SizedBox(height: 16),
            if (widget.phase case final AuctionPhase current) ...<Widget>[
              Text(
                l10n.filterPhase,
                style: theme.textTheme.labelMedium?.copyWith(
                  color: palette.inkMuted,
                ),
              ),
              const SizedBox(height: 8),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: <Widget>[
                  for (final option in AuctionPhase.tabs)
                    _PhaseChip(
                      selected: option == current,
                      label: widget.counts == null
                          ? _phaseLabel(l10n, option)
                          : l10n.homeTabWithCount(
                              _phaseLabel(l10n, option),
                              widget.counts!.of(option),
                            ),
                      onTap: () {
                        // الطور تنقّلٌ في الموجّه لا حالةٌ هنا: العنوان هو
                        // مصدره، والشاشة تُعاد بناؤها منه. لو بُدّل هنا لصار
                        // له مصدران يفترقان عند أول رجوعٍ بزرّ النظام.
                        Navigator.of(context).pop();
                        widget.onPhase?.call(option);
                      },
                      palette: palette,
                    ),
                ],
              ),
              const SizedBox(height: 18),
            ],
            TextField(
              controller: _make,
              onSubmitted: (_) => _apply(),
              decoration: InputDecoration(
                labelText: l10n.filterMake,
                border: const OutlineInputBorder(),
                filled: true,
                fillColor: palette.cardSurface,
              ),
            ),
            const SizedBox(height: 10),
            Row(
              children: <Widget>[
                Expanded(
                  child: _YearField(l10n.filterYearFrom, _yearFrom, _apply),
                ),
                const SizedBox(width: 10),
                Expanded(child: _YearField(l10n.filterYearTo, _yearTo, _apply)),
              ],
            ),
            const SizedBox(height: 18),
            Row(
              children: <Widget>[
                Expanded(
                  child: FilledButton(
                    onPressed: _apply,
                    style: FilledButton.styleFrom(
                      backgroundColor: palette.pillTop,
                      foregroundColor: Colors.white,
                      padding: const EdgeInsets.symmetric(vertical: 14),
                    ),
                    child: Text(l10n.filterApply),
                  ),
                ),
                if (widget.query.isFiltered) ...<Widget>[
                  const SizedBox(width: 10),
                  TextButton(
                    onPressed: _clear,
                    style: TextButton.styleFrom(
                      foregroundColor: palette.inkMuted,
                    ),
                    child: Text(l10n.filterClear),
                  ),
                ],
              ],
            ),
          ],
        ),
      ),
    );
  }

  String _phaseLabel(AppLocalizations l10n, AuctionPhase phase) =>
      switch (phase) {
        AuctionPhase.upcoming => l10n.homeTabUpcoming,
        AuctionPhase.active => l10n.homeTabActive,
        AuctionPhase.ended => l10n.homeTabEnded,
        AuctionPhase.unknown => l10n.homeTabActive,
      };
}

class _PhaseChip extends StatelessWidget {
  const _PhaseChip({
    required this.selected,
    required this.label,
    required this.onTap,
    required this.palette,
  });

  final bool selected;
  final String label;
  final VoidCallback onTap;
  final HarajPalette palette;

  @override
  Widget build(BuildContext context) => Semantics(
    selected: selected,
    button: true,
    child: Material(
      color: selected ? palette.gold : palette.cardSurface,
      borderRadius: BorderRadius.circular(20),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(20),
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 9),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(20),
            border: Border.all(
              color: selected
                  ? palette.gold
                  : palette.inkMuted.withValues(alpha: 0.35),
            ),
          ),
          child: Text(
            label,
            style: TextStyle(
              // أبيضُ على الذهبيّ الغائر، وبنّيٌّ على الأبيض: لونٌ واحد
              // للحالتين يسقط في إحداهما دون حدّ التباين.
              color: selected ? Colors.white : palette.ink,
              fontSize: 12,
              fontWeight: FontWeight.w700,
              fontFamily: HarajTheme.fontFamily,
            ),
          ),
        ),
      ),
    ),
  );
}

class _YearField extends StatelessWidget {
  const _YearField(this.label, this.controller, this.onSubmitted);

  final String label;
  final TextEditingController controller;
  final VoidCallback onSubmitted;

  @override
  Widget build(BuildContext context) => TextField(
    controller: controller,
    keyboardType: TextInputType.number,
    inputFormatters: <TextInputFormatter>[
      FilteringTextInputFormatter.digitsOnly,
    ],
    onSubmitted: (_) => onSubmitted(),
    decoration: InputDecoration(
      labelText: label,
      border: const OutlineInputBorder(),
      filled: true,
      fillColor: HarajPalette.of(context).cardSurface,
    ),
  );
}
