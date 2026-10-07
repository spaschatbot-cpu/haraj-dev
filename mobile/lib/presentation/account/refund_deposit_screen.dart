import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app/providers.dart';
import '../../app/theme.dart';
import '../../domain/common/failure.dart';
import '../../domain/common/money.dart';
import '../../domain/wallet/entities/refund_request.dart';
import '../../domain/wallet/entities/wallet_balance.dart';
import '../../l10n/generated/app_localizations.dart';
import '../common/failure_message.dart';
import '../common/riyal_text.dart';
import '../profile/profile_controller.dart';
import '../wallet/wallet_controller.dart';
import 'account_page_scaffold.dart';

/// صفحة «طلب استرداد مبلغ التأمين» — على تصميم المالك (١٣ سبتمبر ٢٠٢٦).
///
/// **ما يُعرض من الخادم، وما يُدخِله العميل مدخلاتٌ فارغة** (المادة ١-٦، شاشة
/// مال): دلاءُ التأمين ورقمُ الجوال والطلباتُ السابقة تأتي من المزوّدات، ولا
/// رقمَ محسوبٌ هنا. والمبلغُ والآيبانُ والصورةُ والملاحظةُ مدخلاتٌ لا بيانات.
///
/// **والإرسالُ ورفعُ الصورة غيرُ مفعَّلين بعد**: عقد الخادم اليوم يقرأ الطلبات
/// السابقة (`v1WalletRefundRequestsList`) ولا مدخلَ فيه لإنشاء طلب. فالزرّان
/// يقولان «لم يُفعَّل بعد» بدل نجاحٍ مزيَّف — تُوصَل حين يصل مدخلُ الإنشاء.
class RefundDepositScreen extends ConsumerStatefulWidget {
  const RefundDepositScreen({super.key});

  @override
  ConsumerState<RefundDepositScreen> createState() =>
      _RefundDepositScreenState();
}

class _RefundDepositScreenState extends ConsumerState<RefundDepositScreen> {
  final _amount = TextEditingController();
  final _iban = TextEditingController();
  final _notes = TextEditingController();

  @override
  void dispose() {
    _amount.dispose();
    _iban.dispose();
    _notes.dispose();
    super.dispose();
  }

  /// دلاءُ التأمين وحدها من كل الدلاء.
  List<WalletBucket> _insuranceOf(WalletBalance balance) => balance.buckets
      .where(
        (b) => const <WalletBucketKind>{
          WalletBucketKind.insuranceFree,
          WalletBucketKind.insuranceHeld,
          WalletBucketKind.insuranceLocked,
        }.contains(b.kind),
      )
      .toList(growable: false);

  bool _sending = false;
  bool _uploading = false;

  /// يفتح المعرضَ ويرفع ما اختاره العميل صورةَ آيبان.
  ///
  /// **والرفعُ شرطٌ لا زينة**: `request_refund` في الخلفية ترفض الطلبَ بلا
  /// هذه الصورة (`missing_document: iban`). فكان الزرُّ يقول «لم يُفعَّل بعد»
  /// وكان الاستردادُ مستحيلاً من التطبيق أصلاً لا بطيئاً.
  Future<void> _pickIban(AppLocalizations l10n) async {
    final messenger = ScaffoldMessenger.of(context);
    setState(() => _uploading = true);
    try {
      final done = await ref.read(uploadDocumentProvider)(kind: 'iban');
      if (!mounted) return;
      // **الإلغاءُ صمتٌ**: من فتح المعرضَ وعدل لا يحتاج رسالةً تقول له ذلك.
      if (!done) return;
      ref.invalidate(profileControllerProvider);
      messenger
        ..hideCurrentSnackBar()
        ..showSnackBar(SnackBar(content: Text(l10n.refundIbanUploaded)));
    } on Failure catch (failure) {
      if (!mounted) return;
      messenger
        ..hideCurrentSnackBar()
        ..showSnackBar(
          SnackBar(content: Text(failureMessage(context, failure))),
        );
    } finally {
      if (mounted) setState(() => _uploading = false);
    }
  }

