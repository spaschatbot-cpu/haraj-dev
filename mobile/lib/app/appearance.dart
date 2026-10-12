import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/local/appearance_store.dart';
import 'theme.dart';

/// «المظهر» في التطبيق — الإضاءةُ واللونُ الأساسيّ، كدرج «المظهر» في لوحة
/// الموظّفين. طلبُ المالك (١٢ أكتوبر ٢٠٢٦): «ينفع أغيّر ألوان وأعمل فاتح
/// غامق… عوزين نضيف نفس الحتّة في الأبلكيشن».
///
/// **والافتراضُ فاتحٌ كحليّ** لا «تلقائي»: التطبيقُ فاتحٌ دائماً بأمر المالك
/// (٢٩ سبتمبر ٢٠٢٦)، وجهازٌ داكنٌ كان سيفتحه داكناً بلا أن يختار أحد — وهو
/// ما رُفع يومَها. فالداكنُ و«التلقائيّ» لمن يختارهما بيده، كما في اللوحة.
@immutable
class Appearance {
  const Appearance({
    this.mode = ThemeMode.light,
    this.accent = HarajAccent.azure,
  });

  final ThemeMode mode;
  final HarajAccent accent;

  Appearance copyWith({ThemeMode? mode, HarajAccent? accent}) =>
      Appearance(mode: mode ?? this.mode, accent: accent ?? this.accent);

  /// أسماءُ اللوحة نفسُها في التخزين (`auto`/`light`/`dark`).
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

class AppearanceController extends Notifier<Appearance> {
  @override
  Appearance build() {
    // يبدأ بالافتراض ثمّ يُقرأ المحفوظ: القراءةُ غيرُ متزامنة، وشاشةُ البدء
    // تسبق أيَّ شاشةٍ ملوّنة فلا يُرى التبدّل.
    _restore();
    return const Appearance();
  }

  Future<void> _restore() async {
    final saved = await ref.read(appearanceStoreProvider).read();
    state = Appearance(
      mode: Appearance.parseMode(saved.scheme),
      accent: HarajAccent.parse(saved.accent),
    );
  }

  void setMode(ThemeMode mode) => _save(state.copyWith(mode: mode));

  void setAccent(HarajAccent accent) => _save(state.copyWith(accent: accent));

  void _save(Appearance next) {
    state = next;
    ref
        .read(appearanceStoreProvider)
        .write(
          scheme: Appearance.modeName(next.mode),
          accent: next.accent.name,
        );
  }
}

final appearanceProvider = NotifierProvider<AppearanceController, Appearance>(
  AppearanceController.new,
);
