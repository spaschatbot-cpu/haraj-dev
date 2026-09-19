import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app/providers.dart';
import '../../app/theme.dart';
import '../../domain/common/failure.dart';
import '../../domain/wallet/entities/bank_account.dart';
import '../../l10n/generated/app_localizations.dart';
import '../common/failure_view.dart';

/// ورقةُ الحوالة البنكيّة: حسابُ الشركة، ونسخٌ بضغطة. T954.
///
/// ## لماذا وُجدت
///
/// قناتان لشحن التأمين — ميسر بالبطاقة، **والحوالة** — وكان زرُّ الحوالة في
/// التطبيق يردّ «قريباً» بلا رقم حساب، فالعميلُ الذي يريد التحويل لا يجد إلى
/// أين يحوّل. وv1 يعرضه من `account_page_settings`.
///
/// **والفاتورةُ حوالةٌ وحدَها** بعد قرار المالك (١٩ سبتمبر ٢٠٢٦): «رصيد
/// التأمين لا يمكن وممنوع السداد منه للفواتير. بعد سداد فاتورة العربية يقدر
/// يسترد التأمين» — فحلّت هذه الورقةُ محلَّ زرّ «دفع كامل المختارة» في شاشة
/// المشتريات.
///
/// ## وثلاثةُ قراراتٍ في الشكل
///
/// * **النسخُ زرٌّ لا تحديدٌ يدويّ**: آيبانٌ من أربعةٍ وعشرين محرفاً يُنسَخ
///   باليد يُخطئ فيه كثيرون، والمالُ يذهب إلى حسابٍ آخر.
/// * **الآيبان بخطٍّ أحاديّ الاتّساع و`ltr`**: أحرفٌ وأرقامٌ لاتينيّة في
///   سياقٍ عربيّ يُعاد ترتيبُها. والمسافةُ كلَّ أربعةٍ تجعل المراجعةَ ممكنة
///   — **وتُحذف عند النسخ**، فما يُلصَق في تطبيق البنك نظيفٌ بلا فراغات.
/// * **المرجعُ يُعرَض حين يوجد**: من يسدّد فاتورةً يكتب رقمَها في خانة
///   «الغرض»، وبدونه تصل الحوالةُ ولا يُعرف عن ماذا — وذاك تأخيرٌ في
///   المطابقة لا عطلٌ في التطبيق، لكنّه يُعاش عطلاً.
class BankTransferSheet extends ConsumerWidget {
  const BankTransferSheet({this.reference, super.key});

  /// رقمُ الفاتورة إن كانت الحوالةُ لفاتورةٍ بعينها، أو `null` لشحن التأمين.
  final String? reference;

  /// يفتحها ورقةً سفليّة — البابُ الوحيد، فلا يبنيها أحدٌ بيده.
  static Future<void> open(BuildContext context, {String? reference}) {
    return showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (_) => BankTransferSheet(reference: reference),
    );
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final palette = HarajPalette.of(context);
    final l10n = AppLocalizations.of(context);
    final account = ref.watch(bankAccountProvider);

    return Container(
      decoration: BoxDecoration(
        color: palette.cardSurface,
        borderRadius: const BorderRadius.vertical(top: Radius.circular(22)),
      ),
      padding: const EdgeInsets.fromLTRB(18, 10, 18, 18),
      child: SafeArea(
        top: false,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: <Widget>[
            Center(
              child: Container(
                width: 38,
                height: 4,
                margin: const EdgeInsets.only(bottom: 14),
                decoration: BoxDecoration(
                  color: palette.navInactive,
                  borderRadius: BorderRadius.circular(2),
                ),
              ),
            ),
            Row(
              children: <Widget>[
                Icon(
                  Icons.account_balance_outlined,
                  size: 20,
                  color: palette.goldDeep,
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    l10n.bankTransferTitle,
                    style: TextStyle(
                      fontFamily: HarajTheme.fontFamily,
                      fontSize: 16,
                      fontWeight: FontWeight.w800,
                      color: palette.ink,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            switch (account) {
              AsyncData(value: final BankAccount row) when row.configured =>
                _Details(row: row, reference: reference, palette: palette),
              // حسابٌ لم يُضبَط على الخادم: جملةٌ تقول ذلك، لا أربعةُ أسطرٍ
              // فارغةٍ تُقرأ بياناتٍ ناقصة.
              AsyncData() => _Note(
                text: l10n.bankTransferUnavailable,
                palette: palette,
              ),
              AsyncError(:final error, :final stackTrace) => FailureView(
                failure: error is Failure
                    ? error
                    : UnexpectedFailure(error, stackTrace: stackTrace),
                onRetry: () => ref.invalidate(bankAccountProvider),
              ),
              _ => const Padding(
                padding: EdgeInsets.symmetric(vertical: 28),
                child: Center(child: CircularProgressIndicator()),
              ),
            },
          ],
        ),
      ),
    );
  }
}

class _Details extends StatelessWidget {
  const _Details({
    required this.row,
    required this.reference,
    required this.palette,
  });

  final BankAccount row;
  final String? reference;
  final HarajPalette palette;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final purpose = reference;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      mainAxisSize: MainAxisSize.min,
      children: <Widget>[
        _Row(
          label: l10n.bankTransferBeneficiary,
          value: row.beneficiary,
          palette: palette,
        ),
        _Row(label: l10n.bankTransferBank, value: row.bank, palette: palette),
        _Row(
          label: l10n.bankTransferIban,
          value: row.iban,
          palette: palette,
          latin: true,
          grouped: true,
        ),
        if (row.account.isNotEmpty)
          _Row(
            label: l10n.bankTransferAccount,
            value: row.account,
            palette: palette,
            latin: true,
          ),
        if (purpose != null)
          _Row(
            label: l10n.bankTransferPurpose,
            value: purpose,
            palette: palette,
            latin: true,
          ),
        const SizedBox(height: 12),
        _Note(
          text: purpose == null
              ? l10n.bankTransferNoteTopUp
              : l10n.bankTransferNoteInvoice,
          palette: palette,
        ),
      ],
    );
  }
}

