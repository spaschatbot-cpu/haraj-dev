import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../../app/theme.dart';

/// حقلُ جوّالٍ سعوديّ: **الرمزُ مكتوبٌ أمام العميل، وهو يكتب رقمَه**.
///
/// ## العطل الذي وُلد هذا لأجله
///
/// كان الحقلُ فارغاً وتلميحُه `9665xxxxxxxx`، فمن كتب رقمَه **كما يكتبه كلَّ
/// يوم** (`05…`) يُرفَض — ورسالةُ الخادم «الرقم لازم يكون بصيغة 9665XXXXXXXX»
/// تظهر بعد رحلةٍ إلى الشبكة. وقِيس في المتصفّح (١٩ سبتمبر ٢٠٢٦): `0542375553`
/// رُفض، والموقعُ وشاشاتُ اللوحة تقبله لأن `find_by_phone` توحّده.
///
/// وقرارُ المالك: «وحّد دي — اكتب أنت الكود دايماً ظاهر قدّام العميل، وهو
/// يكتب الرقم».
///
/// ## وهذا توحيدٌ لا تحقّق
///
/// شكلُ الرقم قاعدةٌ يملكها الخادم (`PHONE_PATTERN = ^9665\d{8}$`) ويردّ
/// برسالتها العربية. ونسخةٌ منها هنا تفترق عنها عند أوّل تعديل، فيرفض التطبيقُ
/// رقماً يقبله الخادم أو العكس (المادة ٤-٥). **فلا حكمَ هنا على الصحّة** —
/// هذا الحقلُ يوحّد ما كُتب ويرسله، والخادمُ وحدَه يقول أمقبولٌ هو.
///
/// والتوحيدُ ثلاثُ خطواتٍ لا أكثر: تُؤخذ الأرقامُ وحدَها (فاللصقُ من جهات
/// الاتصال يأتي بمسافاتٍ وشرطات)، ويسقط `966` أو `00966` إن لصقه العميلُ كاملاً،
/// ويسقط الصفرُ البادئ. وما بقي يُلحَق بـ`966`.
class SaudiPhoneField extends StatelessWidget {
  const SaudiPhoneField({
    required this.controller,
    required this.label,
    super.key,
    this.enabled = true,
    this.onChanged,
    this.autofocus = false,
    this.boxed = false,
  });

  /// هيئةُ شاشة الدخول (تصميم المالك، ٣٠ سبتمبر ٢٠٢٦): العلمُ و`+966` في
  /// صندوقٍ مظلَّلٍ بحدٍّ فاصل، والأرقامُ كبيرة، بلا تسميةٍ عائمة — الشاشةُ
  /// تقول فوقه ما يُكتب. والهيئةُ الأصليّة باقيةٌ لتغيير الرقم في الحساب.
  final bool boxed;

  final TextEditingController controller;
  final String label;
  final bool enabled;
  final ValueChanged<String>? onChanged;
  final bool autofocus;

  /// رمزُ الدولة كما يُعرَض. ثابتٌ لأن المنصّةَ سعوديّةٌ ورقمُ الجوّال الوحيدُ
  /// الذي يقبله الخادم سعوديّ — وقائمةُ دولٍ منسدلةٌ بخيارٍ واحدٍ صحيحٍ هي
  /// نقرةٌ تُهدَر في كلّ دخول.
  static const String countryCode = '966';

  /// ما يُرسَل إلى الخادم: `9665XXXXXXXX`.
  ///
  /// و`static` ليقرأها من يبني الطلبَ بلا أن يمسك الودجة — الشاشةُ ترسل،
  /// والحقلُ يعرض.
  static String toServerFormat(String typed) {
    var digits = typed.replaceAll(RegExp(r'\D'), '');
    if (digits.startsWith('00$countryCode')) {
      digits = digits.substring(2 + countryCode.length);
    } else if (digits.startsWith(countryCode)) {
      digits = digits.substring(countryCode.length);
    }
    // الصفرُ البادئ صفرُ الاتّصال المحلّيّ (`05…`)، ولا مكانَ له في الصيغة
    // الدوليّة. ويسقط **بعد** رمز الدولة لا قبله: من لصق `+966 05…` كتبها
    // هكذا، والإسقاطان مستقلّان.
    while (digits.startsWith('0')) {
      digits = digits.substring(1);
    }
    return digits.isEmpty ? '' : '$countryCode$digits';
  }

  /// أفارغٌ هو؟ — الحالةُ الوحيدة التي يُعطَّل لها الزرّ (لا شيء يُرسَل أصلاً).
  static bool isBlank(String typed) => toServerFormat(typed).isEmpty;

