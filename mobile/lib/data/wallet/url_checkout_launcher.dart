import 'package:url_launcher/url_launcher.dart';

import '../../domain/wallet/gateways/checkout_launcher.dart';

/// يفتح صفحة الدفع في متصفّح **خارج التطبيق**.
///
/// خارجي لا webview داخلي، ولسببين: صفحة الدفع تحمل شريط العنوان وقفل الأمان
/// اللذين يتحقّق منهما العميل قبل أن يكتب رقم بطاقته، وأي webview نملكه نحن
/// يستطيع أن يقرأ ما يجري فيه — ولا نريد أن نستطيع.
///
/// وهذا الصنف لا يعرف شيئاً عن نتيجة الدفع: يفتح عنواناً ويرجع. النتيجة تُقرأ
/// من الخادم بمرجع النيّة (`ReadTopUpStatus`)، لا مما يعود في الرابط.
final class UrlCheckoutLauncher implements CheckoutLauncher {
  const UrlCheckoutLauncher();

  @override
  Future<bool> open(String url) async {
    final target = Uri.tryParse(url);
    if (target == null) return false;
    try {
      return await launchUrl(target, mode: LaunchMode.externalApplication);
    } on Object {
      // تعذّر الفتح ليس فشلاً في الشحن: النيّة مكتوبة عند الخادم، والشاشة
      // تعرض المحاولة ثانية بالمرجع نفسه بدل أن تُظهر عطباً مالياً لم يقع.
      return false;
    }
  }
}
