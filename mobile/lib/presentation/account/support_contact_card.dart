import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../app/theme.dart';
import '../../l10n/generated/app_localizations.dart';

/// بطاقةُ «الدعم الفني» — عنوانٌ وشرح، صندوقُ معلومةٍ، ثم زرُّ واتساب.
///
/// تُستعمل في «تواصل مع الدعم» و«طلب تعديل البيانات» معاً (المادة ٤-٥): نفسُ
/// البطاقة بنصِّ معلومةٍ مختلف، فلا تفترق هيئةُ الواحدة عن الأخرى.
///
/// **رقمُ الواتساب لم يصل بعد**: `_whatsAppNumber` فارغ، فالزرُّ يقول «لم يُضف
/// رقم الدعم بعد» بدل أن يفتح رابطاً مكسوراً أو رقمَ غريب. يُملأ الثابتُ حين
/// يصل الرقمُ من المالك فيعمل الزرّ بلا تغييرٍ آخر.
class SupportContactCard extends StatelessWidget {
  const SupportContactCard({required this.infoText, super.key});

  /// نصُّ صندوق المعلومة — يختلف بين صفحة الدعم وصفحة تعديل البيانات.
  final String infoText;

  /// رقمُ واتساب الدعم بصيغةٍ دوليّة بلا «+» (مثال: 9665XXXXXXXX). فارغٌ حتى
  /// يصل من المالك.
  static const String _whatsAppNumber = '';

  Future<void> _openWhatsApp(BuildContext context, AppLocalizations l10n) async {
    if (_whatsAppNumber.isEmpty) {
      ScaffoldMessenger.of(context)
        ..hideCurrentSnackBar()
        ..showSnackBar(SnackBar(content: Text(l10n.supportNotConfigured)));
      return;
    }
    final uri = Uri.parse('https://wa.me/$_whatsAppNumber');
    try {
      await launchUrl(uri, mode: LaunchMode.externalApplication);
    } on Object {
      if (context.mounted) {
        ScaffoldMessenger.of(context)
          ..hideCurrentSnackBar()
          ..showSnackBar(SnackBar(content: Text(l10n.supportNotConfigured)));
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final palette = HarajPalette.of(context);
    // أيقونةُ واتساب من خطّ Font Awesome Brands (البناءُ المباشر — الصنفُ
    // النهائيّ يُنشأ ولا يُورَّث).
    const whatsApp = IconData(
      0xf232,
      fontFamily: 'FontAwesomeBrands',
      fontPackage: 'font_awesome_flutter',
    );
    const whatsAppGreen = Color(0xFF25D366);

    return Container(
      margin: const EdgeInsets.all(16),
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: palette.cardSurface,
        borderRadius: BorderRadius.circular(20),
        boxShadow: <BoxShadow>[
          BoxShadow(
            color: palette.ink.withValues(alpha: 0.06),
            blurRadius: 14,
            offset: const Offset(0, 5),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: <Widget>[
          Center(
            child: Container(
              width: 64,
              height: 64,
              alignment: Alignment.center,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: palette.gold.withValues(alpha: 0.12),
              ),
              child: Icon(
                Icons.support_agent_rounded,
                size: 34,
                color: palette.goldDeep,
              ),
            ),
          ),
          const SizedBox(height: 14),
          Text(
            l10n.supportTitle,
            textAlign: TextAlign.center,
            style: TextStyle(
              color: palette.ink,
              fontSize: 19,
              fontWeight: FontWeight.w700,
              fontFamily: HarajTheme.fontFamily,
            ),
          ),
          const SizedBox(height: 6),
          Text(
            l10n.supportSubtitle,
            textAlign: TextAlign.center,
            style: TextStyle(
              color: palette.inkMuted,
              fontSize: 13.5,
              fontFamily: HarajTheme.fontFamily,
            ),
          ),
          const SizedBox(height: 18),

          // صندوقُ المعلومة — أزرقُ فاتحٌ هادئ.
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: palette.heroGlow.withValues(alpha: 0.10),
              borderRadius: BorderRadius.circular(14),
            ),
            child: Text(
              infoText,
              textAlign: TextAlign.center,
              style: TextStyle(
                color: palette.ink,
                fontSize: 13.5,
                height: 1.7,
                fontFamily: HarajTheme.fontFamily,
              ),
            ),
          ),
          const SizedBox(height: 18),

          // زرُّ واتساب — أخضرُ العلامة.
          Material(
            color: Colors.transparent,
            child: InkWell(
              borderRadius: BorderRadius.circular(14),
              onTap: () => _openWhatsApp(context, l10n),
              child: Ink(
                padding: const EdgeInsets.symmetric(vertical: 15),
                decoration: BoxDecoration(
                  color: whatsAppGreen,
                  borderRadius: BorderRadius.circular(14),
                  boxShadow: <BoxShadow>[
                    BoxShadow(
                      color: whatsAppGreen.withValues(alpha: 0.35),
                      blurRadius: 12,
                      offset: const Offset(0, 4),
                    ),
                  ],
                ),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: <Widget>[
                    Text(
                      l10n.supportWhatsApp,
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 15,
                        fontWeight: FontWeight.w700,
                        fontFamily: HarajTheme.fontFamily,
                      ),
                    ),
                    const SizedBox(width: 10),
                    const Icon(whatsApp, color: Colors.white, size: 20),
                  ],
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
