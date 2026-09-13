import 'package:flutter/material.dart';

import '../../app/theme.dart';
import '../../l10n/generated/app_localizations.dart';
import 'account_page_scaffold.dart';

/// صفحة «من نحن» — على تصميم المالك (١٣ سبتمبر ٢٠٢٦): تعريفٌ بالشركة، الموقع،
/// أرقامٌ عنها، ثم الرؤية والقيم و«لماذا نحن».
///
/// **النصوصُ عربيّةٌ في الملف لا في `arb`**: هذه صفحةُ تعريفٍ تسويقيّةٌ ثابتة،
/// والتطبيقُ عربيٌّ فعليّاً (الإنجليزيّة «ليست لغة منتَج» — `l10n.yaml`). نقلُها
/// إلى الترجمة يعني نحو أربعين مفتاحاً بترجمةٍ إنجليزيّةٍ لا تُعرَض؛ فإن صارت
/// الإنجليزيّةُ لغةَ منتَجٍ يوماً نُقلت كتلةً واحدة.
class AboutUsScreen extends StatelessWidget {
  const AboutUsScreen({super.key});

  // ألوانُ لهجةٍ للبطاقات — لكلٍّ معناه في التصميم.
  static const _amber = Color(0xFFB8860B);
  static const _blue = Color(0xFF1C6FD6);
  static const _pink = Color(0xFFC2185B);
  static const _green = Color(0xFF2E7D5B);
  static const _purple = Color(0xFF6A4CB0);
  static const _orange = Color(0xFFE07A2F);

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final palette = HarajPalette.of(context);

    return AccountPageScaffold(
      title: l10n.accountMenuAbout,
      child: ListView(
        padding: EdgeInsets.fromLTRB(
          16,
          16,
          16,
          16 + MediaQuery.paddingOf(context).bottom,
        ),
        children: <Widget>[
          _IntroBox(
            title: 'من نحن؟',
            body: 'نحن شركة رائدة في مجال التجارة الإلكترونية والخدمات '
                'اللوجستية في المملكة.',
            icon: Icons.location_on,
          ),
          const SizedBox(height: 20),
          Text(
            'شركة حراج واحد للخدمات اللوجستية',
            style: TextStyle(
              color: palette.gold,
              fontSize: 19,
              fontWeight: FontWeight.w800,
              height: 1.5,
              fontFamily: HarajTheme.fontFamily,
            ),
          ),
          const SizedBox(height: 10),
          Text(
            'شركة حراج واحد للخدمات اللوجستية هي شركة سعودية تتيح خدمات البيع '
            'والشراء عبر مزادات إلكترونية موثوقة، وتقدّم حلولاً لوجستية متكاملة '
            'تخدم البائع والمشتري.',
            style: TextStyle(
              color: palette.inkMuted,
              fontSize: 14,
              height: 1.8,
              fontFamily: HarajTheme.fontFamily,
            ),
          ),
          const SizedBox(height: 16),
          _InfoTile(
            label: 'موقعنا',
            value: 'الرياض — طريق الحائر',
            icon: Icons.location_on_outlined,
            palette: palette,
          ),
          const SizedBox(height: 12),
          Row(
            children: <Widget>[
              Expanded(
                child: _StatBox(
                  label: 'فريقنا',
                  value: '+80',
                  suffix: 'محترفاً',
                  icon: Icons.groups_outlined,
                  palette: palette,
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: _StatBox(
                  label: 'خبرتنا',
                  value: '+17',
                  suffix: 'عاماً',
                  icon: Icons.access_time_rounded,
                  palette: palette,
                ),
              ),
            ],
          ),
          const SizedBox(height: 24),

          _SectionHeader(
            title: 'رؤيتنا',
            subtitle: 'نسعى إلى أن نكون المنصة الأولى للمزادات في المملكة.',
            icon: Icons.track_changes_rounded,
            palette: palette,
          ),
          const SizedBox(height: 14),
          _StrokeCard(
            title: 'منصة إلكترونية متطورة',
            body: 'نسعى للتميّز والابتكار في تقديم حلول لوجستية ذكية تخدم '
                'تطلّعات عملائنا.',
            icon: Icons.laptop_mac_rounded,
            accent: palette.gold,
            palette: palette,
          ),
          _StrokeCard(
            title: 'شفافية كاملة في المزادات المفتوحة',
            body: 'نسعى للتميّز والابتكار في تقديم حلول لوجستية ذكية تخدم '
                'تطلّعات عملائنا.',
            icon: Icons.lock_outline_rounded,
            accent: _orange,
            palette: palette,
          ),
          _StrokeCard(
            title: 'سرية تامة لمزادات المظاريف المغلقة',
            body: 'نسعى للتميّز والابتكار في تقديم حلول لوجستية ذكية تخدم '
                'تطلّعات عملائنا.',
            icon: Icons.visibility_outlined,
            accent: _green,
            palette: palette,
          ),
          _StrokeCard(
            title: 'دعم فني متميّز 24/7',
            body: 'نسعى للتميّز والابتكار في تقديم حلول لوجستية ذكية تخدم '
                'تطلّعات عملائنا.',
            icon: Icons.headset_mic_outlined,
            accent: _blue,
            palette: palette,
          ),
          const SizedBox(height: 24),

          _SectionHeader(
            title: 'قيمنا',
            icon: Icons.diamond_outlined,
            palette: palette,
          ),
          const SizedBox(height: 14),
          _SoftCard(
            text: 'الشفافية: في التعامل مع المستخدمين',
            icon: Icons.verified_user_outlined,
            accent: _amber,
            palette: palette,
          ),
          _SoftCard(
            text: 'الموثوقية: تقديم الخدمة دون تلاعب',
            icon: Icons.groups_2_outlined,
            accent: _blue,
            palette: palette,
          ),
          _SoftCard(
            text: 'الابتكار: تطوير تقني مستمر',
            icon: Icons.bolt_rounded,
            accent: _pink,
            palette: palette,
          ),
          _SoftCard(
            text: 'خدمة العملاء: خدمة تليق بعملائنا',
            icon: Icons.favorite_border_rounded,
            accent: _green,
            palette: palette,
          ),
          _SoftCard(
            text: 'الالتزام: الالتزام بأنظمة المملكة',
            icon: Icons.emoji_events_outlined,
            accent: _purple,
            palette: palette,
          ),
          const SizedBox(height: 24),

          _SectionHeader(
            title: 'لماذا نحن؟',
            icon: Icons.auto_awesome_rounded,
            palette: palette,
          ),
          const SizedBox(height: 14),
          for (final why in const <String>[
            'لا رسوم خفية',
            'خدمات لوجستية متكاملة',
            'سرعة وكفاءة في إنهاء الإجراءات',
            'سهولة الاستخدام: تطبيق ذكي وسهل',
            'انتشار واسع في جميع أنحاء المملكة',
            'أنظمة مراقبة لحماية المستخدمين',
            'دعم فني عبر قنوات متعددة',
            'خدمات إعلانية مميزة ومرفوعة',
          ])
            _CheckCard(text: why, palette: palette),
        ],
      ),
    );
  }
}

