/// نقطة التحويل **الوحيدة** من UTC إلى التوقيت السعودي للعرض.
///
/// المادة ٣-١: الوقت UTC في التخزين والنقل، سعودي في العرض، والتحويل يحدث مرة
/// واحدة عند حافة العرض. أي `add(Duration(hours: 3))` في مكان آخر يُرفض في
/// المراجعة — سطران بالحساب نفسه هما بالضبط كيف يظهر توقيتان مختلفان لنفس
/// المزاد في شاشتين.
///
/// نظير هذا الملف في الخلفية: `backend/apps/core/time.py`.
abstract final class SaudiTime {
  /// السعودية على UTC+3 ثابتاً — لا توقيت صيفي، فلا حاجة لقاعدة مناطق زمنية.
  static const Duration _offsetFromUtc = Duration(hours: 3);

  /// يرجع لحظة تُقرأ حقولها (`hour`، `day`) كساعة الحائط في السعودية.
  static DateTime forDisplay(DateTime instant) =>
      instant.toUtc().add(_offsetFromUtc);
}
