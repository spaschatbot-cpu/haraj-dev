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
///
/// **تصميمُ الزجاج الأبيض بطلب المالك (٣ أكتوبر ٢٠٢٦)**: كلُّ كتلةٍ كرتٌ
/// زجاجيٌّ واحد (`cardSurface` الشفّاف بحدٍّ فاتح)، وسقطت الأرضيّاتُ الملوّنة
/// والاستروكاتُ الجانبيّة — فوق التدرّج تُقرأ ألوانُها بقعاً لا زجاجاً. وبقيت
/// ألوانُ اللهجة في مربّعات الأيقونات وحدها، فتبقى لكلّ قيمةٍ هويّتُها.
class AboutUsScreen extends StatelessWidget {
  const AboutUsScreen({super.key});

  // ألوانُ لهجةٍ للبطاقات — لكلٍّ معناه في التصميم.
  static const _amber = Color(0xFF84560C);
  static const _blue = Color(0xFF1E3A5F);
  static const _pink = Color(0xFFB42335);
  static const _green = Color(0xFF13795F);
  static const _purple = Color(0xFF35577F);
  static const _orange = Color(0xFFB7791F);

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
          24 + MediaQuery.paddingOf(context).bottom,
        ),
        children: <Widget>[
          const _IntroBox(
            // حُذف عنوانُ «من نحن؟» من البطاقة بطلب المالك (١٣ سبتمبر ٢٠٢٦) —
            // يكفي عنوانُ الشاشة في الشريط، وبقي الشرحُ وحده.
            body:
                'نحن شركة رائدة في مجال التجارة الإلكترونية والخدمات '
                'اللوجستية في المملكة.',
            icon: Icons.location_on,
          ),
          const SizedBox(height: 12),
          _GlassCard(
            palette: palette,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text(
                  'شركة حراج واحد للخدمات اللوجستية',
                  style: TextStyle(
                    color: palette.gold,
                    fontSize: 17,
                    fontWeight: FontWeight.w800,
                    height: 1.5,
                    fontFamily: HarajTheme.fontFamily,
                  ),
                ),
                const SizedBox(height: 8),
                Text(
                  'شركة حراج واحد للخدمات اللوجستية هي شركة سعودية تتيح خدمات '
                  'البيع والشراء عبر مزادات إلكترونية موثوقة، وتقدّم حلولاً '
                  'لوجستية متكاملة تخدم البائع والمشتري.',
                  style: TextStyle(
                    color: palette.inkMuted,
                    fontSize: 13.5,
                    height: 1.6,
                    fontFamily: HarajTheme.fontFamily,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 12),
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
          const SizedBox(height: 12),
          _StrokeCard(
            title: 'منصة إلكترونية متطورة',
            body:
                'نسعى للتميّز والابتكار في تقديم حلول لوجستية ذكية تخدم '
                'تطلّعات عملائنا.',
            icon: Icons.laptop_mac_rounded,
            accent: palette.gold,
            palette: palette,
          ),
          _StrokeCard(
            title: 'شفافية كاملة في المزادات المفتوحة',
            body:
                'نسعى للتميّز والابتكار في تقديم حلول لوجستية ذكية تخدم '
                'تطلّعات عملائنا.',
            icon: Icons.lock_outline_rounded,
            accent: _orange,
            palette: palette,
          ),
          _StrokeCard(
            title: 'سرية تامة لمزادات المظاريف المغلقة',
            body:
                'نسعى للتميّز والابتكار في تقديم حلول لوجستية ذكية تخدم '
                'تطلّعات عملائنا.',
            icon: Icons.visibility_outlined,
            accent: _green,
            palette: palette,
          ),
          _StrokeCard(
            title: 'دعم فني متميّز 24/7',
            body:
                'نسعى للتميّز والابتكار في تقديم حلول لوجستية ذكية تخدم '
                'تطلّعات عملائنا.',
            icon: Icons.headset_mic_outlined,
            accent: _blue,
            palette: palette,
          ),
          const SizedBox(height: 12),

          _SectionHeader(
            title: 'قيمنا',
            icon: Icons.diamond_outlined,
            palette: palette,
          ),
          const SizedBox(height: 12),
          // القيمُ الخمس في كرتٍ واحدٍ بفواصل لا خمسِ بطاقاتٍ ملوّنة — قائمةٌ
          // قصيرةُ الأسطر تُقرأ قائمةً، والكروتُ المتراكبة تُقرأ ضجيجاً.
          _GlassCard(
            palette: palette,
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
            child: _Rows(
              palette: palette,
              children: <Widget>[
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
              ],
            ),
          ),
          const SizedBox(height: 24),

          _SectionHeader(
            title: 'لماذا نحن؟',
            icon: Icons.auto_awesome_rounded,
            palette: palette,
          ),
          const SizedBox(height: 12),
          _GlassCard(
            palette: palette,
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
            child: _Rows(
              palette: palette,
              children: <Widget>[
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
          ),
        ],
      ),
    );
  }
}