/// صندوقُ التعريف العلويّ — أزرقُ فاتحٌ هادئ، أيقونةٌ وعنوانٌ وسطران.
class _IntroBox extends StatelessWidget {
  const _IntroBox({
    required this.title,
    required this.body,
    required this.icon,
  });

  final String title;
  final String body;
  final IconData icon;

  @override
  Widget build(BuildContext context) {
    final palette = HarajPalette.of(context);
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: palette.heroGlow.withValues(alpha: 0.10),
        borderRadius: BorderRadius.circular(18),
      ),
      child: Row(
        children: <Widget>[
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text(
                  title,
                  style: TextStyle(
                    color: palette.ink,
                    fontSize: 18,
                    fontWeight: FontWeight.w800,
                    fontFamily: HarajTheme.fontFamily,
                  ),
                ),
                const SizedBox(height: 6),
                Text(
                  body,
                  style: TextStyle(
                    color: palette.inkMuted,
                    fontSize: 13,
                    height: 1.6,
                    fontFamily: HarajTheme.fontFamily,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(width: 14),
          Container(
            width: 52,
            height: 52,
            alignment: Alignment.center,
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(16),
              color: palette.cardSurface,
            ),
            child: const Text('📍', style: TextStyle(fontSize: 24)),
          ),
        ],
      ),
    );
  }
}

/// صفٌّ معلومةٍ في صندوقٍ خفيف — أيقونةٌ وتسميةٌ فوق قيمة.
class _InfoTile extends StatelessWidget {
  const _InfoTile({
    required this.label,
    required this.value,
    required this.icon,
    required this.palette,
  });

