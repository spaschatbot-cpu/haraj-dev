import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../domain/common/failure.dart';
import '../../domain/profile/entities/customer_profile.dart';
import '../../l10n/generated/app_localizations.dart';
import '../common/failure_view.dart';
import 'company_profile_controller.dart';

/// ملف الشركة والعنوان الوطني (ZATCA).
///
/// **لا شرط اكتمال في الشاشة.** أي حقل «إلزامي» هنا يكون نسخة ثانية من قاعدة
/// لها تاريخ في الخادم: الشركات السابقة على العنوان الوطني معفاة إلى يوم يقرّره
/// المالك (T607). نموذج يفرض الإلزام بنفسه يمنع شركة قديمة من حفظ رقم هاتفها.
class CompanyProfileScreen extends ConsumerWidget {
  const CompanyProfileScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = AppLocalizations.of(context);
    final company = ref.watch(companyProfileControllerProvider);

    return Scaffold(
      appBar: AppBar(title: Text(l10n.companyTitle)),
      body: switch (company) {
        AsyncData(:final value) => _CompanyForm(company: value),
        AsyncError(:final error) => Center(
          child: FailureView(
            failure: error is Failure ? error : UnexpectedFailure(error),
            onRetry: () =>
                ref.read(companyProfileControllerProvider.notifier).refresh(),
          ),
        ),
        _ => const Center(child: CircularProgressIndicator()),
      },
    );
  }
}

class _CompanyForm extends ConsumerStatefulWidget {
  const _CompanyForm({required this.company});

  /// `null` = لا شركة بعد؛ النموذج يفتح فارغاً بتلميح الإنشاء.
  final CompanyProfile? company;

  @override
  ConsumerState<_CompanyForm> createState() => _CompanyFormState();
}

class _CompanyFormState extends ConsumerState<_CompanyForm> {
  late final Map<String, TextEditingController> _fields;
  bool _busy = false;
  Failure? _failure;

  @override
  void initState() {
    super.initState();
    final company = widget.company ?? const CompanyProfile.blank();
    _fields = {
      'name': TextEditingController(text: company.name),
      'representative_name': TextEditingController(
        text: company.representativeName,
      ),
      'commercial_register': TextEditingController(
        text: company.commercialRegister,
      ),
      'vat_number': TextEditingController(text: company.vatNumber),
      'building_number': TextEditingController(text: company.buildingNumber),
      'street': TextEditingController(text: company.street),
      'district': TextEditingController(text: company.district),
      'city': TextEditingController(text: company.city),
      'postal_code': TextEditingController(text: company.postalCode),
    };
  }

  @override
  void dispose() {
    for (final controller in _fields.values) {
      controller.dispose();
    }
    super.dispose();
  }

  String _value(String field) => _fields[field]!.text.trim();

  Future<void> _save() async {
    setState(() {
      _busy = true;
      _failure = null;
    });

    try {
      await ref
          .read(companyProfileControllerProvider.notifier)
          .save(
            CompanyProfile(
              name: _value('name'),
              representativeName: _value('representative_name'),
              commercialRegister: _value('commercial_register'),
              vatNumber: _value('vat_number'),
              buildingNumber: _value('building_number'),
              street: _value('street'),
              district: _value('district'),
              city: _value('city'),
              postalCode: _value('postal_code'),
              // الخادم يقرّر الاكتمال ويردّ به؛ ما نرسله هنا لا يُقرأ.
              isComplete: false,
            ),
          );
    } on Failure catch (failure) {
      if (mounted) setState(() => _failure = failure);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final theme = Theme.of(context);
    final company = widget.company;

    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        if (company == null)
          Text(l10n.companyCreateHint, style: theme.textTheme.bodyMedium)
        else
          Text(
            company.isComplete
                ? l10n.profileCompanyComplete
                : l10n.profileCompanyIncomplete,
            style: theme.textTheme.bodyMedium,
          ),
        const SizedBox(height: 16),

        _field('name', l10n.companyName),
        _field('representative_name', l10n.companyRepresentative),
        _field('commercial_register', l10n.companyRegister),
        _field('vat_number', l10n.companyVatNumber),

        const SizedBox(height: 16),
        Text(l10n.companyNationalAddress, style: theme.textTheme.titleMedium),
        const SizedBox(height: 8),

        _field('building_number', l10n.companyBuildingNumber),
        _field('street', l10n.companyStreet),
        _field('district', l10n.companyDistrict),
        _field('city', l10n.companyCity),
        _field('postal_code', l10n.companyPostalCode),

        const SizedBox(height: 24),

        // الرفض **فوق** الزرّ لا تحته: النموذج أطول من شاشة الجوال، ورسالة
        // أسفل الزرّ تظهر خارج الشاشة عند الضغط — فيبدو الحفظ وكأنه لم يفعل
        // شيئاً.
        if (_failure != null) ...[
          FailureView(failure: _failure!),
          const SizedBox(height: 16),
        ],

        if (_busy)
          const Center(child: CircularProgressIndicator())
        else
          FilledButton(onPressed: _save, child: Text(l10n.companySave)),
      ],
    );
  }

  Widget _field(String name, String label) => Padding(
    padding: const EdgeInsets.symmetric(vertical: 6),
    child: TextField(
      controller: _fields[name],
      decoration: InputDecoration(labelText: label),
    ),
  );
}