/// صفٌّ: تسميةٌ وقيمةٌ وزرُّ نسخ.
class _Row extends StatelessWidget {
  const _Row({
    required this.label,
    required this.value,
    required this.palette,
    this.latin = false,
    this.grouped = false,
  });

  final String label;
  final String value;
  final HarajPalette palette;

  /// نصٌّ لاتينيٌّ يُرسَم `ltr` بخطٍّ أحاديّ — آيبانٌ أو رقمُ حساب.
  final bool latin;

  /// يُعرَض بمسافةٍ كلَّ أربعةِ محارف. **وتُحذف عند النسخ.**
  final bool grouped;

  String get _shown {
    if (!grouped) return value;
    final parts = <String>[];
    for (var i = 0; i < value.length; i += 4) {
      final end = i + 4 < value.length ? i + 4 : value.length;
      parts.add(value.substring(i, end));
    }
    return parts.join(' ');
  }

  Future<void> _copy(BuildContext context) async {
    final l10n = AppLocalizations.of(context);
    final messenger = ScaffoldMessenger.of(context);
    // **القيمةُ الخام لا المعروضة**: المسافاتُ للقراءة، وخانةُ الآيبان في
    // تطبيق البنك ترفضها.
    await Clipboard.setData(ClipboardData(text: value));
    messenger
      ..hideCurrentSnackBar()
      ..showSnackBar(SnackBar(content: Text(l10n.bankTransferCopied(label))));
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 5),
      child: Row(
        children: <Widget>[
          SizedBox(
            width: 86,
            child: Text(
              label,
              style: TextStyle(
                fontFamily: HarajTheme.fontFamily,
                fontSize: 12,
                color: palette.inkMuted,
              ),
            ),
          ),
          Expanded(
            child: Text(
              _shown,
              textDirection: latin ? TextDirection.ltr : null,
              textAlign: latin ? TextAlign.left : TextAlign.right,
              style: TextStyle(
                fontFamily: latin ? 'monospace' : HarajTheme.fontFamily,
                fontSize: latin ? 13 : 13.5,
                fontWeight: FontWeight.w700,
                color: palette.ink,
                letterSpacing: latin ? 0.4 : null,
              ),
            ),
          ),
          IconButton(
            onPressed: () => _copy(context),
            icon: const Icon(Icons.copy_rounded, size: 17),
            color: palette.goldDeep,
            tooltip: l10n.bankTransferCopy,
            visualDensity: VisualDensity.compact,
          ),
        ],
      ),
    );
  }
}

class _Note extends StatelessWidget {
  const _Note({required this.text, required this.palette});

  final String text;
  final HarajPalette palette;

  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.all(11),
    decoration: BoxDecoration(
      color: palette.pillTop.withValues(alpha: 0.10),
      borderRadius: BorderRadius.circular(12),
    ),
    child: Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        Icon(Icons.info_outline_rounded, size: 16, color: palette.goldDeep),
        const SizedBox(width: 8),
        Expanded(
          child: Text(
            text,
            style: TextStyle(
              fontFamily: HarajTheme.fontFamily,
              fontSize: 12,
              height: 1.6,
              color: palette.inkMuted,
            ),
          ),
        ),
      ],
    ),
  );
}
