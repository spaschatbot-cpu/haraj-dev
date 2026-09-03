import '../../core/environment.dart';
import '../../l10n/generated/app_localizations.dart';
import 'environment_label.dart';

/// يختم أي رسالة تظهر للمستخدم باسم بيئتها في كل بناء غير إنتاجي (المادة ٥-٦).
///
/// **لماذا على الرسالة نفسها لا على اللافتة وحدها:** اللافتة في زاوية الشاشة،
/// وإشعار المزايدة يصل والجوال في الجيب أو التطبيق في الخلفية، فلا لافتة معه.
/// في v1 وصلت رسالة اختبار إلى عميل حقيقي فتصرّف على أساسها؛ ما يمنع تكرارها
/// أن تحمل **الرسالة** اسم بيئتها، لا أن تحمله الشاشة التي قد لا تُرى.
///
/// الإنتاج بلا ختم: ختمٌ يظهر لعميل حقيقي ضجيج، والإنتاج هو الحالة التي لا
/// تحتاج تحذيراً.
String stampEnvironment(
  AppLocalizations l10n,
  AppEnvironment environment,
  String message,
) => environment.showsBanner
    ? l10n.environmentStampedMessage(
        environmentLabel(l10n, environment),
        message,
      )
    : message;
