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
    <nav aria-label="حالة المزاد" className="mb-6 border-b border-neutral-200">
      <ul className="flex gap-1">
        {TABS.map((tab) => {
          const selected = tab.id === current;
          return (
            <li key={tab.id}>
              <Link
                href={href(tab.id)}
                aria-current={selected ? "page" : undefined}
                className={
                  selected
                    ? "flex items-baseline gap-2 border-b-2 border-neutral-900 px-4 py-3 text-sm font-semibold text-neutral-900"
                    : "flex items-baseline gap-2 border-b-2 border-transparent px-4 py-3 text-sm text-neutral-600 hover:text-neutral-900"
                }
              >
                <span>{tab.label}</span>
                {counts === null ? null : (
                  <span className="money rounded-full bg-neutral-100 px-2 py-0.5 text-xs text-neutral-700">
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