/// الكرتُ الزجاجيّ — الوعاءُ الواحد لكلّ كتلةٍ في الصفحة، على مقاس كروت
/// تفاصيل المركبة وشاشة الدخول (٢٠ نصفَ قطر، حدٌّ فاتح، ظلٌّ ناعم).
class _GlassCard extends StatelessWidget {
  const _GlassCard({
    required this.palette,
    required this.child,
    this.padding = const EdgeInsets.all(16),
  });

  final HarajPalette palette;
  final Widget child;
  final EdgeInsets padding;

  @override
  Widget build(BuildContext context) => Container(
    padding: padding,
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

/// أسطرٌ داخل كرتٍ واحد، بينها فاصلٌ شعريّ.
class _Rows extends StatelessWidget {
  const _Rows({required this.palette, required this.children});

  final HarajPalette palette;
  final List<Widget> children;

  @override
  Widget build(BuildContext context) => Column(
    children: <Widget>[
      for (var i = 0; i < children.length; i++) ...<Widget>[
        if (i > 0)
          Divider(
            height: 1,
            thickness: 1,
            color: palette.navInactive.withValues(alpha: 0.6),
          ),
        children[i],
      ],
    ],
  );
}

/// مربّعُ الأيقونة — زرقةٌ شفّافة بزوايا ١٠، لغةُ أيقونات الزجاج كلِّها.
class _IconTile extends StatelessWidget {
  const _IconTile({required this.icon, required this.color, this.size = 40});

  final IconData icon;
  final Color color;
  final double size;

  @override
  Widget build(BuildContext context) => Container(
    width: size,
    height: size,
    alignment: Alignment.center,
    decoration: BoxDecoration(
      borderRadius: BorderRadius.circular(10),
      color: color.withValues(alpha: 0.08),
    ),
    child: Icon(icon, color: color, size: size * 0.52),
  );
}

/// صندوقُ التعريف العلويّ — كرتٌ زجاجيٌّ، الشرحُ وبجانبه الدبّوس.
class _IntroBox extends StatelessWidget {
  const _IntroBox({required this.body, required this.icon});

  final String body;
  final IconData icon;

  @override
  Widget build(BuildContext context) {
    final palette = HarajPalette.of(context);
    return _GlassCard(
      palette: palette,
      child: Row(
        children: <Widget>[
          Expanded(
            child: Text(
              body,
              style: TextStyle(
                color: palette.ink,
                fontSize: 14,
                fontWeight: FontWeight.w600,
                height: 1.6,
                fontFamily: HarajTheme.fontFamily,
              ),
            ),
          ),
          const SizedBox(width: 14),
          Container(
            width: 48,
            height: 48,
            alignment: Alignment.center,
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(12),
              color: palette.gold.withValues(alpha: 0.08),
            ),
            child: const Text('📍', style: TextStyle(fontSize: 22)),
          ),
        ],
      ),
    );
  }
}

/// صفٌّ معلومةٍ في كرتٍ زجاجيّ — أيقونةٌ وتسميةٌ فوق قيمة.
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
  Widget build(BuildContext context) => _GlassCard(
    palette: palette,
    child: Row(
      children: <Widget>[
        _IconTile(icon: icon, color: palette.gold, size: 44),
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
                  fontFamily: HarajTheme.fontFamily,
                ),
              ),
              const SizedBox(height: 2),
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
  Widget build(BuildContext context) => _GlassCard(
    palette: palette,
    child: Column(
      children: <Widget>[
        _IconTile(icon: icon, color: palette.gold, size: 36),
        const SizedBox(height: 10),
        Text(
          label,
          style: TextStyle(
            color: palette.inkMuted,
            fontSize: 12.5,
            fontFamily: HarajTheme.fontFamily,
          ),
        ),
        const SizedBox(height: 2),
        Directionality(
          textDirection: TextDirection.ltr,
          child: Text(
            value,
            style: TextStyle(
              color: palette.ink,
              fontSize: 22,
              fontWeight: FontWeight.w800,
              height: 1.2,
              fontFamily: HarajTheme.fontFamily,
            ),
          ),
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

/// عنوانُ قسمٍ — مربّعُ أيقونةٍ أزرق وعنوانٌ، وسطرُ شرحٍ اختياريّ.
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
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.symmetric(horizontal: 4),
    child: Row(
      children: <Widget>[
        // الشارةُ أوّلاً = يمينُ RTL، بطلب المالك (١٣ سبتمبر ٢٠٢٦).
        _IconTile(icon: icon, color: palette.gold, size: 36),
        const SizedBox(width: 12),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Text(
                title,
                style: TextStyle(
                  color: palette.ink,
                  fontSize: 16,
                  fontWeight: FontWeight.w700,
                  fontFamily: HarajTheme.fontFamily,
                ),
              ),
              if (subtitle case final String line) ...<Widget>[
                const SizedBox(height: 2),
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
    ),
  );
}

/// بطاقةُ رؤيةٍ — كرتٌ زجاجيّ: مربّعُ أيقونةٍ بلون لهجتها، وعنوانٌ وشرحٌ
/// بجانبه. (كان استروكاً جانبيّاً ملوّناً قبل الزجاج.)
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
    child: _GlassCard(
      palette: palette,
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          _IconTile(icon: icon, color: accent, size: 44),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text(
                  title,
                  style: TextStyle(
                    color: palette.ink,
                    fontSize: 15,
                    fontWeight: FontWeight.w700,
                    height: 1.4,
                    fontFamily: HarajTheme.fontFamily,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  body,
                  style: TextStyle(
                    color: palette.inkMuted,
                    fontSize: 13.5,
                    height: 1.6,
                    fontFamily: HarajTheme.fontFamily,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    ),
  );
}

/// سطرُ قيمةٍ داخل كرت القيم — مربّعُ أيقونةٍ بلون لهجتها ونصٌّ بالحبر.
///
/// النصُّ بالحبر لا بلون اللهجة: الورديُّ والبنفسجيُّ على الزجاج الفاتح
/// يضعفان قراءةً، واللونُ يكفيه المربّع.
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
    padding: const EdgeInsets.symmetric(vertical: 12),
    child: Row(
      children: <Widget>[
        // الأيقونةُ أوّلاً = يمينُ RTL، بطلب المالك (١٣ سبتمبر ٢٠٢٦).
        _IconTile(icon: icon, color: accent, size: 38),
        const SizedBox(width: 12),
        Expanded(
          child: Text(
            text,
            style: TextStyle(
              color: palette.ink,
              fontSize: 14,
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

/// سطرُ «لماذا نحن» — علامةُ صحٍّ زرقاء ونصّ.
class _CheckCard extends StatelessWidget {
  const _CheckCard({required this.text, required this.palette});

  final String text;
  final HarajPalette palette;

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.symmetric(vertical: 12),
    child: Row(
      children: <Widget>[
        Container(
          width: 24,
          height: 24,
          alignment: Alignment.center,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            color: palette.gold.withValues(alpha: 0.12),
          ),
          child: Icon(Icons.check_rounded, color: palette.gold, size: 16),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: Text(
            text,
            style: TextStyle(
              color: palette.ink,
              fontSize: 14,
              fontWeight: FontWeight.w500,
              height: 1.5,
              fontFamily: HarajTheme.fontFamily,
            ),
          ),
        ),
      ],
    ),
  );
}
