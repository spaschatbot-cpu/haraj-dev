/// إشعار وصل من مزوّد الدفع (FCM)، بشكل لا يعرف FCM.
///
/// الحقول نصّية كما تصل: حمولة الإشعار من الخادم `Map<String, String>` دائماً
/// في FCM، ولا يُفكّ منها رقم ولا مبلغ. أي مبلغ في نصّ الإشعار يُعرض كما كتبه
/// الخادم (المبدأ الحاكم للفيز 008: الشاشة لا تحسب مالاً).
library;

final class PushNotification {
  const PushNotification({required this.data, this.title, this.body});

  /// حمولة البيانات — منها تُشتقّ الوجهة (`resolve_push_destination.dart`).
  final Map<String, String> data;

  /// عنوان ونصّ الإشعار كما كتبهما الخادم. قد يغيبان في إشعار بيانات صامت.
  final String? title;
  final String? body;

  @override
  String toString() => 'PushNotification(${data['type']})';
}
