import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../domain/auth/entities/auth_session.dart';

/// رمز أُرسل وينتظر إدخاله: الرقم الذي ذهب إليه، ومتى ينتهي، ومتى يجوز غيره.
final class PendingSignIn {
  const PendingSignIn({required this.phone, required this.delivery});

  final String phone;
  final CodeDelivery delivery;

  PendingSignIn withDelivery(CodeDelivery delivery) =>
      PendingSignIn(phone: phone, delivery: delivery);
}

final pendingSignInProvider =
    NotifierProvider<PendingSignInController, PendingSignIn?>(
      PendingSignInController.new,
    );

/// حالة بين شاشتَي الدخول، في مزوّد لا في `extra` المسار.
///
/// `extra` في go_router يضيع عند إعادة بناء المسار من رابط أو من استعادة
/// حالة، فتفتح شاشة الرمز بلا رقم تعرفه — ثم تعرض «أرسلنا رمزاً إلى null».
/// هنا تُقرأ الحالة أو لا تكون، والشاشة تعيد التوجيه حين لا تكون.
final class PendingSignInController extends Notifier<PendingSignIn?> {
  @override
  PendingSignIn? build() => null;

  void start({required String phone, required CodeDelivery delivery}) =>
      state = PendingSignIn(phone: phone, delivery: delivery);

  /// بعد إعادة إرسال ناجحة: نفس الرقم، ومهلة جديدة.
  void renew(CodeDelivery delivery) => state = state?.withDelivery(delivery);

  void clear() => state = null;
}
