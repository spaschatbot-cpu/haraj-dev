import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../domain/common/failure.dart';
import '../../../domain/common/snapshot.dart';
import '../../common/failure_view.dart';
import '../../common/stale_data_banner.dart';

/// قائمة تعرض حالاتها الأربع: تحميل، فشل، فراغ، وبيانات.
///
/// **لماذا widget واحدة للقوائم الثلاث:** قاعدة «لا حالة تحميل بلا حالة فشل
/// وحالة فارغة» تُنسى عند كتابتها ثلاث مرات، وأول قائمة تُكتب على عجل هي التي
/// تعرض دوّامة إلى الأبد عند سقوط الشبكة. هنا الحالات الأربع شرط في التركيب:
/// من يبني القائمة يمرّر نصّ الفراغ أو لا تُصرَّف شيفرته.
///
/// وهنا أيضاً تُعلَّق علامة «آخر تحديث» فوق البيانات المحفوظة (H5)، فلا تسقط
/// من قائمة نسيها كاتبها.
class ActivityListView<T> extends StatelessWidget {
  const ActivityListView({
    required this.state,
    required this.emptyMessage,
    required this.itemBuilder,
    this.onRetry,
    super.key,
  });

  final AsyncValue<Snapshot<List<T>>> state;

  /// نصّ الحالة الفارغة — محلي بحق: قائمة بلا صفوف ليست حالة يعرفها الخادم.
  final String emptyMessage;

  final Widget Function(BuildContext context, T item) itemBuilder;
  final VoidCallback? onRetry;

  @override
  Widget build(BuildContext context) => state.when(
    loading: () => const Center(child: CircularProgressIndicator()),
    error: (error, stackTrace) => Center(
      child: FailureView(
        // الخطأ يصل مصنَّفاً من طبقة البيانات؛ وما لم يصل مصنَّفاً يُصنَّف هنا
        // ولا يُبتلع (المادة ٢-٢ بروحها).
        failure: error is Failure
            ? error
            : UnexpectedFailure(error, stackTrace: stackTrace),
        onRetry: onRetry,
      ),
    ),
    data: (snapshot) => Column(
      children: <Widget>[
        StaleDataBanner(snapshot: snapshot),
        Expanded(
          child: snapshot.value.isEmpty
              ? _EmptyState(message: emptyMessage)
              : ListView.builder(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 12,
                    vertical: 8,
                  ),
                  itemCount: snapshot.value.length,
                  itemBuilder: (context, index) =>
                      itemBuilder(context, snapshot.value[index]),
                ),
        ),
      ],
    ),
  );
}

class _EmptyState extends StatelessWidget {
  const _EmptyState({required this.message});

  final String message;

  @override
  Widget build(BuildContext context) => Center(
    child: Padding(
      padding: const EdgeInsets.all(24),
      child: Text(
        message,
        textAlign: TextAlign.center,
        style: Theme.of(context).textTheme.bodyLarge,
      ),
    ),
  );
}