  final String label;
  final String value;
  final IconData icon;
  final HarajPalette palette;

  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.all(14),
    decoration: BoxDecoration(
      color: palette.cardSurface,
      borderRadius: BorderRadius.circular(14),
      boxShadow: <BoxShadow>[
        BoxShadow(
          color: palette.ink.withValues(alpha: 0.05),
          blurRadius: 10,
          offset: const Offset(0, 2),
        ),
      ],
    ),
    child: Row(
      children: <Widget>[
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Text(
                label,
                style: TextStyle(
                  color: palette.inkMuted,
                  fontSize: 12.5,
                  fontFamily: HarajTheme.fontFamily,
                ),
              ),
              const SizedBox(height: 4),
              Text(
                value,
                style: TextStyle(
                  color: palette.ink,
                  fontSize: 15,
                  fontWeight: FontWeight.w700,
                  fontFamily: HarajTheme.fontFamily,
                ),
              ),
            ],
          ),
        ),
        Icon(icon, color: palette.gold, size: 26),
      ],
    ),
  );
}

class _StatBox extends StatelessWidget {
  const _StatBox({
    required this.label,
    required this.value,
    required this.suffix,
    required this.icon,
    required this.palette,
  });

  final String label;
  final String value;
  final String suffix;
  final IconData icon;
  final HarajPalette palette;

  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.all(16),
    decoration: BoxDecoration(
      color: palette.cardSurface,
      borderRadius: BorderRadius.circular(14),
      boxShadow: <BoxShadow>[
        BoxShadow(
          color: palette.ink.withValues(alpha: 0.05),
          blurRadius: 10,
          offset: const Offset(0, 2),
        ),
      ],
    ),
    child: Column(
      children: <Widget>[
        Text(
          label,
          style: TextStyle(
            color: palette.inkMuted,
            fontSize: 12.5,
            fontFamily: HarajTheme.fontFamily,
          ),
        ),
        const SizedBox(height: 8),
        Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: <Widget>[
            Directionality(
              textDirection: TextDirection.ltr,
              child: Text(
                value,
                style: TextStyle(
                  color: palette.ink,
                  fontSize: 22,
                  fontWeight: FontWeight.w800,
                  fontFamily: HarajTheme.fontFamily,
                ),
              ),
            ),
            const SizedBox(width: 6),
            Icon(icon, color: palette.gold, size: 20),
          ],
        ),
        const SizedBox(height: 4),
        Text(
          suffix,
          style: TextStyle(
            color: palette.inkMuted,
            fontSize: 12.5,
            fontFamily: HarajTheme.fontFamily,
          ),
        ),
      ],
    ),
  );
}

/// عنوانُ قسمٍ — شارةٌ ذهبيّةٌ وعنوانٌ، وسطرُ شرحٍ اختياريّ.
class _SectionHeader extends StatelessWidget {
  const _SectionHeader({
    required this.title,
    required this.icon,
    required this.palette,
    this.subtitle,
  });

  final String title;
  final String? subtitle;
  final IconData icon;
  final HarajPalette palette;

  @override
  Widget build(BuildContext context) => Row(
    children: <Widget>[
      // الشارةُ أوّلاً = يمينُ RTL، بطلب المالك (١٣ سبتمبر ٢٠٢٦).
      Container(
        width: 46,
        height: 46,
        alignment: Alignment.center,
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(14),
          color: palette.gold.withValues(alpha: 0.16),
        ),
        child: Icon(icon, color: palette.goldDeep, size: 24),
      ),
      const SizedBox(width: 12),
      Expanded(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Text(
              title,
              style: TextStyle(
                color: palette.ink,
                fontSize: 18,
                fontWeight: FontWeight.w800,
                fontFamily: HarajTheme.fontFamily,
              ),
            ),
            if (subtitle case final String line) ...<Widget>[
              const SizedBox(height: 4),
              Text(
                line,
                style: TextStyle(
                  color: palette.inkMuted,
                  fontSize: 12.5,
                  height: 1.5,
                  fontFamily: HarajTheme.fontFamily,
                ),
              ),
            ],
          ],
        ),
      ),
    ],
  );
}

/// بطاقةُ رؤيةٍ — استروكٌ جانبيٌّ ملوّن، أيقونةٌ فوق عنوانٍ وشرح.
class _StrokeCard extends StatelessWidget {
  const _StrokeCard({
    required this.title,
    required this.body,
    required this.icon,
    required this.accent,
    required this.palette,
  });