  /// يُرسل الطلب.
  ///
  /// **والآيبانُ والملاحظاتُ يسافران في `note`**، نصّاً واحداً كما كتبهما
  /// العميل. لا حقلَ آيبانٍ في النموذج عند الخادم، وكانت الشاشةُ تجمعهما
  /// وترميهما — فتُنفّذ المحاسبةُ استرداداً بلا حسابٍ تحوّل إليه، وتسأل
  /// العميلَ بالهاتف عمّا كتبه في التطبيق.
  ///
  /// **ولا تحقّقَ من المبلغ هنا** غير أنه مكتوب: ما يجوز خروجُه يقرّره الدلو
  /// الحرّ في الخلفية، وقاعدةٌ ثانيةٌ هنا تتفارق عنها فترفض الشاشةُ مبلغاً
  /// يقبله الخادم أو العكس.
  Future<void> _submit(AppLocalizations l10n) async {
    final messenger = ScaffoldMessenger.of(context);
    final amount = _amount.text.trim();
    if (amount.isEmpty) {
      messenger
        ..hideCurrentSnackBar()
        ..showSnackBar(SnackBar(content: Text(l10n.refundAmountRequired)));
      return;
    }

    final iban = _iban.text.trim();
    final notes = _notes.text.trim();
    final note = <String>[
      if (iban.isNotEmpty) '${l10n.refundIbanLabel}: $iban',
      if (notes.isNotEmpty) notes,
    ].join('\n');

    setState(() => _sending = true);
    try {
      await ref.read(requestInsuranceRefundProvider)(
        amount: amount,
        note: note,
      );
      // الطلبُ لا يحرّك رصيداً، لكنّه يظهر في «طلباتي السابقة» — وقائمةٌ
      // قديمةٌ بلا الطلب الجديد تجعل العميلَ يظنّ أن إرساله ضاع فيعيده.
      ref
        ..invalidate(refundRequestsProvider)
        ..invalidate(walletBalanceProvider);
      if (!mounted) return;
      _amount.clear();
      _iban.clear();
      _notes.clear();
      messenger
        ..hideCurrentSnackBar()
        ..showSnackBar(SnackBar(content: Text(l10n.refundSubmitted)));
    } on Failure catch (failure) {
      // جوابُ الخادم كما جاء: «لديك طلبٌ مفتوح»، «المتاح أقلّ من المطلوب»…
      if (!mounted) return;
      messenger
        ..hideCurrentSnackBar()
        ..showSnackBar(
          SnackBar(content: Text(failureMessage(context, failure))),
        );
    } finally {
      if (mounted) setState(() => _sending = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);

    final phone = switch (ref.watch(profileControllerProvider)) {
      AsyncData(:final value) => value.value.phone,
      _ => null,
    };
    final insurance = switch (ref.watch(walletBalanceProvider)) {
      AsyncData(:final value) => _insuranceOf(value.value),
      _ => const <WalletBucket>[],
    };
    final requests = switch (ref.watch(refundRequestsProvider)) {
      AsyncData(:final value) => value.value,
      _ => const <RefundRequest>[],
    };

    return AccountPageScaffold(
      title: l10n.accountMenuRefundDeposit,
      child: ListView(
        padding: EdgeInsets.fromLTRB(
          16,
          16,
          16,
          16 + MediaQuery.paddingOf(context).bottom,
        ),
        children: <Widget>[
          _HeaderCard(l10n: l10n),
          const SizedBox(height: 16),
          _SummaryCard(l10n: l10n, insurance: insurance, phone: phone),
          const SizedBox(height: 16),
          _FormCard(
            l10n: l10n,
            amount: _amount,
            iban: _iban,
            notes: _notes,
            onChooseFile: _uploading ? null : () => _pickIban(l10n),
            uploading: _uploading,
            onSubmit: _sending ? null : () => _submit(l10n),
          ),
          const SizedBox(height: 16),
          _PreviousCard(l10n: l10n, requests: requests),
        ],
      ),
    );
  }
}

/// بطاقةُ الرأس — زجاجٌ مصبوغٌ بأزرقَ خفيف، بأيقونةٍ وعنوانٍ وشرح.
///
/// **كانت كحليّةً متدرّجة** (`heroTop`→`heroBottom`) بنصٍّ أبيض، فسقط الكحليُّ
/// في تصميم الزجاج الأبيض بطلب المالك (٣ أكتوبر ٢٠٢٦): لوحٌ داكنٌ فوق أرضيّةٍ
/// فاتحة يقطع الشاشة. فصارت زجاجاً بصبغةٍ زرقاء تُقرأ رأساً، ونصُّها كحليّ.
class _HeaderCard extends StatelessWidget {
  const _HeaderCard({required this.l10n});

