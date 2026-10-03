/// أكمل تسجيلك — ما بعد الرمز لكلّ حسابٍ ينقصه شيء، جديداً كان أو منقولاً ناقصاً.
///
/// طلبُ المالك (٢٨ سبتمبر ٢٠٢٦): «أوّل حاجة أدخل الرقم، بعد كده الـverification،
/// بعد كده يعمل detection: موجود ⇐ يدخل على طول، ناقص ⇐ يكمّل البيانات، جديد ⇐
/// ينشئ حسابه بكلّ الـdata… ما تعمليش تسجيل ناقص داتا» — وطلبَ الخطواتِ نفسَها
/// في التطبيق كما في الموقع (`web/app/sign-in/complete/page.tsx`).
///
/// **والبناءُ بناءُ v1** (`log2/index.php`): جوال ← رمز ← **نوعُ الحساب** ←
/// **البيانات** ← المستندات. والحقولُ حقولُه (`ClientProfileGuard`):
///
/// * الفرد: الاسمُ الكامل، ورقمُ الهويّة، والمدينة.
/// * الشركة: اسمُ المفوّض، والهويّة، والمنشأة، والسجلّ، والرقمُ الضريبيّ،
///   والعنوانُ الوطنيُّ كلُّه.
///
/// و«ما ينقص» جوابُ الخادم لا حسابُ الشاشة (`CustomerProfile.registrationMissing`)
/// — الشاشةُ تعرضه وتُرسل، ثمّ تسأل ثانيةً. وقواعدُ الصيغة (اسمٌ بلا أرقام،
/// سجلٌّ من عشرة…) عند الخادم أيضاً، وأخطاؤه تقع تحت خاناتها من `detail`.
library;

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../app/providers.dart';
import '../../app/router.dart';
import '../../app/theme.dart';
import '../../domain/common/failure.dart';
import '../../domain/profile/entities/customer_profile.dart';
import '../../l10n/generated/app_localizations.dart';
import '../common/failure_view.dart';
import '../common/haraj_app_bar.dart';
import '../profile/profile_controller.dart';

enum _AccountKind { individual, company }

class CompleteRegistrationScreen extends ConsumerWidget {
  const CompleteRegistrationScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = AppLocalizations.of(context);
    final profile = ref.watch(profileControllerProvider);

    // **تصميمُ الزجاج الأبيض بطلب المالك (٣ أكتوبر ٢٠٢٦)**: أرضيّةٌ شفّافة
    // فوق `GlassBackdrop` العامّة، والخطوتان بطاقاتٌ بيضاء — لا ورقةٌ رماديّة
    // وبطاقاتُ Material الافتراضيّة.
    return Scaffold(
      backgroundColor: Colors.transparent,
      appBar: HarajAppBar(title: l10n.registrationCompleteTitle),
      body: switch (profile) {
        AsyncData(:final value) => _Flow(profile: value.value),
        AsyncError(:final error) => Center(
          child: FailureView(
            failure: error is Failure ? error : UnexpectedFailure(error),
            onRetry: () =>
                ref.read(profileControllerProvider.notifier).refresh(),
          ),
        ),
        _ => const Center(child: CircularProgressIndicator()),
      },
    );
  }
}

class _Flow extends ConsumerStatefulWidget {
  const _Flow({required this.profile});

  final CustomerProfile profile;

  @override
  ConsumerState<_Flow> createState() => _FlowState();
}

class _FlowState extends ConsumerState<_Flow> {
  _AccountKind? _kind;

  /// حسابٌ جديد: بلا اسمٍ وبلا منشأة. وحدَه يُسأل «فردٌ أم شركة؟» — ومن جاء
  /// ناقصاً من v1 يعرف نوعَه، وسؤالُه وهو شركةٌ منذ سنتين لا جوابَ له إلا الضجر.
  bool get _fresh =>
      widget.profile.fullName.trim().isEmpty &&
      !widget.profile.hasCompanyProfile;

  @override
  void initState() {
    super.initState();
    if (!_fresh) {
      _kind = widget.profile.accountType == 'company'
          ? _AccountKind.company
          : _AccountKind.individual;
    }
  }

