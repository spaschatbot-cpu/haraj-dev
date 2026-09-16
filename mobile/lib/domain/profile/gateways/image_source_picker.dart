/// صورةٌ اختارها العميل من جهازه — اسمُه وبايتاته، لا مسارُه.
///
/// **لا `File` ولا `XFile` في النطاق.** النطاقُ لا يعرف نظامَ ملفّاتٍ ولا
/// حزمةَ اختيار: نوعٌ من حزمةٍ خارجيّة هنا يجعل استبدالَها تعديلاً في النطاق،
/// ويمنع اختبارَ المستودع بلا جهاز.
final class PickedImage {
  const PickedImage({required this.name, required this.bytes});

  final String name;
  final List<int> bytes;
}

/// يفتح معرضَ الصور ويُرجع ما اختاره العميل، أو `null` إن عدل.
abstract interface class ImageSourcePicker {
  /// **لا يرمي عند الإلغاء**: عدولُ العميل ليس عطلاً، و`null` تقوله بلا
  /// استثناءٍ تُمسك به كلُّ شاشة.
  Future<PickedImage?> pickImage();
}
