import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app/providers.dart';

/// حالة الجلسة كما يراها التوجيه.
enum SessionState {
  /// لم يُسأل التخزين الآمن بعد — لحظة الإقلاع وحدها.
  ///
  /// حالة ثالثة مقصودة: بلا هذه اللحظة يبدأ التطبيق «مسجَّل الخروج» فيومض
  /// المستخدمُ العائدُ على شاشة دخول لا يحتاجها، ثم يُقذف منها.
  unknown,

  signedIn,

  signedOut,

  /// كان داخلاً ثم سقطت جلسته — 401 لم ينفع معه التجديد.
  ///
  /// حالة مستقلة عن `signedOut` لأن الشاشة تقول له لماذا وجد نفسه هنا. من
  /// قُذف إلى شاشة الدخول بلا سبب يظنّ التطبيق تعطّل.
  expired,
}

final sessionControllerProvider =
    NotifierProvider<SessionController, SessionState>(SessionController.new);

/// من يقرّر أن المستخدم داخل أو خارج — نقطة واحدة يقرأ منها الموجّه.
///
/// السقوط لا يأتي من شاشة: `SessionSignal` يرفعه اعتراض المصادقة بعد 401 لم
/// ينفع معه التجديد. الشاشات لا تعرف 401 أصلاً.
final class SessionController extends Notifier<SessionState> {
  @override
  SessionState build() {
    final subscription = ref
        .watch(sessionSignalProvider)
        .lost
        .listen((_) => state = SessionState.expired);
    ref.onDispose(subscription.cancel);

    // القراءة من التخزين الآمن غير متزامنة، والحالة الابتدائية `unknown`
    // ريثما تصل — لا حزر ولا افتراض.
    unawaited(_restore());
    return SessionState.unknown;
  }

  Future<void> _restore() async {
    final hasSession = await ref
        .read(authRepositoryProvider)
        .hasStoredSession();
    state = hasSession ? SessionState.signedIn : SessionState.signedOut;
  }

  /// بعد تحقّق ناجح: الرمزان محفوظان فعلاً في التخزين الآمن.
  void markSignedIn() => state = SessionState.signedIn;

  Future<void> signOut() async {
    await ref.read(authRepositoryProvider).signOut();
    state = SessionState.signedOut;
  }
}