  @override
  Widget build(BuildContext context) {
    final kind = _kind;
    if (kind == null) {
      return _TypeStep(onChosen: (chosen) => setState(() => _kind = chosen));
    }
    return _DetailsStep(
      profile: widget.profile,
      kind: kind,
      onChangeKind: _fresh ? () => setState(() => _kind = null) : null,
    );
  }
}

class _TypeStep extends StatelessWidget {
  const _TypeStep({required this.onChosen});

  final ValueChanged<_AccountKind> onChosen;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final palette = HarajPalette.of(context);
    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 20, 16, 24),
      children: <Widget>[
        Text(
          l10n.registrationTypeTitle,
          style: TextStyle(
            fontFamily: HarajTheme.fontFamily,
            fontSize: 20,
            fontWeight: FontWeight.w700,
            color: palette.ink,
          ),
        ),
        const SizedBox(height: 6),
        Text(
          l10n.registrationTypeSubtitle,
          style: TextStyle(
            fontFamily: HarajTheme.fontFamily,
            fontSize: 13.5,
            height: 1.5,
            color: palette.inkMuted,
          ),
        ),
        const SizedBox(height: 16),
        _TypeCard(
          icon: Icons.person_outline,
          title: l10n.registrationIndividual,
          hint: l10n.registrationIndividualHint,
          onTap: () => onChosen(_AccountKind.individual),
        ),
        const SizedBox(height: 12),
        _TypeCard(
          icon: Icons.apartment_outlined,
          title: l10n.registrationCompany,
          hint: l10n.registrationCompanyHint,
          onTap: () => onChosen(_AccountKind.company),
        ),
      ],
    );
  }
}

class _TypeCard extends StatelessWidget {
  const _TypeCard({
    required this.icon,
    required this.title,
    required this.hint,
    required this.onTap,
  });

