import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app/theme.dart';
import '../../domain/common/money.dart';
import '../../domain/wallet/entities/refund_request.dart';
import '../../domain/wallet/entities/wallet_balance.dart';
import '../../l10n/generated/app_localizations.dart';
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

  void _soon(AppLocalizations l10n) => ScaffoldMessenger.of(context)
    ..hideCurrentSnackBar()
    ..showSnackBar(SnackBar(content: Text(l10n.refundSubmitSoon)));

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
            onChooseFile: () => _soon(l10n),
            onSubmit: () => _soon(l10n),
          ),
          const SizedBox(height: 16),
          _PreviousCard(l10n: l10n, requests: requests),
        ],
      ),
    );
  }
}

/// بطاقةُ الرأس — كحليّةٌ متدرّجة بأيقونةٍ وعنوانٍ وشرح.
class _HeaderCard extends StatelessWidget {
  const _HeaderCard({required this.l10n});

  final AppLocalizations l10n;

  @override
  Widget build(BuildContext context) {
    final palette = HarajPalette.of(context);
    return Container(
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(20),
        gradient: LinearGradient(
          begin: Alignment.topRight,
          end: Alignment.bottomLeft,
          colors: <Color>[palette.heroTop, palette.heroBottom],
        ),
        boxShadow: <BoxShadow>[
          BoxShadow(
            color: palette.ink.withValues(alpha: 0.12),
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
              shape: BoxShape.circle,
              color: palette.goldOnDark.withValues(alpha: 0.14),
              border: Border.all(color: palette.gold, width: 1.6),
            ),
            child: Icon(
              Icons.assignment_return_rounded,
              color: palette.goldOnDark,
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
                    color: Colors.white,
                    fontSize: 18,
                    fontWeight: FontWeight.w700,
                    fontFamily: HarajTheme.fontFamily,
                  ),
                ),
                const SizedBox(height: 6),
                Text(
                  l10n.refundHeaderSubtitle,
                  style: TextStyle(
                    color: palette.navInactive,
                    fontSize: 13,
                    height: 1.4,
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

/// تنسيقُ حقلٍ احترافيّ: أرضيّةٌ فاتحةٌ ممتلئة، زوايا مدوّرة، حدٌّ رقيقٌ يذهب
/// إلى ذهبيٍّ عند التركيز — بدل الإطار الأسود التقليديّ لـ`OutlineInputBorder`.
InputDecoration _fieldDecoration(
  HarajPalette palette, {
  required String label,
  String? helper,
  String? hint,
  bool alignLabelWithHint = false,
}) {
  OutlineInputBorder border(Color color, double width) => OutlineInputBorder(
    borderRadius: BorderRadius.circular(12),
    borderSide: BorderSide(color: color, width: width),
  );
  return InputDecoration(
    labelText: label,
    helperText: helper,
    helperMaxLines: 2,
    hintText: hint,
    alignLabelWithHint: alignLabelWithHint,
    filled: true,
    fillColor: palette.pageBackground,
    floatingLabelStyle: TextStyle(color: palette.goldDeep),
    enabledBorder: border(palette.ink.withValues(alpha: 0.10), 1),
    focusedBorder: border(palette.gold, 1.6),
    border: border(palette.ink.withValues(alpha: 0.10), 1),
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
    required this.onSubmit,
  });

  final AppLocalizations l10n;
  final TextEditingController amount;
  final TextEditingController iban;
  final TextEditingController notes;
  final VoidCallback onChooseFile;
  final VoidCallback onSubmit;

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
          _FilePickerRow(l10n: l10n, onTap: onChooseFile, palette: palette),
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
    required this.palette,
  });

  final AppLocalizations l10n;
  final VoidCallback onTap;
  final HarajPalette palette;

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: palette.ink.withValues(alpha: 0.20)),
      ),
      child: Row(
        children: <Widget>[
          Material(
            color: palette.ink.withValues(alpha: 0.06),
            borderRadius: const BorderRadius.horizontal(
              right: Radius.circular(10),
            ),
            child: InkWell(
              borderRadius: const BorderRadius.horizontal(
                right: Radius.circular(10),
              ),
              onTap: onTap,
              child: Padding(
                padding: const EdgeInsets.symmetric(
                  horizontal: 14,
                  vertical: 12,
                ),
                child: Text(
                  l10n.refundChooseFile,
                  style: TextStyle(
                    color: palette.ink,
                    fontWeight: FontWeight.w600,
                    fontFamily: HarajTheme.fontFamily,
                  ),
                ),
              ),
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Text(
              l10n.refundNoFile,
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

/// بطاقةٌ بيضاء بظلٍّ خفيف — قشرةُ كل أقسام الصفحة.
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
        borderRadius: BorderRadius.circular(16),
        boxShadow: <BoxShadow>[
          BoxShadow(
            color: palette.ink.withValues(alpha: 0.05),
            blurRadius: 10,
            offset: const Offset(0, 2),
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
        Icon(icon, size: 18, color: palette.gold),
        const SizedBox(width: 8),
        Text(
          text,
          style: TextStyle(
            color: palette.ink,
            fontSize: 16,
            fontWeight: FontWeight.w700,
            fontFamily: HarajTheme.fontFamily,
          ),
        ),
      ],
    );
  }
}

/// صندوقٌ احترافيّ: أيقونةٌ ذهبيّةٌ دائريّة على اليمين، ثم تسميةٌ فوق قيمة.
///
/// عنصرٌ واحد يخدم المبلغَ (`money`) والنصَّ (`text`) معاً — بحدٍّ رقيقٍ وأرضيّةٍ
/// بيضاءَ لا رماديّة، فيُقرأ بطاقةً مرتّبة لا صندوقاً باهتاً.
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

    return Container(
      decoration: BoxDecoration(
        color: palette.cardSurface,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: palette.ink.withValues(alpha: 0.08)),
        boxShadow: <BoxShadow>[
          BoxShadow(
            color: palette.ink.withValues(alpha: 0.06),
            blurRadius: 12,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(14),
        child: IntrinsicHeight(
          child: Row(
            children: <Widget>[
              // استروكٌ جانبيٌّ ذهبيّ — شريطٌ رأسيٌّ على الحافّة (يمينُ RTL)
              // يعطي البطاقةَ لهجةً بلا حدٍّ ثقيل.
              Container(
                width: 4,
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    begin: Alignment.topCenter,
                    end: Alignment.bottomCenter,
                    colors: <Color>[palette.gold, palette.goldDeep],
                  ),
                ),
              ),
              Expanded(
                child: Padding(
                  padding: const EdgeInsets.all(14),
                  child: Row(
                    children: <Widget>[
                      Container(
                        width: 40,
                        height: 40,
                        alignment: Alignment.center,
                        decoration: BoxDecoration(
                          shape: BoxShape.circle,
                          color: palette.gold.withValues(alpha: 0.12),
                        ),
                        child: Icon(icon, size: 20, color: palette.goldDeep),
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
                ),
              ),
            ],
          ),
        ),
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
    const danger = Color(0xFFC0392B);
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: danger.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(12),
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

/// زرٌّ ذهبيٌّ ممتدّ — نفسُ زرّ المحفظة في الرأس.
class _GoldButton extends StatelessWidget {
  const _GoldButton({
    required this.label,
    required this.onTap,
    required this.palette,
  });

  final String label;
  final VoidCallback onTap;
  final HarajPalette palette;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.transparent,
      child: InkWell(
        borderRadius: BorderRadius.circular(14),
        onTap: onTap,
        child: Ink(
          width: double.infinity,
          padding: const EdgeInsets.symmetric(vertical: 15),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(14),
            gradient: LinearGradient(
              begin: Alignment.topRight,
              end: Alignment.bottomLeft,
              colors: <Color>[palette.gold, palette.goldDeep],
            ),
          ),
          child: Text(
            label,
            textAlign: TextAlign.center,
            style: const TextStyle(
              color: Colors.white,
              fontSize: 15,
              fontWeight: FontWeight.w700,
              fontFamily: HarajTheme.fontFamily,
            ),
          ),
        ),
      ),
    );
  }
}
