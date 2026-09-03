import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../app/providers.dart';
import '../../../l10n/generated/app_localizations.dart';

/// أي لحظة يعدّ إليها العدّاد.
///
/// القسم الذي يسكنه الكرت هو من يقرّر — لا الكرت: المزادات «الجارية» جاءت من
/// الخادم بسؤالٍ عن الجارية، فالعدّ فيها إلى النهاية؛ و«القادمة» بسؤالٍ عن
/// المجدولة، فالعدّ فيها إلى البداية. التطبيق لا يصنّف مزاداً بنفسه.
enum CountdownTarget { start, end }

/// نصّ ما تبقّى — دالة صافية تُختبَر بلا شاشة ولا مؤقّت.
///
/// تعرض أكبر وحدتين وتقف: «٣ يوم و٤ ساعة» أوضح من «٣ يوم و٤ ساعة و١٢ دقيقة»،
/// ولا أحد يقرأ الثواني في مزادٍ يبدأ بعد أسبوع.
String remainingLabel(AppLocalizations l10n, Duration remaining) {
  if (remaining <= Duration.zero) return l10n.countdownElapsed;
  if (remaining.inMinutes < 1) return l10n.countdownLessThanMinute;
  if (remaining.inHours < 1) return l10n.countdownMinutes(remaining.inMinutes);
  if (remaining.inDays < 1) {
    return l10n.countdownHoursMinutes(
      remaining.inHours,
      remaining.inMinutes % Duration.minutesPerHour,
    );
  }
  return l10n.countdownDaysHours(
    remaining.inDays,
    remaining.inHours % Duration.hoursPerDay,
  );
}

/// عدّاد تنازلي حيّ إلى لحظة بعينها (T707).
///
/// **الفرق بين لحظتين لا حسابَ مناطقَ زمنية:** `target` و`now` كلاهما UTC،
/// وطرحهما صحيح عبر منتصف الليل وعبر تغيّر اليوم بلا استثناء يُكتب له فرع.
/// التاريخ المعروض بجواره هو الذي يُحوَّل إلى التوقيت السعودي، في `SaudiTime`
/// وحدها (المادة ٣-١).
class CountdownText extends ConsumerStatefulWidget {
  const CountdownText({required this.at, required this.target, super.key});

  /// اللحظة المقصودة، بتوقيت UTC.
  final DateTime at;

  final CountdownTarget target;

  @override
  ConsumerState<CountdownText> createState() => _CountdownTextState();
}

class _CountdownTextState extends ConsumerState<CountdownText> {
  Timer? _ticker;

  @override
  void initState() {
    super.initState();
    final tick = ref.read(countdownTickProvider);
    if (tick != null) {
      _ticker = Timer.periodic(tick, (_) => setState(() {}));
    }
  }

  @override
  void dispose() {
    _ticker?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final now = ref.watch(nowProvider)();
    final remaining = widget.at.toUtc().difference(now.toUtc());
    final label = remainingLabel(l10n, remaining);

    return Text(switch (widget.target) {
      CountdownTarget.start => l10n.countdownToStart(label),
      CountdownTarget.end => l10n.countdownToEnd(label),
    }, style: Theme.of(context).textTheme.bodyMedium);
  }
}
