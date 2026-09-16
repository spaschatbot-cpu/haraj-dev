import '../gateways/image_source_picker.dart';
import '../repositories/profile_repository.dart';

/// «اختر صورةً وارفعها كوثيقة».
///
/// الخطوتان في فعلٍ واحدٍ لأنهما سؤالٌ واحدٌ عند العميل، **ويُرجع `false` حين
/// يعدل** — لا استثناءَ لفعلٍ لم يقع.
final class UploadDocument {
  const UploadDocument(this._repository, this._picker);

  final ProfileRepository _repository;
  final ImageSourcePicker _picker;

  Future<bool> call({required String kind}) async {
    final picked = await _picker.pickImage();
    if (picked == null) return false;
    await _repository.uploadDocument(
      kind: kind,
      fileName: picked.name,
      bytes: picked.bytes,
    );
    return true;
  }
}
