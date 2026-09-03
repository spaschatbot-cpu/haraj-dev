import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app/providers.dart';
import '../../domain/activity/entities/invoice.dart';
import '../../domain/activity/entities/participation.dart';
import '../../domain/activity/entities/purchase.dart';
import '../../domain/common/snapshot.dart';

/// حالة القوائم الثلاث لطبقة العرض.
///
/// ثلاثة مزوّدات لا واحد: التبويب الذي يفشل يعيد المحاولة وحده، ولا يسحب معه
/// تبويبين نجحا. ولو كانت الثلاث في مزوّد واحد لصار سقوط نقطة واحدة سقوطاً
/// للشاشة كلها.
///
/// كل مزوّد يرجع `Snapshot` لا قائمة: بلا مصدر البيانات وطابعها تعذّر عرض
/// علامة «آخر تحديث» بصدق (H5).
final myParticipationsProvider = FutureProvider<Snapshot<List<Participation>>>(
  (ref) => ref.watch(loadMyParticipationsProvider)(),
);

final myPurchasesProvider = FutureProvider<Snapshot<List<Purchase>>>(
  (ref) => ref.watch(loadMyPurchasesProvider)(),
);

final myInvoicesProvider = FutureProvider<Snapshot<List<Invoice>>>(
  (ref) => ref.watch(loadMyInvoicesProvider)(),
);
