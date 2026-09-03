import 'package:flutter/material.dart';

import '../../../l10n/generated/app_localizations.dart';

/// صورة من الشبكة، **بحالة فشل خاصة بها**.
///
/// السبب المباشر: مركبة قد تحمل عشرين صورة، وصورةٌ واحدة تسقط لأن ملفها ناقص
/// على التخزين. لو رفعت الشاشة عندها شاشة خطأ لاختفت المركبة كلها بسبب صورة —
/// فالفشل يبقى في مكان الصورة وحدها والباقي يُعرض.
///
/// **التحميل كسول وله ذاكرة مؤقتة:** `Image.network` يمرّ على `ImageCache` في
/// Flutter، والقوائم تبنيه عند ظهور العنصر لا قبله، فمئتا مركبة لا تعني مئتي
/// تنزيل. و`cacheWidth` يفكّ ترميز المصغَّرة بحجمها المعروض لا بحجمها الأصلي —
/// وهو الفرق بين قائمة تمرّ عند 60 إطاراً وقائمة تلتهم الذاكرة (H2).
class RemoteImage extends StatelessWidget {
  const RemoteImage({
    required this.url,
    this.fit = BoxFit.cover,
    this.decodeWidth,
    super.key,
  });

  /// `null` يعني «لا صورة أصلاً» — وهي حالة أخرى غير «صورة فشلت»، وتُعرض بنصّ
  /// آخر: الأولى حقيقة عن المركبة، والثانية عطبٌ مؤقّت.
  final String? url;

  final BoxFit fit;

  /// عرض فكّ الترميز بالبكسل. يُمرَّر للمصغَّرات في القوائم.
  final int? decodeWidth;

  @override
  Widget build(BuildContext context) {
    final address = url;
    if (address == null || address.isEmpty) {
      return _Placeholder(text: AppLocalizations.of(context).vehicleNoImage);
    }

    return Image.network(
      address,
      fit: fit,
      cacheWidth: decodeWidth,
      errorBuilder: (context, error, stackTrace) =>
          _Placeholder(text: AppLocalizations.of(context).vehicleImageFailed),
      loadingBuilder: (context, child, progress) => progress == null
          ? child
          : const Center(child: CircularProgressIndicator()),
    );
  }
}

class _Placeholder extends StatelessWidget {
  const _Placeholder({required this.text});

  final String text;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return ColoredBox(
      color: theme.colorScheme.surfaceContainerHighest,
      child: Center(
        child: Padding(
          padding: const EdgeInsets.all(8),
          child: Text(
            text,
            textAlign: TextAlign.center,
            style: theme.textTheme.bodySmall,
          ),
        ),
      ),
    );
  }
}
