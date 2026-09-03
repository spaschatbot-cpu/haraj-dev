import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app/providers.dart';
import '../../domain/common/failure.dart';
import '../../domain/wallet/entities/top_up.dart';

/// حالة شاشة الشحن.
///
/// ما ليس فيها مقصود بقدر ما فيها: **لا حقل «نجح»** يضبطه التطبيق. النجاح صفة
/// في `intent` جاءت من الخادم، وأي علم محلي بجانبها كان سيصير مصدراً ثانياً
/// للحقيقة — وهو تحديداً ما جعل رابط عودة مزوَّراً يغيّر رصيداً في v1.
final class TopUpState {
  const TopUpState({
    this.intent,
    this.gatewayOpened = true,
    this.isBusy = false,
    this.failure,
  });

  /// نيّة الشحن الجارية، إن بدأت.
  final TopUp? intent;

  /// هل فُتحت صفحة الدفع فعلاً على الجهاز.
  final bool gatewayOpened;

  final bool isBusy;

  /// عطب آخر محاولة (بدء أو سؤال عن الحالة).
  final Failure? failure;

  TopUpState copyWith({
    TopUp? intent,
    bool? gatewayOpened,
    bool? isBusy,
    Failure? failure,
    bool clearFailure = false,
  }) => TopUpState(
    intent: intent ?? this.intent,
    gatewayOpened: gatewayOpened ?? this.gatewayOpened,
    isBusy: isBusy ?? this.isBusy,
    failure: clearFailure ? null : failure ?? this.failure,
  );
}

final topUpControllerProvider =
    NotifierProvider.autoDispose<TopUpController, TopUpState>(
      TopUpController.new,
    );

/// يبدأ الشحن، ويسأل الخادم عن نتيجته. لا شيء غير ذلك.
final class TopUpController extends Notifier<TopUpState> {
  @override
  TopUpState build() => const TopUpState();

  /// يكتب النيّة عند الخادم ثم يسلّم العميل إلى البوابة.
  Future<void> start() async {
    state = state.copyWith(isBusy: true, clearFailure: true);
    try {
      final handoff = await ref.read(startCardTopUpProvider)();
      state = TopUpState(
        intent: handoff.intent,
        gatewayOpened: handoff.gatewayOpened,
      );
    } on Failure catch (failure) {
      state = state.copyWith(isBusy: false, failure: failure);
    }
  }

  /// يسأل الخادم: ماذا صار بهذه النيّة؟
  ///
  /// تُستدعى عند العودة إلى التطبيق وبضغطة صريحة. في الحالتين المصدر واحد:
  /// نقطة الخادم بمرجع النيّة. لا شيء هنا يقرأ رابطاً ولا معاملاً فيه.
  Future<void> checkStatus() async {
    final reference = state.intent?.reference;
    if (reference == null || state.isBusy) return;

    state = state.copyWith(isBusy: true, clearFailure: true);
    try {
      final intent = await ref.read(readTopUpStatusProvider)(reference);
      state = state.copyWith(intent: intent, isBusy: false);
    } on Failure catch (failure) {
      // انقطاع أثناء السؤال يبقي النيّة معروضة بحالتها الأخيرة المعروفة —
      // ولا يُقرأ الانقطاع نجاحاً ولا فشلاً في الدفع.
      state = state.copyWith(isBusy: false, failure: failure);
    }
  }

  /// يفتح صفحة الدفع ثانية بالمرجع نفسه، بلا إنشاء نيّة جديدة.
  ///
  /// نيّة جديدة لكل ضغطة تترك عند الخادم صفوفاً معلَّقة لا يقابلها دفع.
  Future<void> openGatewayAgain() async {
    final intent = state.intent;
    if (intent == null) return;
    final opened = await ref
        .read(checkoutLauncherProvider)
        .open(intent.checkoutUrl);
    state = state.copyWith(gatewayOpened: opened);
  }
}
