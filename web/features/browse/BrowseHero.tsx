/**
 * لافتة صدر شاشة التصفّح — تقول ما هذا المكان، وكم فيه الآن. T1032.
 *
 * وفيها **حقيقتان اثنتان لا غير**، وكلتاهما من الخادم:
 *
 * ١. **أن المزاد مغلق.** ليست زينة: عميلٌ يظنّ المزاد علنياً ينتظر أن يرى
 *    مزايدات غيره، فلا يراها، فيقرأ الغياب عطلاً في الموقع ويتصل بالدعم. وهي
 *    وصفٌ صادق للنظام: لا نقطة في العقد تُعيد مزايدات سيارةٍ لأحد، والسرّية
 *    بنيةٌ لا إعداد.
 * ٢. **عدد المركبات في هذا التبويب** — `total` من الرد نفسه الذي رسم الشبكة.
 *    لا طلبَ ثانياً، ولا رقمٌ يُشتقّ من طول القائمة: صفحةٌ من عشرين لا تعرف
 *    أن خلفها أربعمئة.
 *
 * وما حُذف من التصميم المرجعيّ: شارة «فحص معتمد موجز». لا فحصَ في هذا المنتج،
 * ولا حقلَ له في العقد — وشارةُ ثقةٍ عن شيءٍ غير موجود ادّعاءٌ على العميل، لا
 * عنصرُ تصميم.
 */

import { count } from "@/lib/format";

export function BrowseHero({
  /** كم مركبة في التبويب المعروض — `total` كما قاله الخادم، أو `null` إن لم يردّ. */
  total,
}: {
  total: number | null;
}) {
  return (
    <section className="mb-6 flex flex-col gap-4 rounded-xl bg-surface-lowest p-6 shadow-sm md:flex-row md:items-center md:justify-between">
      <div className="flex items-start gap-4">
        <span
          aria-hidden="true"
          className="flex h-12 w-12 shrink-0 items-center justify-center rounded-lg bg-surface-highest text-2xl text-secondary"
        >
          🔒
        </span>
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="text-headline-md">ساحة المزادات المغلقة</h1>
            <span className="rounded-sm bg-secondary-fixed px-2 py-0.5 text-caption font-bold text-on-secondary-fixed">
              مزايدة مغلقة
            </span>
          </div>
          <p className="mt-1 max-w-xl text-body-sm text-on-surface-variant">
            كل مزايدة سرّية: لا يرى أحدٌ مبلغك، ولا ترى مبلغ غيرك، ولا عدد
            المزايدين. تُفتح المظاريف عند الإغلاق.
          </p>
        </div>
      </div>

      {total === null ? null : (
        <div className="shrink-0 border-t border-outline-variant/60 pt-3 md:border-t-0 md:border-e md:pe-6 md:pt-0">
          <p className="text-caption text-on-surface-variant">مركبات هذا التبويب</p>
          <p className="text-headline-md">
            <span className="tnum">{count(total)}</span>{" "}
            <span className="text-label-sm font-normal text-on-surface-variant">
              مركبة
            </span>
          </p>
        </div>
      )}
    </section>
  );
}
