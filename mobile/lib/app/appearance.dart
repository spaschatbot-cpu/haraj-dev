import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/api/dio_factory.dart';
import '../data/local/appearance_store.dart';
import 'providers.dart';
import 'theme.dart';

/// «المظهر» في التطبيق — الإضاءةُ واللونُ الأساسيّ، كدرج «المظهر» في لوحة
/// الموظّفين. طلبُ المالك (١٢ أكتوبر ٢٠٢٦): «ينفع أغيّر ألوان وأعمل فاتح
/// غامق… عوزين نضيف نفس الحتّة في الأبلكيشن».
///
/// ## ومن يتحكّم فيه (١٣ أكتوبر ٢٠٢٦: «ومين يقدر يتحكّم فيها؟ — اعمل»)
///
/// **الإدارةُ من اللوحة** («الإعدادات ← مظهر التطبيق»، `GET /api/v1/appearance/`)
/// تحدّد اللونَ والإضاءةَ لكلّ العملاء، وتقرّر هل يغيّرهما العميل:
///
/// * **مسموحٌ للعميل**: ما اختاره على هاتفه يتقدّم، وما لم يختره يتبع الإدارة.
/// * **ممنوع**: يغيب قسمُ «المظهر» من «حسابي»، ويرى الجميعُ ما قالته الإدارة
///   ولو كان أحدُهم اختار قبلها شيئاً — اختيارُه محفوظٌ ويعود إن أُعيد السماح.
///
/// وقبل أن تقول الإدارةُ شيئاً: فاتحٌ كحليٌّ والعميلُ يختار — ما كان عليه
/// التطبيق. والداكنُ ليس افتراضاً: «فاتحٌ دائماً» بأمر المالك (٢٩ سبتمبر).
@immutable
class Appearance {
  const Appearance({
    this.mode = ThemeMode.light,
    this.accent = HarajAccent.azure,
    this.customersChoose = true,
  });

  final ThemeMode mode;
  final HarajAccent accent;

  /// هل يُعرض قسمُ «المظهر» في «حسابي» — قرارُ الإدارة.
  final bool customersChoose;

  /// أسماءُ اللوحة نفسُها في التخزين وفي الخادم (`auto`/`light`/`dark`).
  static ThemeMode parseMode(String? value) => switch (value) {
    'auto' => ThemeMode.system,
    'dark' => ThemeMode.dark,
    _ => ThemeMode.light,
  };

  static String modeName(ThemeMode mode) => switch (mode) {
    ThemeMode.system => 'auto',
    ThemeMode.dark => 'dark',
    ThemeMode.light => 'light',
  };
}

/// ما قالته الإدارة — من الخادم أو من آخر نسخةٍ محفوظة.
typedef _Policy = ({HarajAccent accent, ThemeMode mode, bool customersChoose});

class AppearanceController extends Notifier<Appearance> {
  _Policy _policy = (
    accent: HarajAccent.azure,
    mode: ThemeMode.light,
    customersChoose: true,
  );
  String? _chosenScheme;
  String? _chosenAccent;

  @override
  Appearance build() {
    // يبدأ بالافتراض ثمّ يُقرأ المحفوظ ثمّ يُسأل الخادم: القراءةُ غيرُ متزامنة،
    // وشاشةُ البدء تسبق أيَّ شاشةٍ ملوّنة فلا يُرى التبدّل.
    _restore();
    return const Appearance();
  }

  AppearanceStore get _store => ref.read(appearanceStoreProvider);

  Future<void> _restore() async {
    final chosen = await _store.readChoice();
    _chosenScheme = chosen.scheme;
    _chosenAccent = chosen.accent;
    final cached = _parsePolicy(await _store.readServer());
    if (cached != null) _policy = cached;
    _publish();
    await _fetchPolicy();
  }

  /// **بلا دخولٍ ولا كاشٍ وسيط**: يُسأل الخادم عند كلّ إقلاع، وفشلُه يُبقي
  /// آخرَ نسخةٍ محفوظة — لونٌ قديمٌ ساعةً أهونُ من شاشةٍ لا تُفتح.
  Future<void> _fetchPolicy() async {
    try {
      final dio = DioFactory.build(
        baseUrl: ref.read(appConfigProvider).apiBaseUrl,
      );
      final response = await dio.get<Map<String, dynamic>>(
        '/api/v1/appearance/',
      );
      final data = response.data;
      if (data == null) return;
      final line =
          '${data['accent']}|${data['mode']}|'
          '${data['customers_choose'] == false ? 0 : 1}';
      final policy = _parsePolicy(line);
      if (policy == null) return;
      _policy = policy;
      _publish();
      await _store.writeServer(line);
    } on Object {
      // بلا شبكة أو خادمٌ قديمٌ بلا هذه النقطة: يبقى ما سبق.
    }
  }

  static _Policy? _parsePolicy(String? line) {
    if (line == null) return null;
    final parts = line.split('|');
    if (parts.length != 3) return null;
    return (
      accent: HarajAccent.parse(parts[0]),
      mode: Appearance.parseMode(parts[1]),
      customersChoose: parts[2] != '0',
    );
  }

  void _publish() {
    final choose = _policy.customersChoose;
    state = Appearance(
      customersChoose: choose,
      mode: choose && _chosenScheme != null
          ? Appearance.parseMode(_chosenScheme)
          : _policy.mode,
      accent: choose && _chosenAccent != null
          ? HarajAccent.parse(_chosenAccent)
          : _policy.accent,
    );
  }

  void setMode(ThemeMode mode) {
    if (!_policy.customersChoose) return;
    _chosenScheme = Appearance.modeName(mode);
    _publish();
    _store.writeScheme(_chosenScheme!);
  }

  void setAccent(HarajAccent accent) {
    if (!_policy.customersChoose) return;
    _chosenAccent = accent.name;
    _publish();
    _store.writeAccent(accent.name);
  }
}

final appearanceProvider = NotifierProvider<AppearanceController, Appearance>(
  AppearanceController.new,
);
