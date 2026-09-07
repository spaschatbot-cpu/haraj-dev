/**
 * تبويبات حالة المزاد — روابط، لا أزرار. T1030.
 *
 * كل تبويب `<a>` إلى عنوانٍ كامل، فيعمل بلا جافاسكربت، ويُفتح في تبويب جديد،
 * ويُنسخ ويُرسَل، ويرجع إليه زرّ الرجوع. تبويبٌ بمعالج نقر هو ثلاثة من هذه
 * الأربعة مفقودة، ولا يكسب شيئاً في شاشةٍ تُرندَر في الخادم أصلاً.
 *
 * والانتقال يحتفظ بالبحث ويصفّر الترقيم: من كان في الصفحة الرابعة من «نشط»
 * وضغط «منتهي» لا يريد الصفحة الرابعة من «منتهي» — وغالباً لا توجد، فيرى
 * شبكةً فارغة يظنّها التبويب كلّه.
 *
 * والعدّاد يُعرض إن قاله الخادم، ويُترك إن لم يقله. لا صفر يُكتب هنا: التبويب
 * الذي يقول «٠» يقول «لا مزاد قادم»، وذلك ادّعاءٌ عن العالم لا عن الرد.
 */

import Link from "next/link";

import { count } from "@/lib/format";

import { TABS, type Phase } from "./phase";
import type { PhaseCounts } from "@/lib/api";

export function PhaseTabs({
  current,
  counts,
  /** ما في العنوان الآن، فيبقى البحث قائماً عبر التبويبات. */
  query,
  path,
}: {
  current: Phase;
  counts: PhaseCounts | null;
  query: URLSearchParams;
  path: string;
}) {
  function href(phase: Phase): string {
    const next = new URLSearchParams(query);
    next.set("phase", phase);
    next.delete("offset");
    return `${path}?${next.toString()}`;
  }

  return (
    /*
      مجموعةُ حبّاتٍ في وعاءٍ غائر، لا تبويباتٌ بخطٍّ سفليّ — التصميم المرجعيّ
      (T1032). والوعاء يمرّر أفقياً على الجوال بدل أن يلتفّ سطرين: ثلاثة
      تبويبات في سطرين تُقرأ قائمتين.
    */
    <nav aria-label="حالة المزاد" className="mb-6">
      <ul className="inline-flex gap-1 overflow-x-auto rounded-xl bg-surface-low p-1.5">
        {TABS.map((tab) => {
          const selected = tab.id === current;
          return (
            <li key={tab.id}>
              <Link
                href={href(tab.id)}
                aria-current={selected ? "page" : undefined}
                className={`flex items-baseline gap-2 whitespace-nowrap rounded-lg px-5 py-2 text-label-md transition-colors ${
                  selected
                    ? "bg-surface-lowest text-on-surface shadow-sm"
                    : "text-on-surface-variant hover:text-on-surface"
                }`}
              >
                <span>{tab.label}</span>
                {counts === null ? null : (
                  <span
                    className={`tnum rounded-full px-2 py-0.5 text-label-sm ${
                      selected
                        ? "bg-surface-container text-on-surface"
                        : "bg-surface-container text-on-surface-variant"
                    }`}
                  >
                    {count(counts[tab.id])}
                  </span>
                )}
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