  final AppLocalizations l10n;

  @override
  Widget build(BuildContext context) {
    final palette = HarajPalette.of(context);
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(20),
        gradient: LinearGradient(
          begin: Alignment.topRight,
          end: Alignment.bottomLeft,
          colors: <Color>[
            Color.alphaBlend(
              palette.gold.withValues(alpha: 0.14),
              palette.cardSurface,
            ),
            palette.cardSurface,
          ],
        ),
        border: Border.all(color: palette.gold.withValues(alpha: 0.22)),
        boxShadow: <BoxShadow>[
          BoxShadow(
            color: palette.ink.withValues(alpha: 0.05),
            blurRadius: 16,
            offset: const Offset(0, 6),
          ),
        ],
      ),
      child: Row(
        children: <Widget>[
          Container(
            width: 48,
            height: 48,
            alignment: Alignment.center,
            decoration: BoxDecoration(
              color: palette.gold.withValues(alpha: 0.10),
              borderRadius: BorderRadius.circular(14),
            ),
            child: Icon(
              Icons.assignment_return_rounded,
              color: palette.gold,
              size: 24,
            ),
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: <Widget>[
                Text(
                  l10n.refundHeaderTitle,
                  style: TextStyle(
                    color: palette.ink,
                    fontSize: 17,
                    fontWeight: FontWeight.w700,
                    fontFamily: HarajTheme.fontFamily,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  l10n.refundHeaderSubtitle,
                  style: TextStyle(
                    color: palette.inkMuted,
                    fontSize: 12.5,
                    height: 1.5,
                    fontFamily: HarajTheme.fontFamily,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

/// بطاقةُ الملخّص — دلاءُ التأمين من الخادم (أو تنبيهٌ حين لا تأمين)، والجوال.
class _SummaryCard extends StatelessWidget {
  const _SummaryCard({
    required this.l10n,
    required this.insurance,
    required this.phone,
  });

  final AppLocalizations l10n;
  final List<WalletBucket> insurance;
  final String? phone;

  @override
  Widget build(BuildContext context) {
    return _WhiteCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: <Widget>[
          if (insurance.isEmpty)
            _WarningBox(text: l10n.refundNoInsurance)
          else
            for (final bucket in insurance) ...<Widget>[
              _AmountRow(label: bucket.label, money: bucket.money),
              const SizedBox(height: 12),
            ],
          if (phone != null)
            _AmountRow.text(
              label: l10n.profilePhone,
              text: phone!,
              icon: Icons.phone_outlined,
              textLtr: true,
            ),
        ],
      ),
    );
  }
}

/// تنسيقُ حقلٍ احترافيّ: أرضيّةٌ زجاجيّةٌ ممتلئة، زوايا مدوّرة، حدٌّ رقيقٌ يذهب
/// إلى الأزرق عند التركيز — بدل الإطار الأسود التقليديّ لـ`OutlineInputBorder`.
///
/// والأرضيّةُ `cardSurface` لا `pageBackground` منذ تصميم الزجاج (٣ أكتوبر
/// ٢٠٢٦): الرماديُّ المصمت داخل كرتٍ شفّاف يُقرأ ثقباً لا حقلاً.
InputDecoration _fieldDecoration(
  HarajPalette palette, {
  required String label,
  String? helper,
  String? hint,
  bool alignLabelWithHint = false,
}) {
  OutlineInputBorder border(Color color, double width) => OutlineInputBorder(
    borderRadius: BorderRadius.circular(14),
    borderSide: BorderSide(color: color, width: width),
  );
  return InputDecoration(
    labelText: label,
    helperText: helper,
    helperMaxLines: 2,
    hintText: hint,
    alignLabelWithHint: alignLabelWithHint,
    filled: true,
    fillColor: palette.cardSurface,
    floatingLabelStyle: TextStyle(color: palette.gold),
    enabledBorder: border(palette.navInactive, 1),
    focusedBorder: border(palette.gold, 1.6),
    border: border(palette.navInactive, 1),
  );
}

/// بطاقةُ النموذج — المبلغ، الآيبان، صورة الآيبان، الملاحظات، وزرّ الإرسال.
class _FormCard extends StatelessWidget {
  const _FormCard({
    required this.l10n,
    required this.amount,
    required this.iban,
    required this.notes,
    required this.onChooseFile,
    required this.uploading,
    required this.onSubmit,
  });

  final AppLocalizations l10n;
  final TextEditingController amount;
  final TextEditingController iban;
  final TextEditingController notes;

  /// `null` أثناء الرفع: ضغطتان تفتحان معرضين.
  final VoidCallback? onChooseFile;

  final bool uploading;

  /// `null` أثناء الإرسال: ضغطتان على طلبِ استردادٍ طلبان.
  final VoidCallback? onSubmit;

  @override
  Widget build(BuildContext context) {
    final palette = HarajPalette.of(context);
    return _WhiteCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          _SectionTitle(
            icon: Icons.description_outlined,
            text: l10n.refundFormSection,
          ),
          const SizedBox(height: 16),

          TextField(
            controller: amount,
            keyboardType: const TextInputType.numberWithOptions(decimal: true),
            decoration: _fieldDecoration(
              palette,
              label: l10n.refundAmountLabel,
            ),
          ),
          const SizedBox(height: 16),

          TextField(
            controller: iban,
            textCapitalization: TextCapitalization.characters,
            maxLength: 24,
            inputFormatters: <TextInputFormatter>[
              // آيبانٌ سعوديّ: أحرفٌ كبيرة وأرقام لا غير، ٢٤ خانة.
              FilteringTextInputFormatter.allow(RegExp('[A-Za-z0-9]')),
              TextInputFormatter.withFunction(
                (old, value) => value.copyWith(text: value.text.toUpperCase()),
              ),
            ],
            decoration: _fieldDecoration(
              palette,
              label: l10n.refundIbanLabel,
              helper: l10n.refundIbanHint,
              hint: 'SA',
            ),
          ),
          const SizedBox(height: 8),

          Text(
            l10n.refundIbanImageLabel,
            style: TextStyle(
              color: palette.ink,
              fontSize: 14,
              fontWeight: FontWeight.w600,
              fontFamily: HarajTheme.fontFamily,
            ),
          ),
          const SizedBox(height: 8),
          _FilePickerRow(
            l10n: l10n,
            onTap: onChooseFile,
            uploading: uploading,
            palette: palette,
          ),
          const SizedBox(height: 16),

          TextField(
            controller: notes,
            maxLines: 3,
            decoration: _fieldDecoration(
              palette,
              label: l10n.refundNotesLabel,
              alignLabelWithHint: true,
            ),
          ),
          const SizedBox(height: 18),

          _GoldButton(
            label: l10n.refundSubmit,
            onTap: onSubmit,
            palette: palette,
          ),
        ],
      ),
    );
  }
}

/// صفُّ اختيار الملف — زرٌّ واسمُ الملف (فارغٌ حتى يُختار).
class _FilePickerRow extends StatelessWidget {
  const _FilePickerRow({
    required this.l10n,
    required this.onTap,
    required this.uploading,
    required this.palette,
  });

  final AppLocalizations l10n;
  final VoidCallback? onTap;
  final bool uploading;
  final HarajPalette palette;

  @override
  Widget build(BuildContext context) {
    // صفُّ الزجاج (٣ أكتوبر ٢٠٢٦): حدٌّ فاتحٌ كالحقول، والزرُّ أزرقُ شفيف
    // بأيقونة — كان رماديّاً بحدٍّ كحليٍّ لا يشبه ما حوله.
    return Container(
      decoration: BoxDecoration(
        color: palette.cardSurface,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: palette.navInactive),
      ),
      child: Row(
        children: <Widget>[
          Material(
            color: palette.gold.withValues(alpha: 0.08),
            borderRadius: const BorderRadius.horizontal(
              right: Radius.circular(14),
            ),
            child: InkWell(
              borderRadius: const BorderRadius.horizontal(
                right: Radius.circular(14),
              ),
              onTap: onTap,
              child: Padding(
                padding: const EdgeInsets.symmetric(
                  horizontal: 14,
                  vertical: 13,
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: <Widget>[
                    Icon(
                      Icons.upload_file_rounded,
                      size: 18,
                      color: palette.gold,
                    ),
                    const SizedBox(width: 6),
                    Text(
                      l10n.refundChooseFile,
                      style: TextStyle(
                        color: palette.gold,
                        fontWeight: FontWeight.w700,
                        fontFamily: HarajTheme.fontFamily,
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Text(
              // أثناء الرفع يُقال ذلك مكان «لم يُختَر ملف» — فالسطرُ نفسُه
              // يجيب عن «ماذا يحدث الآن؟».
              uploading ? l10n.refundIbanUploading : l10n.refundNoFile,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: TextStyle(
                color: palette.inkMuted,
                fontSize: 13,
                fontFamily: HarajTheme.fontFamily,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

/// بطاقةُ الطلبات السابقة — من المزوّد، أو «لا توجد» حين تخلو.
class _PreviousCard extends StatelessWidget {
  const _PreviousCard({required this.l10n, required this.requests});

  final AppLocalizations l10n;
  final List<RefundRequest> requests;

  @override
  Widget build(BuildContext context) {
    final palette = HarajPalette.of(context);
    return _WhiteCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          _SectionTitle(
            icon: Icons.history_rounded,
            text: l10n.refundPreviousSection,
          ),
          const SizedBox(height: 12),
          if (requests.isEmpty)
            Text(
              l10n.refundPreviousEmpty,
              style: TextStyle(
                color: palette.inkMuted,
                fontFamily: HarajTheme.fontFamily,
              ),
            )
          else
            for (final request in requests) ...<Widget>[
              _AmountRow(label: request.stateLabel, money: request.money),
              const SizedBox(height: 12),
            ],
        ],
      ),
    );
  }
}

// ————— عناصرُ مشتركة —————

/// بطاقةٌ زجاجيّة بحدٍّ رفيعٍ وظلٍّ ناعم — قشرةُ كل أقسام الصفحة، بتصميم
/// الزجاج الأبيض (٣ أكتوبر ٢٠٢٦).
class _WhiteCard extends StatelessWidget {
  const _WhiteCard({required this.child});

  final Widget child;

  @override
  Widget build(BuildContext context) {
    final palette = HarajPalette.of(context);
    return Container(
      padding: const EdgeInsets.all(16),
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
      child: child,
    );
  }
}

class _SectionTitle extends StatelessWidget {
  const _SectionTitle({required this.icon, required this.text});

  final IconData icon;
  final String text;

  @override
  Widget build(BuildContext context) {
    final palette = HarajPalette.of(context);
    return Row(
      children: <Widget>[
        Container(
          width: 34,
          height: 34,
          decoration: BoxDecoration(
            color: palette.gold.withValues(alpha: 0.08),
            borderRadius: BorderRadius.circular(10),
          ),
          child: Icon(icon, size: 18, color: palette.gold),
        ),
        const SizedBox(width: 10),
        Text(
          text,
          style: TextStyle(
            color: palette.ink,
            fontSize: 15,
            fontWeight: FontWeight.w700,
            fontFamily: HarajTheme.fontFamily,
          ),
        ),
      ],
    );
  }
}

/// صندوقٌ احترافيّ: مربّعُ أيقونةٍ أزرق على اليمين، ثم تسميةٌ فوق قيمة.
///
/// عنصرٌ واحد يخدم المبلغَ (`money`) والنصَّ (`text`) معاً — بحدٍّ رقيقٍ وأرضيّةٍ
/// زرقاءَ شفيفة لا رماديّة، فيُقرأ بطاقةً مرتّبة لا صندوقاً باهتاً.
class _AmountRow extends StatelessWidget {
  const _AmountRow({required this.label, required this.money})
    : text = null,
      textLtr = false,
      icon = Icons.shield_outlined;

  const _AmountRow.text({
    required this.label,
    required String this.text,
    required this.icon,
    this.textLtr = false,
  }) : money = null;

  final String label;
  final Money? money;
  final String? text;
  final bool textLtr;
  final IconData icon;

  @override
  Widget build(BuildContext context) {
    final palette = HarajPalette.of(context);
    final Widget value = money != null
        ? RiyalText(
            money!,
            style: TextStyle(
              color: palette.ink,
              fontSize: 18,
              fontWeight: FontWeight.w700,
              fontFamily: HarajTheme.fontFamily,
            ),
          )
        : Text(
            text!,
            textDirection: textLtr ? TextDirection.ltr : null,
            style: TextStyle(
              color: palette.ink,
              fontSize: 16,
              fontWeight: FontWeight.w700,
              fontFamily: HarajTheme.fontFamily,
            ),
          );

    // صفُّ الزجاج (٣ أكتوبر ٢٠٢٦): سقط الشريطُ الجانبيّ والظلّ — الصفُّ داخل
    // كرتٍ زجاجيٍّ له ظلُّه، وظلٌّ ثانٍ وشريطٌ ملوّن كانا زخرفةً فوق زخرفة.
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: palette.gold.withValues(alpha: 0.05),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: palette.navInactive.withValues(alpha: 0.7)),
      ),
      child: Row(
        children: <Widget>[
          Container(
            width: 40,
            height: 40,
            alignment: Alignment.center,
            decoration: BoxDecoration(
              color: palette.gold.withValues(alpha: 0.08),
              borderRadius: BorderRadius.circular(10),
            ),
            child: Icon(icon, size: 20, color: palette.gold),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text(
                  label,
                  style: TextStyle(
                    color: palette.inkMuted,
                    fontSize: 12.5,
                    fontWeight: FontWeight.w600,
                    fontFamily: HarajTheme.fontFamily,
                  ),
                ),
                const SizedBox(height: 4),
                value,
              ],
            ),
          ),
        ],
      ),
    );
  }
}

/// صندوقُ تنبيهٍ أحمر — حين لا تأمينَ قابلاً للاسترداد.
class _WarningBox extends StatelessWidget {
  const _WarningBox({required this.text});

  final String text;

  @override
  Widget build(BuildContext context) {
    const danger = Color(0xFFB42335);
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: danger.withValues(alpha: 0.07),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: danger.withValues(alpha: 0.30)),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          const Icon(Icons.error_outline_rounded, color: danger, size: 20),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              text,
              style: const TextStyle(
                color: danger,
                fontSize: 13.5,
                height: 1.5,
                fontWeight: FontWeight.w600,
                fontFamily: HarajTheme.fontFamily,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

/// الزرُّ الأزرقُ الممتلئ — كزرّ الدخول.
///
/// كان `InkWell` بتدرّجٍ لا يتغيّر حين يُعطَّل، فيبدو قابلاً للضغط أثناء
/// الإرسال. وفي تصميم الزجاج (٣ أكتوبر ٢٠٢٦) صار `FilledButton` بلون الزرّ
/// الواحد في التطبيق، ويَبهَت حين `onTap` فارغ — والسلوكُ هو هو.
class _GoldButton extends StatelessWidget {
  const _GoldButton({
    required this.label,
    required this.onTap,
    required this.palette,
  });

  final String label;
  final VoidCallback? onTap;
  final HarajPalette palette;

  @override
  Widget build(BuildContext context) {
    return FilledButton(
      onPressed: onTap,
      style: FilledButton.styleFrom(
        backgroundColor: palette.gold,
        foregroundColor: Colors.white,
        disabledBackgroundColor: palette.gold.withValues(alpha: 0.35),
        disabledForegroundColor: Colors.white,
        minimumSize: const Size.fromHeight(50),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
        textStyle: const TextStyle(
          fontFamily: HarajTheme.fontFamily,
          fontWeight: FontWeight.w700,
          fontSize: 15,
        ),
      ),
      child: Text(label, textAlign: TextAlign.center),
    );
  }
}