  @override
  Widget build(BuildContext context) {
    if (boxed) return _boxed(context);
    return TextField(
      controller: controller,
      enabled: enabled,
      autofocus: autofocus,
      keyboardType: TextInputType.phone,
      textDirection: TextDirection.ltr,
      autofillHints: const <String>[AutofillHints.telephoneNumber],
      // أرقامٌ فقط: لوحةُ الجوّال تحمل `+` و`*` و`#`، وحرفٌ منها في الخانة
      // يُرسَل ويُرفَض بعد رحلةِ شبكة.
      inputFormatters: <TextInputFormatter>[
        FilteringTextInputFormatter.digitsOnly,
        // عشرةٌ لا تسعة: من يكتب `05…` يكتب عشرة، ونحن نُسقط الصفر. وحدٌّ
        // أقصرُ كان سيقصّ رقمَه وهو يكتب.
        LengthLimitingTextInputFormatter(10),
      ],
      decoration: InputDecoration(
        labelText: label,
        // **الرمزُ ظاهرٌ دائماً — و`prefixIcon` لا `prefixText`.**
        //
        // `prefixText` **لا يُرسَم والحقلُ فارغٌ غيرُ مركَّز**: تلك قاعدةُ
        // Flutter نفسِها. فالعميلُ يفتح الشاشةَ ولا يرى رمزاً إطلاقاً، ويظهر
        // له `+966` بعد أن يلمس الخانة — أي بعد أن يقرّر ماذا يكتب. قِيس في
        // المتصفّح (١٩ سبتمبر ٢٠٢٦): جُرّب `prefixText` أوّلاً فلم يظهر.
        //
        // وقرارُ المالك «الكود دايماً ظاهر قدّام العميل» يعني **قبل** أن يلمس،
        // و`prefixIcon` ودجةٌ تُرسَم دائماً.
        prefixIcon: Padding(
          padding: const EdgeInsetsDirectional.only(start: 12, end: 8),
          child: Text(
            '+$countryCode',
            textDirection: TextDirection.ltr,
            style: Theme.of(context).textTheme.bodyLarge,
          ),
        ),
        // ودجةُ البادئة تأخذ أقلَّ عرضٍ ممكن: الافتراضيُّ ٤٨ بكسلاً مربّعةً
        // لأيقونة، وهي هنا نصٌّ قصير.
        prefixIconConstraints: const BoxConstraints(minWidth: 0, minHeight: 0),
        hintText: '5XXXXXXXX',
        hintTextDirection: TextDirection.ltr,
        filled: true,
        border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
      ),
      onChanged: onChanged,
    );
  }

  Widget _boxed(BuildContext context) {
    final palette = HarajPalette.of(context);
    OutlineInputBorder edge(Color colour, [double width = 1.4]) =>
        OutlineInputBorder(
          borderRadius: BorderRadius.circular(16),
          borderSide: BorderSide(color: colour, width: width),
        );
    // **الخانةُ كلُّها `ltr`**: رمزُ الدولة على الشمال قبل الرقم كما يُكتب
    // الرقمُ الدوليّ — بطلب المالك (٣٠ سبتمبر ٢٠٢٦). والحدُّ والتدويرُ
    // اتّجاهيّان، فيتبعان البادئةَ حيث وقفت.
    return Directionality(
      textDirection: TextDirection.ltr,
      child: TextField(
        controller: controller,
        enabled: enabled,
        autofocus: autofocus,
        keyboardType: TextInputType.phone,
        textDirection: TextDirection.ltr,
        autofillHints: const <String>[AutofillHints.telephoneNumber],
        inputFormatters: <TextInputFormatter>[
          FilteringTextInputFormatter.digitsOnly,
          LengthLimitingTextInputFormatter(10),
        ],
        style: TextStyle(
          fontFamily: HarajTheme.fontFamily,
          fontSize: 20,
          fontWeight: FontWeight.w600,
          letterSpacing: 1.5,
          color: palette.ink,
        ),
        decoration: InputDecoration(
          prefixIcon: Container(
            margin: const EdgeInsetsDirectional.only(end: 12),
            padding: const EdgeInsets.symmetric(horizontal: 14),
            decoration: BoxDecoration(
              color: palette.pageBackground,
              border: BorderDirectional(
                end: BorderSide(color: palette.navInactive),
              ),
              borderRadius: const BorderRadiusDirectional.horizontal(
                start: Radius.circular(15),
              ),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              textDirection: TextDirection.ltr,
              children: <Widget>[
                // العلمُ رسمٌ لا إيموجي: ويندوز لا يرسم أعلامَ الإيموجي فيكتب
                // «SA» حرفين — قِيس على الموقع في ٢٨ سبتمبر.
                Container(
                  width: 24,
                  height: 16,
                  decoration: BoxDecoration(
                    color: const Color(0xFF006C35),
                    borderRadius: BorderRadius.circular(3),
                  ),
                  alignment: Alignment.center,
                  child: Container(width: 14, height: 1.4, color: Colors.white),
                ),
                const SizedBox(width: 8),
                Text(
                  '+$countryCode',
                  textDirection: TextDirection.ltr,
                  style: TextStyle(
                    fontFamily: HarajTheme.fontFamily,
                    fontSize: 17,
                    fontWeight: FontWeight.w700,
                    color: palette.ink,
                  ),
                ),
              ],
            ),
          ),
          prefixIconConstraints: const BoxConstraints(
            minWidth: 0,
            minHeight: 56,
          ),
          hintText: '5X XXX XXXX',
          hintTextDirection: TextDirection.ltr,
          hintStyle: TextStyle(
            fontFamily: HarajTheme.fontFamily,
            fontSize: 20,
            letterSpacing: 1.5,
            color: palette.inkMuted.withValues(alpha: 0.6),
          ),
          filled: true,
          fillColor: palette.cardSurface,
          contentPadding: const EdgeInsets.symmetric(vertical: 16),
          border: edge(palette.navInactive),
          enabledBorder: edge(palette.navInactive),
          focusedBorder: edge(palette.gold, 1.8),
        ),
        onChanged: onChanged,
      ),
    );
  }
}
