import 'package:flutter/widgets.dart';

import '../../domain/common/failure.dart';
import '../../l10n/generated/app_localizations.dart';

/// النصّ الذي يُعرض لأي `Failure` — نقطة قرار واحدة في التطبيق كله.
///
/// **القاعدة:** إن تكلّم الخادم، فكلامه هو النصّ. `ApiFailure.message` عربية
/// جاهزة للعرض وتُعاد حرفياً، بلا خريطة رموز ولا استبدال. لو كتبنا نصّاً محلياً
/// لرمز يعرفه الخادم لصار عندنا نسخة ثانية من القاعدة، وأول تعديل في الخلفية
/// يجعل الشاشة تكذب (المادة ٤-٥، وقاعدة التصميم 3 في الفيز 008).
///
/// النصوص المحلية هنا مقصورة على ما **لا يعرفه الخادم**: أنه لم يُسأل أصلاً،
/// أو أن ردّه لم يصل مفهوماً، أو أن العطب في التطبيق نفسه.
String failureMessage(BuildContext context, Failure failure) {
  final l10n = AppLocalizations.of(context);
  return switch (failure) {
    ApiFailure(:final message) => message,
    TransportFailure(:final problem) => switch (problem) {
      TransportProblem.offline => l10n.errorOffline,
      TransportProblem.timeout => l10n.errorTimeout,
      TransportProblem.malformedResponse => l10n.errorMalformedResponse,
    },
    UnexpectedFailure() => l10n.errorUnexpected,
  };
}
