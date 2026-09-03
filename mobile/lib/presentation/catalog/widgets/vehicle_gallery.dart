import 'package:flutter/material.dart';

import '../../../l10n/generated/app_localizations.dart';
import 'remote_image.dart';

/// معرض صور المركبة (T709).
///
/// **الصور قد تكون كثيرة**، فالمعرض `PageView.builder`: الصفحة تُبنى عند
/// الوصول إليها، فلا تُنزَّل عشرون صورة كاملة لأن العميل فتح الصفحة. وفشلُ
/// صورةٍ يبقى في مكانها (`RemoteImage`) ولا يرفع شاشة خطأ فوق المركبة كلها.
///
/// وغيابُ الصور حالةٌ لا عطل: مركبةٌ لم تُصوَّر بعد تُعرض بنصّ يقول ذلك.
class VehicleGallery extends StatefulWidget {
  const VehicleGallery({required this.imageUrls, super.key});

  final List<String> imageUrls;

  @override
  State<VehicleGallery> createState() => _VehicleGalleryState();
}

class _VehicleGalleryState extends State<VehicleGallery> {
  int _index = 0;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);

    if (widget.imageUrls.isEmpty) {
      return AspectRatio(
        aspectRatio: 4 / 3,
        child: Center(
          child: Text(l10n.vehicleNoImages, textAlign: TextAlign.center),
        ),
      );
    }

    return Column(
      children: <Widget>[
        AspectRatio(
          aspectRatio: 4 / 3,
          child: PageView.builder(
            itemCount: widget.imageUrls.length,
            onPageChanged: (index) => setState(() => _index = index),
            itemBuilder: (context, index) =>
                RemoteImage(url: widget.imageUrls[index], fit: BoxFit.contain),
          ),
        ),
        if (widget.imageUrls.length > 1)
          Padding(
            padding: const EdgeInsets.only(top: 8),
            child: Text(
              l10n.vehicleImageCounter(_index + 1, widget.imageUrls.length),
              style: Theme.of(context).textTheme.bodySmall,
            ),
          ),
      ],
    );
  }
}
