import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

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
  });

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
}
