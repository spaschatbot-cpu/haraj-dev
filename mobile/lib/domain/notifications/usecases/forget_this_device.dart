import '../../common/failure.dart';
import '../repositories/device_registry.dart';
import '../repositories/push_service.dart';

/// ماذا جرى فعلاً عند إلغاء التسجيل — كل فرع له اسم، ولا فرع صامت.
enum ForgetDeviceOutcome {
  /// الخادم أزال الربط، والمزوّد أبطل الرمز. الحالة الكاملة.
  unregistered,

  /// المزوّد أبطل الرمز، لكن الخادم لم يُبلَّغ (شبكة، أو رفض الطلب).
  ///
  /// الجهاز لن يستقبل شيئاً بعد الآن — إبطال الرمز عند المزوّد كافٍ لذلك —
  /// لكن صفّاً معلّقاً يبقى في الخادم يقول إن هذا الحساب له جهاز يعمل. المادة
  /// ٢-٤: غياب تأكيد ليس تأكيداً، فالحالة تُسمّى ولا تُحسب نجاحاً.
  tokenDeletedButServerNotTold,

  /// لا رمز أصلاً — لم يُسجَّل هذا الجهاز يوماً.
  nothingToForget,
}

/// يُنهي استقبال هذا الجهاز لإشعارات صاحب الجلسة (T716 — الخروج).
///
/// إبطال الرمز محلياً وحده لا يكفي: الصفّ يبقى في الخادم باسم من خرج، فيقرأ
/// تقرير التسليم كأن الرجل ما زال مطمئناً إلى وصول تنبيهاته (المادة ٢-٤).
/// والعكس أيضاً لا يكفي: لو أُبلغ الخادم ولم يُبطَل الرمز، بقي جهاز يحمل رمزاً
/// صالحاً لحساب انتهى.
final class ForgetThisDevice {
  const ForgetThisDevice({
    required PushService push,
    required DeviceRegistry registry,
  }) : _push = push,
       _registry = registry;

  final PushService _push;
  final DeviceRegistry _registry;

  Future<ForgetDeviceOutcome> call() async {
    final token = await _push.currentToken();
    if (token == null) return ForgetDeviceOutcome.nothingToForget;

    var serverTold = true;
    try {
      await _registry.unregister(token: token);
    } on Failure {
      // الخروج لا يُحتجز على الشبكة: مستخدم يريد الخروج من جهاز يسلّمه لغيره
      // الآن لا يُقال له «حاول لاحقاً». نُبطل الرمز على أي حال فينقطع الاستقبال.
      serverTold = false;
    }

    await _push.deleteToken();

    return serverTold
        ? ForgetDeviceOutcome.unregistered
        : ForgetDeviceOutcome.tokenDeletedButServerNotTold;
  }
}
