import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app/providers.dart';
import '../../domain/catalog/entities/vehicle_query.dart';
import '../../domain/common/snapshot.dart';

/// مفضلة العميل كما جاءت من الخادم، بمصدرها ولحظتها.
///
/// `Snapshot` لا `VehiclePage` مجرَّدة: بلا المصدر واللحظة تُعرض قائمةٌ محفوظة
/// على أنها الحالية، فيظنّ العميل أنه أزال مركبةً وهي باقية.
final favouritesProvider = FutureProvider.autoDispose<Snapshot<VehiclePage>>(
  (ref) => ref.watch(favouritesRepositoryProvider).loadFavourites(),
);

/// قلبُ حال المركبة في المفضلة: تُضاف إن لم تكن، وتُزال إن كانت.
///
/// **يُعاد السؤال ولا تُعدَّل القائمة محلياً:** التعديل المحليّ يجعل الشاشة
/// تقول «أُزيلت» قبل أن يقولها الخادم، فإن فشل الطلب بقيت مخفيّةً وهي موجودة.
/// والقائمة قصيرة، فإعادة قراءتها أرخص من كذبةٍ تُصحَّح لاحقاً.
///
/// ويُبطَل معها كاش المركبة نفسها: القلب على صفحتها يقرأ `isFavourite` من
/// الكرت، وتركُه بلا إبطال يُبقيه على حاله بعد الضغط.
final toggleFavouriteProvider =
    Provider<
      Future<void> Function({
        required String vehicleId,
        required bool isFavourite,
      })
    >((ref) {
      return ({required String vehicleId, required bool isFavourite}) async {
        final repository = ref.read(favouritesRepositoryProvider);
        if (isFavourite) {
          await repository.unmark(vehicleId);
        } else {
          await repository.mark(vehicleId);
        }
        ref
          ..invalidate(favouritesProvider)
          ..invalidate(vehicleProvider(vehicleId));
      };
    });
