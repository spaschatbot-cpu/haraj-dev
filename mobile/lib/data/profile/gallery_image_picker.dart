import 'package:image_picker/image_picker.dart';

import '../../domain/profile/gateways/image_source_picker.dart';

/// معرضُ الصور، خلف عقد النطاق.
final class GalleryImagePicker implements ImageSourcePicker {
  GalleryImagePicker([ImagePicker? picker]) : _picker = picker ?? ImagePicker();

  final ImagePicker _picker;

  @override
  Future<PickedImage?> pickImage() async {
    final XFile? picked;
    try {
      // **حدٌّ للأبعاد وجودةٌ مضغوطة**: صورةُ خطابٍ من كاميرا هاتفٍ حديث
      // تتجاوز ٨ م.ب، ورفعُها على شبكةِ جوّالٍ ضعيفة يفشل بمهلةٍ لا يفهمها
      // العميل. و١٦٠٠ بكسل تكفي لقراءة آيبانٍ بالعين.
      picked = await _picker.pickImage(
        source: ImageSource.gallery,
        maxWidth: 1600,
        maxHeight: 1600,
        imageQuality: 85,
      );
    } on Object {
      // تعذّر فتحُ المعرض — إذنٌ مرفوض أو جهازٌ بلا معرض. الشاشةُ تعرض «لم
      // يُختَر ملف»، ولا يسقط التطبيق على فعلٍ اختياريّ.
      return null;
    }
    if (picked == null) return null;
    return PickedImage(name: picked.name, bytes: await picked.readAsBytes());
  }
}