  final IconData icon;
  final String title;
  final String hint;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final palette = HarajPalette.of(context);
    return _Card(
      padding: EdgeInsets.zero,
      child: Material(
        type: MaterialType.transparency,
        child: InkWell(
          onTap: onTap,
          borderRadius: BorderRadius.circular(_Card.radius),
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Row(
              children: <Widget>[
                _IconTile(icon: icon, size: 46),
                const SizedBox(width: 14),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      Text(
                        title,
                        style: TextStyle(
                          fontFamily: HarajTheme.fontFamily,
                          fontSize: 15.5,
                          fontWeight: FontWeight.w700,
                          color: palette.ink,
                        ),
                      ),
                      const SizedBox(height: 3),
                      Text(
                        hint,
                        style: TextStyle(
                          fontFamily: HarajTheme.fontFamily,
                          fontSize: 12.5,
                          height: 1.45,
                          color: palette.inkMuted,
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(width: 8),
                Icon(Icons.chevron_left_rounded, color: palette.inkMuted),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

/// بطاقةٌ بيضاء زجاجيّة بحدٍّ فاتح — وعاءُ شاشة الدخول نفسُه.
class _Card extends StatelessWidget {
  const _Card({required this.child, this.padding = const EdgeInsets.all(16)});

  static const double radius = 20;

  final Widget child;
  final EdgeInsetsGeometry padding;

  @override
  Widget build(BuildContext context) {
    final palette = HarajPalette.of(context);
    return Container(
      padding: padding,
      decoration: BoxDecoration(
        color: palette.cardSurface,
        borderRadius: BorderRadius.circular(radius),
        border: Border.all(color: palette.navInactive.withValues(alpha: 0.7)),
        boxShadow: <BoxShadow>[
          BoxShadow(
            color: palette.ink.withValues(alpha: 0.05),
            blurRadius: 16,
            offset: const Offset(0, 6),
          ),
        ],
      ),
      child: child,
    );
  }
}

class _IconTile extends StatelessWidget {
  const _IconTile({required this.icon, this.size = 34});

  final IconData icon;
  final double size;

  @override
  Widget build(BuildContext context) {
    final palette = HarajPalette.of(context);
    return Container(
      width: size,
      height: size,
      decoration: BoxDecoration(
        color: palette.gold.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(size > 40 ? 14 : 12),
      ),
      child: Icon(icon, size: size * 0.52, color: palette.gold),
    );
  }
}

/// عنوانُ بطاقةٍ: أيقونةٌ في مربّعها ثمّ الاسم — كرأس بطاقة الدخول.
class _CardHeader extends StatelessWidget {
  const _CardHeader({required this.icon, required this.title, this.trailing});

  final IconData icon;
  final String title;
  final Widget? trailing;

  @override
  Widget build(BuildContext context) {
    final palette = HarajPalette.of(context);
    return Row(
      children: <Widget>[
        _IconTile(icon: icon),
        const SizedBox(width: 12),
        Expanded(
          child: Text(
            title,
            style: TextStyle(
              fontFamily: HarajTheme.fontFamily,
              fontSize: 15,
              fontWeight: FontWeight.w700,
              color: palette.ink,
            ),
          ),
        ),
        ?trailing,
      ],
    );
  }
}

class _DetailsStep extends ConsumerStatefulWidget {
  const _DetailsStep({
    required this.profile,
    required this.kind,
    required this.onChangeKind,
  });

  final CustomerProfile profile;
  final _AccountKind kind;
  final VoidCallback? onChangeKind;

  @override
  ConsumerState<_DetailsStep> createState() => _DetailsStepState();
}

class _DetailsStepState extends ConsumerState<_DetailsStep> {
  final Map<String, TextEditingController> _fields =
      <String, TextEditingController>{};
  Map<String, String> _errors = const <String, String>{};
  Failure? _failure;
  bool _busy = false;
  bool _companyLoaded = false;

  bool get _company => widget.kind == _AccountKind.company;

  bool _missing(String field) =>
      widget.profile.registrationMissing.any((gap) => gap.field == field);

  TextEditingController _controller(String field, [String initial = '']) =>
      _fields.putIfAbsent(field, () => TextEditingController(text: initial));

  @override
  void initState() {
    super.initState();
    _controller('full_name', widget.profile.fullName);
    _controller('national_id', widget.profile.nationalId);
    _controller('city', widget.profile.city);
    if (_company) _loadCompany();
  }

  Future<void> _loadCompany() async {
    // ما سبق حفظُه من بيانات المنشأة يُعرض لا يُطلب ثانيةً — ومنشأةٌ لا ملفَّ لها
    // بعدُ تبدأ فارغة، وذلك ليس خطأً.
    final company = await ref
        .read(manageProfileProvider)
        .loadCompany()
        .catchError((_) => null);
    if (!mounted) return;
    final value = company ?? const CompanyProfile.blank();
    setState(() {
      _controller('name').text = value.name;
      _controller('commercial_register').text = value.commercialRegister;
      _controller('vat_number').text = value.vatNumber;
      _controller('district').text = value.district;
      _controller('street').text = value.street;
      _controller('building_number').text = value.buildingNumber;
      _controller('additional_number').text = value.additionalNumber;
      _controller('postal_code').text = value.postalCode;
      if (value.city.isNotEmpty) _controller('city').text = value.city;
      _companyLoaded = true;
    });
  }

  @override
  void dispose() {
    for (final controller in _fields.values) {
      controller.dispose();
    }
    super.dispose();
  }

  String _text(String field) => _fields[field]?.text.trim() ?? '';

  /// أخطاءُ الحقول من `detail` كما أرسلها الخادم: `{"vat_number": ["…"]}`.
  Map<String, String> _fieldErrors(Failure failure) {
    if (failure is! ApiFailure) return const <String, String>{};
    final detail = failure.detail ?? const <String, Object?>{};
    return <String, String>{
      for (final entry in detail.entries)
        if (entry.value is List && (entry.value! as List).isNotEmpty)
          entry.key: '${(entry.value! as List).first}'
        else if (entry.value is String)
          entry.key: entry.value! as String,
    };
  }

  Future<void> _save() async {
    setState(() {
      _busy = true;
      _failure = null;
      _errors = const <String, String>{};
    });
    final manage = ref.read(manageProfileProvider);
    try {
      // الاسمُ يُرسَل إن تغيّر وحده: اسمٌ قديمٌ قصيرٌ من v1 لا يُعاد فحصُه على
      // عميلٍ جاء يُكمل مدينتَه. وكلُّ بابٍ يُحفظ وحده — خطأٌ في الرقم الضريبيّ
      // لا يمحو الاسمَ الذي كُتب صحيحاً.
      final name = _text('full_name');
      final nameChanged = name.isNotEmpty && name != widget.profile.fullName;
      final city = _company ? '' : _text('city');
      if (nameChanged || city.isNotEmpty) {
        await manage.save(
          fullName: nameChanged ? name : null,
          city: city.isEmpty ? null : city,
        );
      }
      if (_missing('national_id') && _text('national_id').isNotEmpty) {
        await manage.pinNationalId(_text('national_id'));
      }
      if (_company) {
        await manage.saveCompany(
          CompanyProfile(
            name: _text('name'),
            representativeName: name,
            commercialRegister: _text('commercial_register'),
            vatNumber: _text('vat_number'),
            buildingNumber: _text('building_number'),
            additionalNumber: _text('additional_number'),
            street: _text('street'),
            district: _text('district'),
            city: _text('city'),
            postalCode: _text('postal_code'),
            isComplete: false,
          ),
        );
      }

      // ثمّ **يُسأل الخادمُ لا الاستمارة**: هل بقي شيء؟
      await ref.read(profileControllerProvider.notifier).refresh();
      final fresh = ref.read(profileControllerProvider).value?.value;
      if (!mounted) return;
      final l10n = AppLocalizations.of(context);
      if (fresh != null && !fresh.isRegistered) {
        setState(() {
          // `ApiFailure` لا `UnexpectedFailure`: هذه تُعرض «حدث خطأ غير
          // متوقع»، وهذا ليس خطأً — هو جوابٌ يسمّي ما بقي.
          _failure = ApiFailure(
            code: 'registration_incomplete',
            message: l10n.registrationStillMissing(
              fresh.registrationMissing.map((gap) => gap.label).join('، '),
            ),
          );
        });
        return;
      }
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text(l10n.registrationDone)));
      context.goNamed(Routes.home);
    } on Failure catch (failure) {
      if (!mounted) return;
      setState(() {
        _failure = failure;
        _errors = _fieldErrors(failure);
      });
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final palette = HarajPalette.of(context);
    final missing = widget.profile.registrationMissing
        .map((gap) => gap.label)
        .join('، ');

    // ثلاثُ بطاقات: ما ينقص ونوعُ الحساب، ثمّ بياناتُ الشخص، ثمّ المنشأة —
    // كلُّ بابٍ في وعائه كما يُحفظ كلُّ بابٍ وحدَه في `_save`.
    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 16, 16, 24),
      children: <Widget>[
        _Card(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: <Widget>[
              _CardHeader(
                icon: _company
                    ? Icons.apartment_outlined
                    : Icons.person_outline,
                title: l10n.registrationAccountType(
                  _company
                      ? l10n.registrationCompany
                      : l10n.registrationIndividual,
                ),
                trailing: widget.onChangeKind == null
                    ? null
                    : TextButton(
                        onPressed: widget.onChangeKind,
                        style: TextButton.styleFrom(
                          foregroundColor: palette.gold,
                          padding: const EdgeInsets.symmetric(horizontal: 10),
                          minimumSize: const Size(0, 34),
                          tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                          textStyle: const TextStyle(
                            fontFamily: HarajTheme.fontFamily,
                            fontSize: 13,
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                        child: Text(l10n.registrationChangeType),
                      ),
              ),
              Padding(
                padding: const EdgeInsets.symmetric(vertical: 12),
                child: Divider(height: 1, color: palette.navInactive),
              ),
              Text(
                l10n.registrationMissing(missing),
                style: TextStyle(
                  fontFamily: HarajTheme.fontFamily,
                  fontSize: 13,
                  height: 1.55,
                  color: palette.inkMuted,
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 14),
        _Card(
          padding: const EdgeInsets.fromLTRB(16, 10, 16, 10),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: <Widget>[
              _field(
                'full_name',
                _company
                    ? l10n.registrationRepresentative
                    : l10n.registrationFullName,
                hint: l10n.registrationNameHint,
              ),
              if (_missing('national_id'))
                _field(
                  'national_id',
                  l10n.registrationNationalId,
                  hint: l10n.registrationNationalIdHint,
                  digits: 10,
                ),
              if (!_company) _field('city', l10n.registrationCity),
            ],
          ),
        ),
        if (_company) ...<Widget>[
          const SizedBox(height: 14),
          _Card(
            padding: const EdgeInsets.fromLTRB(16, 16, 16, 10),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: <Widget>[
                _CardHeader(
                  icon: Icons.business_center_outlined,
                  title: l10n.registrationCompanySection,
                ),
                const SizedBox(height: 8),
                if (!_companyLoaded)
                  const Padding(
                    padding: EdgeInsets.all(16),
                    child: Center(child: CircularProgressIndicator()),
                  )
                else ...<Widget>[
                  _field('name', l10n.registrationOrgName),
                  _field(
                    'commercial_register',
                    l10n.companyRegister,
                    digits: 10,
                  ),
                  _field('vat_number', l10n.companyVatNumber, digits: 15),
                  _field('city', l10n.registrationCity),
                  _field('district', l10n.companyDistrict),
                  _field('street', l10n.companyStreet),
                  _field(
                    'building_number',
                    l10n.companyBuildingNumber,
                    digits: 4,
                  ),
                  _field(
                    'additional_number',
                    l10n.registrationAdditionalNumber,
                    digits: 4,
                  ),
                  _field('postal_code', l10n.companyPostalCode, digits: 5),
                ],
              ],
            ),
          ),
        ],
        const SizedBox(height: 16),
        if (_failure != null && _errors.isEmpty) ...<Widget>[
          FailureView(failure: _failure!),
          const SizedBox(height: 12),
        ],
        if (_busy)
          const SizedBox(
            height: 52,
            child: Center(child: CircularProgressIndicator()),
          )
        else
          FilledButton(
            onPressed: _save,
            style: FilledButton.styleFrom(
              backgroundColor: palette.gold,
              foregroundColor: Colors.white,
              minimumSize: const Size.fromHeight(52),
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(16),
              ),
              textStyle: const TextStyle(
                fontFamily: HarajTheme.fontFamily,
                fontWeight: FontWeight.w700,
                fontSize: 15,
              ),
            ),
            child: Text(l10n.registrationSave),
          ),
      ],
    );
  }

  Widget _field(String name, String label, {String? hint, int? digits}) {
    final error = _errors[name];
    final palette = HarajPalette.of(context);
    final border = OutlineInputBorder(
      borderRadius: BorderRadius.circular(14),
      borderSide: BorderSide(color: palette.navInactive),
    );
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: TextField(
        controller: _controller(name),
        keyboardType: digits == null
            ? TextInputType.text
            : TextInputType.number,
        textDirection: digits == null ? null : TextDirection.ltr,
        maxLength: digits,
        inputFormatters: digits == null
            ? null
            : <TextInputFormatter>[FilteringTextInputFormatter.digitsOnly],
        style: TextStyle(
          fontFamily: HarajTheme.fontFamily,
          fontSize: 14.5,
          color: palette.ink,
        ),
        decoration: InputDecoration(
          labelText: label,
          helperText: error == null ? hint : null,
          errorText: error,
          counterText: '',
          labelStyle: TextStyle(
            fontFamily: HarajTheme.fontFamily,
            color: palette.inkMuted,
          ),
          floatingLabelStyle: TextStyle(
            fontFamily: HarajTheme.fontFamily,
            color: palette.gold,
            fontWeight: FontWeight.w600,
          ),
          helperStyle: TextStyle(
            fontFamily: HarajTheme.fontFamily,
            fontSize: 11.5,
            color: palette.inkMuted,
          ),
          helperMaxLines: 2,
          errorMaxLines: 2,
          filled: true,
          fillColor: palette.cardSurface,
          contentPadding: const EdgeInsets.symmetric(
            horizontal: 14,
            vertical: 14,
          ),
          border: border,
          enabledBorder: border,
          focusedBorder: border.copyWith(
            borderSide: BorderSide(color: palette.gold, width: 1.6),
          ),
        ),
      ),
    );
  }
}
