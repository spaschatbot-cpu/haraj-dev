import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../domain/common/failure.dart';
import '../../domain/common/snapshot.dart';
import 'failure_view.dart';
import 'stale_data_banner.dart';

/// الأحوال الثلاثة لأي شاشة تقرأ من الخادم: تحميل، فشل، بيانات.
///
/// قاعدة التصميم 6 في الفيز 008: **لا حالة تحميل بلا حالة فشل وحالة فارغة.**
/// الشاشة التي تعرض دوّامة إلى الأبد عند سقوط الشبكة عطلٌ لا تصميم. جمعُ
/// الحالتين الأوليين هنا يجعل نسيان إحداهما مستحيلاً بالبناء، لا مرهوناً
/// بانتباه المراجع؛ والحالة الفارغة تبقى للشاشة لأن «فارغ» يختلف معناه بين
/// «لا مزادات» و«لا مركبات مطابقة».
///
/// وحين تصل البيانات من الكاش تُسبَق بعلامة «آخر تحديث» (H5) — هنا أيضاً، لا
/// في كل شاشة على حدة.
class SnapshotView<T> extends StatelessWidget {
  const SnapshotView({
    required this.state,
    required this.builder,
    this.onRetry,
    super.key,
  });

  /// حالة الجلب كما تصل من Riverpod.
  final AsyncValue<Snapshot<T>> state;

  final Widget Function(BuildContext context, Snapshot<T> snapshot) builder;

  final VoidCallback? onRetry;

  @override
  Widget build(BuildContext context) => switch (state) {
    AsyncData<Snapshot<T>>(:final value) => Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: <Widget>[
        StaleDataBanner(snapshot: value),
        Expanded(child: builder(context, value)),
      ],
    ),
    AsyncError<Snapshot<T>>(:final error, :final stackTrace) => Center(
      child: FailureView(
        // خطأٌ ليس `Failure` عطبٌ في التطبيق: يُصنَّف ويظهر، ولا يُبتلع في
        // فرعٍ صامت (المادة ٢-٢ بروحها).
        failure: error is Failure
            ? error
            : UnexpectedFailure(error, stackTrace: stackTrace),
        onRetry: onRetry,
      ),
    ),
    _ => const Center(child: CircularProgressIndicator()),
  };
}