  final String title;
  final String body;
  final IconData icon;
  final Color accent;
  final HarajPalette palette;

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.only(bottom: 12),
    child: Container(
      decoration: BoxDecoration(
        color: palette.cardSurface,
        borderRadius: BorderRadius.circular(16),
        boxShadow: <BoxShadow>[
          BoxShadow(
            color: palette.ink.withValues(alpha: 0.05),
            blurRadius: 10,
            offset: const Offset(0, 3),
          ),
        ],
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(16),
        child: IntrinsicHeight(
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: <Widget>[
              Container(width: 5, color: accent),
              Expanded(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.center,
                    children: <Widget>[
                      Container(
                        width: 56,
                        height: 56,
                        alignment: Alignment.center,
                        decoration: BoxDecoration(
                          borderRadius: BorderRadius.circular(16),
                          color: accent.withValues(alpha: 0.12),
                        ),
                        child: Icon(icon, color: accent, size: 28),
                      ),
                      const SizedBox(height: 12),
                      Text(
                        title,
                        textAlign: TextAlign.center,
                        style: TextStyle(
                          color: palette.ink,
                          fontSize: 15.5,
                          fontWeight: FontWeight.w700,
                          fontFamily: HarajTheme.fontFamily,
                        ),
                      ),
                      const SizedBox(height: 6),
                      Text(
                        body,
                        textAlign: TextAlign.center,
                        style: TextStyle(
                          color: palette.inkMuted,
                          fontSize: 13,
                          height: 1.6,
                          fontFamily: HarajTheme.fontFamily,
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
    ),
  );
}

/// بطاقةُ قيمةٍ — أرضيّةٌ ملوّنةٌ خفيفة، نصٌّ وأيقونةٌ في دائرةٍ بيضاء.
class _SoftCard extends StatelessWidget {
  const _SoftCard({
    required this.text,
    required this.icon,
    required this.accent,
    required this.palette,
  });

  final String text;
  final IconData icon;
  final Color accent;
  final HarajPalette palette;

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.only(bottom: 12),
    child: Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: accent.withValues(alpha: 0.10),
        borderRadius: BorderRadius.circular(16),
      ),
      child: Row(
        children: <Widget>[
          // الأيقونةُ أوّلاً = يمينُ RTL، بطلب المالك (١٣ سبتمبر ٢٠٢٦).
          Container(
            width: 44,
            height: 44,
            alignment: Alignment.center,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: palette.cardSurface,
            ),
            child: Icon(icon, color: accent, size: 22),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Text(
              text,
              style: TextStyle(
                color: accent,
                fontSize: 14.5,
                height: 1.5,
                fontWeight: FontWeight.w700,
                fontFamily: HarajTheme.fontFamily,
              ),
            ),
          ),
        ],
      ),
    ),
  );
}

/// بطاقةُ «لماذا نحن» — استروكٌ ذهبيّ، شارةُ صحٍّ ذهبيّة، ونصّ.
class _CheckCard extends StatelessWidget {
  const _CheckCard({required this.text, required this.palette});

  final String text;
  final HarajPalette palette;

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.only(bottom: 12),
    child: Container(
      decoration: BoxDecoration(
        color: palette.cardSurface,
        borderRadius: BorderRadius.circular(14),
        boxShadow: <BoxShadow>[
          BoxShadow(
            color: palette.ink.withValues(alpha: 0.05),
            blurRadius: 10,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(14),
        child: IntrinsicHeight(
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: <Widget>[
              Container(width: 4, color: palette.gold),
              Expanded(
                child: Padding(
                  padding: const EdgeInsets.all(14),
                  child: Row(
                    children: <Widget>[
                      Expanded(
                        child: Text(
                          text,
                          style: TextStyle(
                            color: palette.ink,
                            fontSize: 14.5,
                            fontWeight: FontWeight.w600,
                            fontFamily: HarajTheme.fontFamily,
                          ),
                        ),
                      ),
                      const SizedBox(width: 12),
                      Container(
                        width: 28,
                        height: 28,
                        alignment: Alignment.center,
                        decoration: BoxDecoration(
                          shape: BoxShape.circle,
                          color: palette.gold,
                        ),
                        child: const Icon(
                          Icons.check_rounded,
                          color: Colors.white,
                          size: 18,
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
    ),
  );
}
