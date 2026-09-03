import 'package:flutter/material.dart';

import '../../core/environment.dart';
import '../../domain/notifications/entities/push_notification.dart';
import '../../l10n/generated/app_localizations.dart';
import 'environment_stamp.dart';

/// يعرض إشعاراً وصل والتطبيق مفتوح، بلا أن ينقل المستخدم عن شاشته.
///
/// **لا تنقّل تلقائي في المقدمة**: مستخدم يزايد الآن وإصبعه على الزرّ، وقفزةٌ
/// تحته تفقده اللحظة التي تعنيه. الفتح زرّ يضغطه هو.
///
/// النصّ يأتي من الخادم كما كتبه — لا صياغة ثانية في التطبيق (نفس قاعدة
/// `FailureView`: من كتب القاعدة كتب نصّها). ما يضيفه التطبيق شيء واحد: ختم
/// البيئة في كل بناء غير إنتاجي (المادة ٥-٦).
///
/// إشعار بيانات صامت (بلا عنوان ولا نصّ) لا يُعرض: لا شيء فيه يُقرأ. تُرجع
/// الدالة `false` فيبقى الفرع مسمّى ولا ينتهي بصمت.
bool showPushBanner(
  ScaffoldMessengerState messenger, {
  required PushNotification notification,
  required AppLocalizations l10n,
  required AppEnvironment environment,
  required VoidCallback onOpen,
}) {
  final text = notification.body ?? notification.title;
  if (text == null || text.trim().isEmpty) return false;

  messenger.showSnackBar(
    SnackBar(
      content: Text(stampEnvironment(l10n, environment, text)),
      action: SnackBarAction(label: l10n.pushOpen, onPressed: onOpen),
    ),
  );
  return true;
}
