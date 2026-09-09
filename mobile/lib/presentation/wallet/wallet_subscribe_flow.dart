import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../app/router.dart';
import '../../app/theme.dart';
import '../../domain/common/failure.dart';
import '../../domain/profile/entities/customer_profile.dart';
import '../../l10n/generated/app_localizations.dart';
import '../common/failure_message.dart';
import '../profile/profile_controller.dart';

/// مسارُ الاشتراك: **بياناتٌ أوّلاً، ثم طريقةُ الدفع**.
///
/// خطوتان لا شاشة: الأولى تُكمل ما ينقص الحساب، والثانية تختار كيف يُدفع.
/// وترتيبُهما ليس ذوقاً — الدفعُ يُنسَب إلى شخصٍ باسمه وهويّته، وبوّابةٌ تُفتح
/// قبلهما تُنشئ عمليةً لا يُعرف صاحبُها.
///
/// **والحفظُ يقع فعلاً**: الاسمُ يمرّ بـ`save` والهويّةُ بـ`pinNationalId`،
/// وكلاهما يكتب عند الخادم ويردّ بالملف بعد الكتابة. زرٌّ يقول «حفظ» ولا يحفظ
/// أسوأ من غيابه.
Future<void> showSubscribeFlow(BuildContext context) async {
  final saved = await showDialog<bool>(
    context: context,
    builder: (context) => const _DetailsDialog(),
  );
  if (!(saved ?? false) || !context.mounted) return;

  await showDialog<void>(
    context: context,
    builder: (context) => const _PaymentDialog(),
  );
}

/// إطارُ الحوارين: شريطٌ باسمٍ وزرّ إغلاق، ثم المحتوى، ثم «إلغاء».
class _Sheet extends StatelessWidget {
  const _Sheet({required this.title, required this.child});

  final String title;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    final palette = HarajPalette.of(context);
    final theme = Theme.of(context);

