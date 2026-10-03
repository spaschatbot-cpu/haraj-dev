import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app/theme.dart';
import '../../domain/common/failure.dart';
import '../../domain/profile/entities/customer_profile.dart';
import '../../l10n/generated/app_localizations.dart';
import '../common/failure_view.dart';
import '../common/haraj_app_bar.dart';
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

    // شفّافةٌ لتظهر الخلفيّةُ المتدرّجة المشتركة (`GlassBackdrop`) — الزجاج
    // الأبيض بطلب المالك (٣ أكتوبر ٢٠٢٦).
    return Scaffold(
      backgroundColor: Colors.transparent,
      appBar: HarajAppBar(title: l10n.companyTitle),
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
    final palette = HarajPalette.of(context);
    final company = widget.company;

    // تصميمُ الزجاج الأبيض بطلب المالك (٣ أكتوبر ٢٠٢٦): سطرُ الحالة شارةٌ
    // زجاجيّة، والحقولُ في بطاقتين — بياناتُ الشركة ثم العنوانُ الوطنيّ —
    // كي يُقرأ النموذجُ الطويل قسمين لا تسعَ خاناتٍ متتالية.
    return ListView(
      padding: EdgeInsets.fromLTRB(
        16,
        16,
        16,
        16 + MediaQuery.paddingOf(context).bottom,
      ),
      children: [
        _StatusNotice(
          text: company == null
              ? l10n.companyCreateHint
              : company.isComplete
              ? l10n.profileCompanyComplete
              : l10n.profileCompanyIncomplete,
          complete: company?.isComplete ?? false,
        ),
        const SizedBox(height: 14),

        _GlassCard(
          icon: Icons.business_rounded,
          title: l10n.companyTitle,
          children: <Widget>[
            _field('name', l10n.companyName, palette),
            _field('representative_name', l10n.companyRepresentative, palette),
            _field('commercial_register', l10n.companyRegister, palette),
            _field('vat_number', l10n.companyVatNumber, palette),
          ],
        ),
        const SizedBox(height: 14),

        _GlassCard(
          icon: Icons.location_on_outlined,
          title: l10n.companyNationalAddress,
          children: <Widget>[
            _field('building_number', l10n.companyBuildingNumber, palette),
            _field('street', l10n.companyStreet, palette),
            _field('district', l10n.companyDistrict, palette),
            _field('city', l10n.companyCity, palette),
            _field('postal_code', l10n.companyPostalCode, palette),
          ],
        ),

        const SizedBox(height: 20),

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
          FilledButton(
            onPressed: _save,
            style: FilledButton.styleFrom(
              backgroundColor: palette.gold,
              foregroundColor: Colors.white,
              minimumSize: const Size.fromHeight(50),
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(14),
              ),
              textStyle: const TextStyle(
                fontFamily: HarajTheme.fontFamily,
                fontWeight: FontWeight.w700,
                fontSize: 15,
              ),
            ),
            child: Text(l10n.companySave),
          ),
      ],
    );
  }

  Widget _field(String name, String label, HarajPalette palette) {
    OutlineInputBorder edge(Color colour, [double width = 1]) =>
        OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: BorderSide(color: colour, width: width),
        );
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: TextField(
        controller: _fields[name],
        style: TextStyle(
          fontFamily: HarajTheme.fontFamily,
          fontSize: 15,
          color: palette.ink,
        ),
        // خانةٌ زجاجيّة: مملوءةٌ بسطح البطاقة، وحدُّها رفيع، وتزرقّ عند
        // التركيز — على مقاس خانات شاشة الدخول.
        decoration: InputDecoration(
          labelText: label,
          labelStyle: TextStyle(
            fontFamily: HarajTheme.fontFamily,
            color: palette.inkMuted,
          ),
          filled: true,
          fillColor: palette.cardSurface,
          contentPadding: const EdgeInsets.symmetric(
            horizontal: 16,
            vertical: 14,
          ),
          border: edge(palette.navInactive),
          enabledBorder: edge(palette.navInactive),
          focusedBorder: edge(palette.gold, 1.4),
        ),
      ),
    );
  }
}

/// بطاقةُ قسمٍ زجاجيّة: رأسٌ بأيقونةٍ زرقاء في مربّعٍ مدوّر، ثم خيطٌ رفيع، ثم
/// الحقول. خاصّةٌ بالملفّ لا مشتركة — الأجزاءُ المشتركة يحرّرها غيرُ هذه الشاشة
/// الآن (٣ أكتوبر ٢٠٢٦).
class _GlassCard extends StatelessWidget {
  const _GlassCard({
    required this.icon,
    required this.title,
    required this.children,
  });

  final IconData icon;
  final String title;
  final List<Widget> children;

  @override
  Widget build(BuildContext context) {
    final palette = HarajPalette.of(context);
    return Container(
      padding: const EdgeInsets.fromLTRB(16, 16, 16, 10),
      decoration: BoxDecoration(
        color: palette.cardSurface,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: palette.navInactive.withValues(alpha: 0.7)),
        boxShadow: <BoxShadow>[
          BoxShadow(
            color: palette.ink.withValues(alpha: 0.05),
            blurRadius: 16,
            offset: const Offset(0, 6),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: <Widget>[
          Row(
            children: <Widget>[
              Container(
                width: 36,
                height: 36,
                alignment: Alignment.center,
                decoration: BoxDecoration(
                  color: palette.gold.withValues(alpha: 0.08),
                  borderRadius: BorderRadius.circular(10),
                ),
                child: Icon(icon, size: 19, color: palette.gold),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Text(
                  title,
                  style: TextStyle(
                    fontFamily: HarajTheme.fontFamily,
                    fontSize: 16,
                    fontWeight: FontWeight.w700,
                    color: palette.ink,
                  ),
                ),
              ),
            ],
          ),
          Padding(
            padding: const EdgeInsets.fromLTRB(0, 14, 0, 8),
            child: Divider(
              height: 1,
              color: palette.navInactive.withValues(alpha: 0.7),
            ),
          ),
          ...children,
        ],
      ),
    );
  }
}

/// سطرُ حالة الملفّ أعلى النموذج — مكتملٌ أم ناقصٌ أم لم يُنشأ بعد. والحالةُ
/// جوابُ الخادم (`isComplete`) لا حكمُ الشاشة؛ هنا تُعرض فقط.
class _StatusNotice extends StatelessWidget {
  const _StatusNotice({required this.text, required this.complete});

  final String text;
  final bool complete;

  @override
  Widget build(BuildContext context) {
    final palette = HarajPalette.of(context);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
      decoration: BoxDecoration(
        color: palette.cardSurface,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: palette.gold.withValues(alpha: 0.25)),
      ),
      child: Row(
        children: <Widget>[
          Icon(
            complete ? Icons.verified_outlined : Icons.info_outline_rounded,
            size: 20,
            color: palette.gold,
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              text,
              style: TextStyle(
                fontFamily: HarajTheme.fontFamily,
                fontSize: 13.5,
                height: 1.5,
                color: palette.ink,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
