/// بيانات مع مصدرها ولحظة جلبها (T704 / معيار القبول H5).
///
/// كل شاشة تعمل بلا اتصال بآخر بيانات معروفة، **مع علامة «آخر تحديث»**. لكي
/// تُعرض العلامة بصدق، لا بدّ أن تصل البيانات إلى العرض ومعها من أين جاءت
/// ومتى — لا أن تُخمَّن من وجود شبكة أو غيابها.
library;

/// من أين جاءت هذه النسخة من البيانات.
enum DataOrigin {
  /// من الخادم في هذه اللحظة.
  network,

  /// من الكاش المحلي بعد تعذّر الوصول للخادم.
  cache,
}

/// قيمة مغلَّفة بمصدرها وطابعها الزمني.
final class Snapshot<T> {
  const Snapshot({
    required this.value,
    required this.origin,
    required this.fetchedAt,
  });

  /// نسخة طازجة جاءت من الخادم الآن.
  Snapshot.fresh(this.value, {required DateTime at})
    : origin = DataOrigin.network,
      fetchedAt = at;

  /// نسخة قديمة من الكاش — `fetchedAt` لحظة جلبها من الخادم، لا لحظة قراءتها.
  Snapshot.cached(this.value, {required DateTime storedAt})
    : origin = DataOrigin.cache,
      fetchedAt = storedAt;

  final T value;
  final DataOrigin origin;

  /// بتوقيت UTC دائماً — التحويل للعرض عند حافة العرض وحدها (المادة ٣-١).
  final DateTime fetchedAt;

  bool get isStale => origin == DataOrigin.cache;

  Snapshot<R> map<R>(R Function(T value) transform) => Snapshot<R>(
    value: transform(value),
    origin: origin,
    fetchedAt: fetchedAt,
  );
}