    return Dialog(
      insetPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 40),
      backgroundColor: palette.cardSurface,
      clipBehavior: Clip.antiAlias,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 440),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: <Widget>[
            Padding(
              padding: const EdgeInsetsDirectional.fromSTEB(16, 10, 8, 8),
              child: Row(
                children: <Widget>[
                  Icon(
                    Icons.account_balance_wallet_outlined,
                    size: 18,
                    color: palette.goldDeep,
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      title,
                      style: theme.textTheme.titleMedium?.copyWith(
                        color: palette.brown,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ),
                  IconButton(
                    onPressed: () => Navigator.of(context).pop(),
                    icon: const Icon(Icons.close_rounded, size: 20),
                    color: palette.inkMuted,
                    tooltip: MaterialLocalizations.of(
                      context,
                    ).closeButtonTooltip,
                  ),
                ],
              ),
            ),
            Divider(height: 1, color: palette.gold.withValues(alpha: 0.30)),
            Flexible(
              // قابلٌ للتمرير: خمسةُ حقولٍ ولوحةُ مفاتيح لا يسعها جوّالٌ قصير.
              child: SingleChildScrollView(
                padding: const EdgeInsets.fromLTRB(16, 14, 16, 14),
                child: child,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// الخطوة الأولى: بيانات الحساب.
class _DetailsDialog extends ConsumerStatefulWidget {
  const _DetailsDialog();

  @override
  ConsumerState<_DetailsDialog> createState() => _DetailsDialogState();
}

class _DetailsDialogState extends ConsumerState<_DetailsDialog> {
  final TextEditingController _name = TextEditingController();
  final TextEditingController _nationalId = TextEditingController();

  bool _filled = false;
  bool _saving = false;
  Failure? _failure;

  @override
  void dispose() {
    _name.dispose();
    _nationalId.dispose();
    super.dispose();
  }

  /// يملأ الحقلين من الملف مرّةً واحدة: ملؤهما في كل بناءٍ يمسح ما يكتبه
  /// العميل تحت إصبعه.
  void _fill(CustomerProfile profile) {
    if (_filled) return;
    _filled = true;
    _name.text = profile.fullName;
    _nationalId.text = profile.nationalId;
  }

  Future<void> _save(CustomerProfile profile) async {
    setState(() {
      _saving = true;
      _failure = null;
    });
    try {
      final controller = ref.read(profileControllerProvider.notifier);
      final name = _name.text.trim();
      if (name.isNotEmpty && name != profile.fullName) {
        await controller.save(fullName: name);
      }
      final id = _nationalId.text.trim();
      // **الهويّة تُثبَّت مرّةً**: حسابٌ عليه هويّةٌ صحيحة يصل حقلُه مقفلاً،
      // وإعادةُ إرسالها تُرفض من الخادم برسالةٍ لا معنى لها هنا.
      if (id.isNotEmpty && id != profile.nationalId) {
        await controller.pinNationalId(id);
      }
      if (!mounted) return;
      Navigator.of(context).pop(true);
    } on Failure catch (failure) {
      if (!mounted) return;
      setState(() {
        _failure = failure;
        _saving = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final palette = HarajPalette.of(context);
    final state = ref.watch(profileControllerProvider);
    final profile = state.value?.value;
    if (profile != null) _fill(profile);

    return _Sheet(
      title: l10n.walletTopUpTitle,
      child: profile == null
          ? const Padding(
              padding: EdgeInsets.symmetric(vertical: 32),
              child: Center(child: CircularProgressIndicator()),
            )
          : Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: <Widget>[
                _Notice(
                  title: l10n.walletCompleteDataTitle,
                  body: l10n.walletCompleteDataNote,
                  palette: palette,
                ),
                const SizedBox(height: 14),
                // **نوعُ الحساب وجوّالُه للقراءة**: الأول يقرّره الخادم،
                // والثاني يُبدَّل من شاشة تغيير الجوال برمز تحقّق — وحقلٌ
                // يُكتب فيه ولا يُحفظ أسوأ من حقلٍ مقفل.
                _ReadOnlyField(
                  label: l10n.walletAccountType,
                  value: profile.accountType,
                  palette: palette,
                ),
                const SizedBox(height: 10),
                _Field(
                  label: l10n.walletFullName,
                  controller: _name,
                  palette: palette,
                ),
                const SizedBox(height: 10),
                _ReadOnlyField(
                  label: l10n.walletPhone,
                  value: profile.phone,
                  palette: palette,
                  ltr: true,
                ),
                const SizedBox(height: 10),
                _Field(
                  label: l10n.walletNationalId,
                  controller: _nationalId,
                  palette: palette,
                  ltr: true,
                  digitsOnly: true,
                  enabled: profile.nationalId.isEmpty,
                ),
                if (_failure case final Failure failure) ...<Widget>[
                  const SizedBox(height: 12),
                  Text(
                    failureMessage(context, failure),
                    style: TextStyle(
                      fontFamily: HarajTheme.fontFamily,
                      fontSize: 12,
                      fontWeight: FontWeight.w600,
                      color: Theme.of(context).colorScheme.error,
                    ),
                  ),
                ],
                const SizedBox(height: 16),
                FilledButton(
                  onPressed: _saving ? null : () => _save(profile),
                  style: FilledButton.styleFrom(
                    backgroundColor: palette.goldDeep,
                    foregroundColor: Colors.white,
                    padding: const EdgeInsets.symmetric(vertical: 15),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(12),
                    ),
                  ),
                  child: _saving
                      ? const SizedBox.square(
                          dimension: 18,
                          child: CircularProgressIndicator(
                            strokeWidth: 2,
                            color: Colors.white,
                          ),
                        )
                      : Text(l10n.walletSaveAndContinue),
                ),
                const SizedBox(height: 6),
                Align(
                  alignment: AlignmentDirectional.centerStart,
                  child: TextButton(
                    onPressed: () => Navigator.of(context).pop(false),
                    style: TextButton.styleFrom(
                      foregroundColor: palette.inkMuted,
                    ),
                    child: Text(
                      MaterialLocalizations.of(context).cancelButtonLabel,
                    ),
                  ),
                ),
              ],
            ),
    );
  }
}

/// الخطوة الثانية: طريقة الدفع.
///
/// **الثلاثةُ تُضغَط، وواحدةٌ تدفع**: البطاقة/مدى هي ما يفتحه العقد (`topups`).
/// والتحويلُ البنكيّ وApple Pay لا نقطةَ لهما بعد — وكانا باهتَين معطَّلين،
/// فصارا يُضغطان ويردّان «قريباً» بطلب المالك في ٩ سبتمبر ٢٠٢٦.
///
/// **ولا يفتحان مسارَ البطاقة**: زرٌّ اسمُه «تحويل بنكي» يفتح بوّابةَ بطاقةٍ
/// يكذب على من ضغطه، وقد يدفع بها وهو يظنّ أنه حوّل.
class _PaymentDialog extends StatelessWidget {
  const _PaymentDialog();

  /// طريقةٌ لم تُفعَّل بعد: حوارٌ صغير يقول ذلك، ولا يُغلق مربّعَ الاختيار —
  /// من ضغط طريقةً غير جاهزة يريد أن يختار غيرها لا أن يبدأ من جديد.
  static void _soon(BuildContext context) {
    final palette = HarajPalette.of(context);
    unawaited(
      showDialog<void>(
        context: context,
        builder: (context) => AlertDialog(
          backgroundColor: palette.cardSurface,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(18),
          ),
          content: Text(
            AppLocalizations.of(context).walletMethodSoon,
            textAlign: TextAlign.center,
            style: TextStyle(
              fontFamily: HarajTheme.fontFamily,
              fontSize: 13.5,
              fontWeight: FontWeight.w700,
              color: palette.brown,
              height: 1.5,
            ),
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
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final palette = HarajPalette.of(context);

    return _Sheet(
      title: l10n.walletTopUpTitle,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: <Widget>[
          Text(
            l10n.walletChoosePayment,
            style: TextStyle(
              fontFamily: HarajTheme.fontFamily,
              fontSize: 12,
              fontWeight: FontWeight.w600,
              color: palette.inkMuted,
            ),
          ),
          const SizedBox(height: 12),
          _Method(
            icon: Icons.account_balance_outlined,
            title: l10n.walletBankTransfer,
            note: l10n.walletBankTransferNote,
            palette: palette,
            onTap: () => _soon(context),
          ),
          const SizedBox(height: 10),
          _Method(
            icon: Icons.credit_card_rounded,
            title: l10n.walletCardMada,
            note: l10n.walletCardMadaNote,
            palette: palette,
            onTap: () {
              Navigator.of(context).pop();
              context.pushNamed(Routes.walletTopUp);
            },
          ),
          const SizedBox(height: 10),
          _Method(
            icon: Icons.apple_rounded,
            title: l10n.walletApplePay,
            note: l10n.walletApplePayNote,
            palette: palette,
            onTap: () => _soon(context),
          ),
          const SizedBox(height: 10),
          Align(
            alignment: AlignmentDirectional.centerStart,
            child: TextButton(
              onPressed: () => Navigator.of(context).pop(),
              style: TextButton.styleFrom(foregroundColor: palette.inkMuted),
              child: Text(MaterialLocalizations.of(context).cancelButtonLabel),
            ),
          ),
        ],
      ),
    );
  }
}

/// لوحُ تنبيهٍ ذهبيّ فوق النموذج.
class _Notice extends StatelessWidget {
  const _Notice({
    required this.title,
    required this.body,
    required this.palette,
  });

  final String title;
  final String body;
  final HarajPalette palette;

  @override
  Widget build(BuildContext context) => Container(
    decoration: BoxDecoration(
      color: palette.gold.withValues(alpha: 0.10),
      borderRadius: BorderRadius.circular(12),
      border: Border.all(color: palette.gold.withValues(alpha: 0.45)),
    ),
    padding: const EdgeInsets.fromLTRB(12, 10, 12, 12),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        Row(
          children: <Widget>[
            Icon(
              Icons.error_outline_rounded,
              size: 16,
              color: palette.goldDeep,
            ),
            const SizedBox(width: 6),
            Text(
              title,
              style: TextStyle(
                fontFamily: HarajTheme.fontFamily,
                fontSize: 12.5,
                fontWeight: FontWeight.w700,
                color: palette.goldDeep,
              ),
            ),
          ],
        ),
        const SizedBox(height: 6),
        Text(
          body,
          style: TextStyle(
            fontFamily: HarajTheme.fontFamily,
            fontSize: 11.5,
            color: palette.brown.withValues(alpha: 0.85),
            height: 1.55,
          ),
        ),
      ],
    ),
  );
}

/// حقلٌ يُكتب فيه.
class _Field extends StatelessWidget {
  const _Field({
    required this.label,
    required this.controller,
    required this.palette,
    this.ltr = false,
    this.digitsOnly = false,
    this.enabled = true,
  });

  final String label;
  final TextEditingController controller;
  final HarajPalette palette;
  final bool ltr;
  final bool digitsOnly;
  final bool enabled;

  @override
  Widget build(BuildContext context) => Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: <Widget>[
      Text(
        label,
        style: TextStyle(
          fontFamily: HarajTheme.fontFamily,
          fontSize: 11.5,
          fontWeight: FontWeight.w600,
          color: palette.inkMuted,
        ),
      ),
      const SizedBox(height: 5),
      TextField(
        controller: controller,
        enabled: enabled,
        textDirection: ltr ? TextDirection.ltr : null,
        keyboardType: digitsOnly ? TextInputType.number : TextInputType.text,
        inputFormatters: digitsOnly
            ? <TextInputFormatter>[FilteringTextInputFormatter.digitsOnly]
            : null,
        decoration: InputDecoration(
          isDense: true,
          filled: true,
          fillColor: enabled ? palette.cardSurface : palette.pageBackground,
          contentPadding: const EdgeInsets.symmetric(
            horizontal: 12,
            vertical: 14,
          ),
          border: OutlineInputBorder(
            borderRadius: BorderRadius.circular(12),
            borderSide: BorderSide(color: palette.gold.withValues(alpha: 0.35)),
          ),
          enabledBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(12),
            borderSide: BorderSide(color: palette.gold.withValues(alpha: 0.35)),
          ),
        ),
        style: TextStyle(
          fontFamily: HarajTheme.fontFamily,
          fontSize: 13.5,
          fontWeight: FontWeight.w600,
          color: palette.brown,
        ),
      ),
    ],
  );
}

/// حقلٌ للقراءة — يُعرض ولا يُكتب.
class _ReadOnlyField extends StatelessWidget {
  const _ReadOnlyField({
    required this.label,
    required this.value,
    required this.palette,
    this.ltr = false,
  });

  final String label;
  final String value;
  final HarajPalette palette;
  final bool ltr;

  @override
  Widget build(BuildContext context) => Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: <Widget>[
      Text(
        label,
        style: TextStyle(
          fontFamily: HarajTheme.fontFamily,
          fontSize: 11.5,
          fontWeight: FontWeight.w600,
          color: palette.inkMuted,
        ),
      ),
      const SizedBox(height: 5),
      Container(
        width: double.infinity,
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 14),
        decoration: BoxDecoration(
          color: palette.pageBackground,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: palette.gold.withValues(alpha: 0.22)),
        ),
        child: Text(
          value,
          textDirection: ltr ? TextDirection.ltr : null,
          style: TextStyle(
            fontFamily: HarajTheme.fontFamily,
            fontSize: 13.5,
            fontWeight: FontWeight.w600,
            color: palette.brown,
          ),
        ),
      ),
    ],
  );
}

