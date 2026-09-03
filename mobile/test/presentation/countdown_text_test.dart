import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:haraj_mobile/l10n/generated/app_localizations.dart';
import 'package:haraj_mobile/presentation/catalog/widgets/countdown_text.dart';

/// T707 — معيار القبول: **العدّاد صحيح عبر تغيّر اليوم.**
///
/// العدّاد فرقٌ بين لحظتين UTC، لا حسابُ تقويم: هذه الاختبارات تثبت أن عبور
/// منتصف الليل (وعبوره بالتوقيت السعودي، وهو منتصف ليلٍ آخر) لا يغيّر شيئاً في
/// الجواب — ولا يحتاج فرعاً في الشيفرة.
void main() {
  late AppLocalizations ar;

  setUp(() async {
    ar = await AppLocalizations.delegate.load(const Locale('ar'));
  });

  test('أقل من دقيقة تُقال كما هي لا بالثواني', () {
    expect(
      remainingLabel(ar, const Duration(seconds: 40)),
      ar.countdownLessThanMinute,
    );
  });

  test('الوقت الذي مضى يُقال إنه مضى', () {
    expect(
      remainingLabel(ar, const Duration(seconds: -1)),
      ar.countdownElapsed,
    );
    expect(remainingLabel(ar, Duration.zero), ar.countdownElapsed);
  });

  test('دقائق ثم ساعات ثم أيام — أكبر وحدتين وتقف', () {
    expect(
      remainingLabel(ar, const Duration(minutes: 40)),
      ar.countdownMinutes(40),
    );
    expect(
      remainingLabel(ar, const Duration(hours: 2, minutes: 15)),
      ar.countdownHoursMinutes(2, 15),
    );
    expect(
      remainingLabel(ar, const Duration(days: 3, hours: 4, minutes: 50)),
      ar.countdownDaysHours(3, 4),
    );
  });

  test('عبور منتصف الليل لا يقفز بالعدّاد يوماً', () {
    // ٢٣:٥٠ بتوقيت السعودية = ٢٠:٥٠ UTC، والمزاد يبدأ ٠٠:٣٠ من اليوم التالي
    // بتوقيت السعودية. الفرق أربعون دقيقة، لا «يوم واحد» ولا «سالب».
    final now = DateTime.utc(2026, 9, 3, 20, 50);
    final startsAt = DateTime.utc(2026, 9, 3, 21, 30);

    expect(
      remainingLabel(ar, startsAt.difference(now)),
      ar.countdownMinutes(40),
    );
  });

  test('عبور آخر الشهر يُحسب بالفرق لا بترقيم الأيام', () {
    final now = DateTime.utc(2026, 9, 30, 23, 30);
    final endsAt = DateTime.utc(2026, 10, 2, 1, 30);

    expect(
      remainingLabel(ar, endsAt.difference(now)),
      ar.countdownDaysHours(1, 2),
    );
  });
}
