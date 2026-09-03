import '../../common/snapshot.dart';
import '../entities/participation.dart';
import '../repositories/activity_repository.dart';

/// «في أي مزادات أنا داخل، وإيش وضع تأميني فيها؟»
///
/// رقيقة عمداً: القواعد كلها في الخادم (المبدأ الحاكم للفيز 008). قيمتها أنها
/// الاسم الذي تناديه طبقة العرض، فتبقى العرض جاهلة بمصدر البيانات.
final class LoadMyParticipations {
  const LoadMyParticipations(this._repository);

  final ActivityRepository _repository;

  Future<Snapshot<List<Participation>>> call() =>
      _repository.loadParticipations();
}