/// صفُّ طريقةِ دفعٍ واحدة.
class _Method extends StatelessWidget {
  const _Method({
    required this.icon,
    required this.title,
    required this.note,
    required this.palette,
    required this.onTap,
  });

  final IconData icon;
  final String title;
  final String note;
  final HarajPalette palette;

  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => Material(
    color: palette.cardSurface,
    borderRadius: BorderRadius.circular(14),
    child: InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(14),
      child: Container(
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: palette.gold.withValues(alpha: 0.55)),
        ),
        padding: const EdgeInsets.fromLTRB(12, 12, 12, 12),
        child: Row(
          children: <Widget>[
            Container(
              padding: const EdgeInsets.all(8),
              decoration: BoxDecoration(
                color: palette.gold.withValues(alpha: 0.16),
                borderRadius: BorderRadius.circular(10),
              ),
              child: Icon(icon, size: 20, color: palette.goldDeep),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Text(
                    title,
                    style: TextStyle(
                      fontFamily: HarajTheme.fontFamily,
                      fontSize: 13.5,
                      fontWeight: FontWeight.w700,
                      color: palette.brown,
                    ),
                  ),
                  const SizedBox(height: 2),
                  Text(
                    note,
                    style: TextStyle(
                      fontFamily: HarajTheme.fontFamily,
                      fontSize: 11,
                      color: palette.inkMuted,
                      height: 1.4,
                    ),
                  ),
                ],
              ),
            ),
            Icon(Icons.chevron_left_rounded, size: 20, color: palette.inkMuted),
          ],
        ),
      ),
    ),
  );
}
