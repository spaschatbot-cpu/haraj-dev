import 'package:flutter/material.dart';

/// ثيم التطبيق.
///
/// الخط عربي **مبنيّ في الحزمة** لا مجلوب من الشبكة: قاعدة العرض 7 في الفيز
/// 008 تشترط أن تعمل كل شاشة بلا اتصال، وخط يُنزَّل وقت التشغيل يجعل أول فتح
/// بلا شبكة يعرض مربّعات فارغة.
abstract final class HarajTheme {
  /// عائلة الخط معرَّفة في `pubspec.yaml` تحت `fonts:`.
  static const String fontFamily = 'IBMPlexSansArabic';

  /// خطوط النظام العربية كاحتياط — لو سقط تحميل الأصل لأي سبب، يبقى النصّ
  /// مقروءاً بدل أن يتحوّل إلى مربّعات.
  static const List<String> _fallbacks = <String>[
    'Noto Naskh Arabic',
    'Geeza Pro',
    'Arial',
  ];

  static ThemeData light() => _build(Brightness.light);

  static ThemeData dark() => _build(Brightness.dark);

  static ThemeData _build(Brightness brightness) {
    final base = ThemeData(
      brightness: brightness,
      colorScheme: ColorScheme.fromSeed(
        seedColor: const Color(0xFF0F5C4A),
        brightness: brightness,
      ),
      useMaterial3: true,
    );

    return base.copyWith(
      textTheme: base.textTheme.apply(
        fontFamily: fontFamily,
        fontFamilyFallback: _fallbacks,
      ),
      primaryTextTheme: base.primaryTextTheme.apply(
        fontFamily: fontFamily,
        fontFamilyFallback: _fallbacks,
      ),
    );
  }
}
