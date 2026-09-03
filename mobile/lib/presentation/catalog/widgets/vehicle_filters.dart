import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../../../domain/catalog/entities/vehicle_query.dart';
import '../../../l10n/generated/app_localizations.dart';

/// حقول البحث والترشيح — **تجمع المعايير فقط**، ولا تطبّقها.
///
/// الحقول هنا هي بعينها مُعاملات الاستعلام التي يعلنها العقد
/// (`search`، `make`، `year_from`، `year_to`) — وهي نفسها التي يرسلها الويب في
/// `web/features/catalog/VehicleFilters.tsx`. ترشيحٌ يحتاجه التطبيق ولا يوفّره
/// العقد يُضاف إلى العقد فيرثه الاثنان، أو لا يُضاف.
class VehicleFilters extends StatefulWidget {
  const VehicleFilters({required this.query, required this.onApply, super.key});

  final VehicleQuery query;
  final void Function(VehicleQuery query) onApply;

  @override
  State<VehicleFilters> createState() => _VehicleFiltersState();
}

class _VehicleFiltersState extends State<VehicleFilters> {
  late final TextEditingController _search = TextEditingController(
    text: widget.query.search ?? '',
  );
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
    _search.dispose();
    _make.dispose();
    _yearFrom.dispose();
    _yearTo.dispose();
    super.dispose();
  }

  void _apply() => widget.onApply(
    VehicleQuery(
      search: _search.text.trim(),
      make: _make.text.trim(),
      // `int.tryParse` لا `double`: سنة الصنع عددٌ صحيح، ولا شيء في هذا النموذج
      // مبلغٌ أصلاً (المادة ٣-٢).
      yearFrom: int.tryParse(_yearFrom.text.trim()),
      yearTo: int.tryParse(_yearTo.text.trim()),
    ),
  );

  void _clear() {
    _search.clear();
    _make.clear();
    _yearFrom.clear();
    _yearTo.clear();
    widget.onApply(const VehicleQuery());
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);

    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 12, 16, 0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: <Widget>[
          TextField(
            controller: _search,
            textInputAction: TextInputAction.search,
            onSubmitted: (_) => _apply(),
            decoration: InputDecoration(
              hintText: l10n.searchHint,
              prefixIcon: const Icon(Icons.search),
              border: const OutlineInputBorder(),
            ),
          ),
          const SizedBox(height: 8),
          Row(
            children: <Widget>[
              Expanded(
                flex: 2,
                child: TextField(
                  controller: _make,
                  onSubmitted: (_) => _apply(),
                  decoration: InputDecoration(
                    labelText: l10n.filterMake,
                    border: const OutlineInputBorder(),
                  ),
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: _YearField(l10n.filterYearFrom, _yearFrom, _apply),
              ),
              const SizedBox(width: 8),
              Expanded(child: _YearField(l10n.filterYearTo, _yearTo, _apply)),
            ],
          ),
          const SizedBox(height: 8),
          // `Wrap` لا `Row`: الزرّان بنصّيهما العربيين أعرض من سطر جوال ضيّق،
          // و`Row` تقصّ «إزالة الترشيح» فيبقى العميل أمام نتائج لا يعرف كيف
          // يخرج منها.
          Wrap(
            spacing: 12,
            runSpacing: 8,
            children: <Widget>[
              FilledButton(onPressed: _apply, child: Text(l10n.filterApply)),
              if (widget.query.isFiltered)
                TextButton(onPressed: _clear, child: Text(l10n.filterClear)),
            ],
          ),
        ],
      ),
    );
  }
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
    ),
  );
}
