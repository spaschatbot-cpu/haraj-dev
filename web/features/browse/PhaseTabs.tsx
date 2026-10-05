/**
 * حالة المزاد — ثلاثُ بطاقاتٍ تُفتح، لا شرائحُ في وعاء. T1030 / T1035.
 *
 * **ولماذا بطاقات.** المزادُ أسبوعيٌّ واحد، فالسؤالُ الذي يأتي به الزائر ليس
 * «أيُّ مزادٍ أختار» بل **«أين وصل المزاد الآن»** — والحالاتُ الثلاث هي
 * المدخل. وكانت شرائحَ صغيرةً في وعاءٍ غائر: العددُ فيها حبّةٌ بحجم الحرف،
 * يُقرأ بالتدقيق لا بالنظر. وقرارُ المالكة في ٥ أكتوبر ٢٠٢٦ (دمجُ المقترحين
 * ٣ و٤).
 *
 * **وروابطُ لا أزرار.** كل بطاقة `<a>` إلى عنوانٍ كامل، فتعمل بلا جافاسكربت،
 * وتُفتح في تبويب جديد، وتُنسخ وتُرسَل، ويرجع إليها زرّ الرجوع. بطاقةٌ بمعالج
 * نقر هي ثلاثةٌ من هذه الأربعة مفقودة، ولا تكسب شيئاً في شاشةٍ تُرندَر في
 * الخادم أصلاً.
 *
 * والانتقال يحتفظ بالبحث ويصفّر الترقيم: من كان في الصفحة الرابعة من «نشط»
 * وضغط «منتهي» لا يريد الصفحة الرابعة من «منتهي» — وغالباً لا توجد، فيرى
 * شبكةً فارغة يظنّها التبويب كلّه.
 *
 * والعدّاد يُعرض إن قاله الخادم، ويُترك إن لم يقله. لا صفر يُكتب هنا: البطاقةُ
 * التي تقول «٠» تقول «لا مزاد قادم»، وذلك ادّعاءٌ عن العالم لا عن الرد.
 *
 * **والمختارةُ تُميَّز بأكثر من اللون**: تمتلئ كبسولتُها بالكحليّ وتُطوَّق
 * دائرتُها بالأبيض، ولها `aria-current` — فمن لا يميّز الألوان يراها، ومن
 * يقرأ بالصوت يسمعها.
 *
 * **وكبسولاتٌ لا مستطيلات** (الاقتراح «ج»، ٥ أكتوبر ٢٠٢٦): ثلاثُ بطاقاتٍ
 * مملوءةٍ بألوانٍ مشبعةٍ متجاورة كانت تتنافس على العين، فصار اللونُ في دائرة
 * الأيقونة وحدَها والكبسولةُ بيضاء. والشكلُ في `globals.css` (`.phase-pill`).
 */

import Link from "next/link";

import { count } from "@/lib/format";

import { TABS, type Phase } from "./phase";
import type { PhaseCounts } from "@/lib/api";

//: **ولكلّ حالةٍ لونُها** — كما في v1: «قريباً» برتقاليّ (`#d97706`)
//: و«نشط» ذهبيّ (`#a88118`) و«منتهي» محايد (`index.php:1612`). وعندنا
//: تُقرأ من رموز المشروع لا بهيئةٍ مكتوبة: `warn` للقادم (انتظار)،
//: و`ok` للجاري (مفتوحٌ الآن)، و`secondary` للمنتهي (أرشيف).
//:
//: واللونُ **لا يحمل المعنى وحده**: الرقمُ والاسمُ والرسمُ كلُّها مكتوبة،
//: والمختارةُ لها إطارٌ أثخن و`aria-current` — فمن لا يميّز الألوان يقرأ.
const TONE: Record<Phase, string> = {
  soon: "tone-soon",
  active: "tone-active",
  ended: "tone-ended",
};

//: رسمٌ لكل حالة — مضمَّنٌ لا محرف: المحرفَ يرسمه نظامُ التشغيل بأسلوبه،
//: ملوّناً ومختلفاً بين ويندوز وأندرويد (قاعدةُ T837 في اللوحة).
const ART: Record<Phase, React.ReactNode> = {
  soon: (
    <>
      <circle cx="12" cy="12" r="8.5" />
      <path d="M12 7.5V12l3 2" />
    </>
  ),
  active: (
    <>
      <path d="M4.5 19.5h9" />
      <path d="m7 15 7-7" />
      <path d="m11.5 4.5 5 5-2.5 2.5-5-5z" />
      <path d="m15 11 4.5 4.5" />
    </>
  ),
  ended: (
    <>
      <path d="M4 7.5h16v12H4z" />
      <path d="M3 4.5h18v3H3z" />
      <path d="M10 12h4" />
    </>
  ),
};

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
    <nav aria-label="حالة المزاد" className="mb-6">
      <ul className="grid grid-cols-3 gap-3">
        {TABS.map((tab, index) => {
          const selected = tab.id === current;
          const tone = TONE[tab.id];
          const live = tab.id === "active" && (counts?.active ?? 0) > 0;
          return (
            <li key={tab.id}>
              <Link
                href={href(tab.id)}
                aria-current={selected ? "page" : undefined}
                /* التأخيرُ المتدرّج يجعل العينَ تقرأ الثلاثَ واحدةً بعد
                   واحدة، لا هبوطاً واحداً لا يُقرأ منه شيء. */
                style={{ animationDelay: `${index * 70}ms` }}
                className={`phase-card phase-pill ${tone} flex h-full flex-col items-center justify-center gap-2 px-2 py-3 text-center md:flex-row md:justify-start md:gap-4 md:p-2.5 md:pe-6 md:text-start`}
              >
                {/* الأيقونةُ في دائرةٍ من سطح نغمتها — اللونُ فيها وحدَها.
                    وعلى الجوّال تقف الكبسولةُ قائمةً، الدائرةُ فوق النصّ: ثلثُ
                    شاشةٍ عرضُها ٣٧٥ لا يسع الدائرةَ والاسمَ متجاورين، فقُصّ
                    «منتهي» إلى «منت…» (قِيس على الإنتاج). */}
                <span
                  aria-hidden="true"
                  className="phase-icon relative flex h-10 w-10 shrink-0 items-center justify-center rounded-full md:h-14 md:w-14"
                >
                  <svg
                    viewBox="0 0 24 24"
                    className="h-5 w-5 md:h-7 md:w-7"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="1.8"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  >
                    {ART[tab.id]}
                  </svg>
                  {live ? (
                    <span className="phase-live-dot absolute -top-0.5 -end-0.5 h-3 w-3 rounded-full border-2 border-white bg-current" />
                  ) : null}
                </span>

                <span className="flex min-w-0 flex-col items-center md:items-start">
                  {counts === null ? null : (
                    <span className="tnum text-headline-sm leading-none md:text-headline-md">
                      {count(counts[tab.id])}
                    </span>
                  )}
                  <span className="tone-ink text-label-md">{tab.label}</span>
                </span>
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
