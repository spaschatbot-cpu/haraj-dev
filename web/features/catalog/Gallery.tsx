"use client";

/**
 * معرض صور المركبة بعدّاد `1 / 9` — HR-12ب، ونظير معرض v1 في نافذة التفاصيل.
 *
 * الطبقة التي كانت بلا قناة
 * ==========================
 * HR-12 يولّد لكل صورة طبقتين ويخزّنهما: بطاقة (400×300) ومعاينة (1280×960).
 * ولم يكن **أي** عميل يستطيع طلب الثانية: الكرت يحمل `thumbnail_url` وحده،
 * وشاشة التفاصيل كانت تُكبّر صورة البطاقة إلى عرض الشاشة — أي 400 بكسل
 * ممدودةً على 1280. هذا المكوّن هو القناة، ومصدره
 * `GET /api/v1/vehicles/{id}/images/`.
 *
 * والصورة الكبيرة `preview_url` لا `thumbnail_url`، والشريط تحتها
 * `thumbnail_url` لا `preview_url` — وهذا كل ما تعنيه طبقتان: أن يُطلَب من
 * كل مقاسٍ ما بُني له. شريطٌ من صور المعاينة هو الحادثة نفسها التي وُلد
 * HR-12 لأجلها (١٣ جيجابايت جمّدت الصفحة) مصغَّرةً بالـCSS.
 *
 * ولا يقرّر شيئاً
 * ================
 * لا ترتيب ولا اختيار غلاف: الخادم يرتّب (`-is_cover, position, id`) وهذا
 * يعرض بالترتيب الذي وصل. أول صورةٍ في المصفوفة هي التي رآها العميل على
 * الكرت، فالضغط على كرتٍ يفتح الصورة نفسها لا غيرها.
 *
 * ويرندَر في الخادم كاملاً
 * =========================
 * `"use client"` لأن التنقّل بين الصور حدثٌ في المتصفّح — لا لأن المحتوى
 * ينتظره. أول صورةٍ وعدّادُها في الـHTML قبل أن يُحمَّل أي سكربت (معيار J5)،
 * وزائرٌ بلا جافاسكربت يرى الصورة الأولى وعددَ ما بعدها؛ لا يتنقّل، ولا يرى
 * هيكلاً رمادياً ينتظر.
  *
 * لماذا كان التنقّل بطيئاً (٢٤ نوفمبر ٢٠٢٦)
 * ==========================================
 * المالك: «الحركة بين الصور بطيئة جداً وبايظة». وسببان:
 *
 * ١. **كلُّ نقرةٍ طلبٌ جديد يمرّ بمُحسِّن Next** (`/_next/image`) فيعيد ترميزَ
 *    معاينةٍ بعرض 1280 على خادم الويب — وهي مولَّدةٌ بمقاسها في الخلفيّة
 *    أصلاً. فالصورُ هنا `unoptimized`: تُطلب كما هي من الوسائط.
 * ٢. **لا صورةَ تُجهَّز قبل أن تُطلب**: كانت الصورةُ الكبيرة تُستبدل، فيبقى
 *    الإطارُ فارغاً حتى تصل التالية. فالصورُ الآن مكدّسةٌ والظاهرةُ وحدها
 *    مرئيّة، والتي قبلها وبعدها محمَّلةٌ مسبقاً — فالانتقالُ تلاشٍ فوريّ.
 *
 * ومعها: الأسهمُ في لوحة المفاتيح، والسحبُ باللمس، والشريطُ يلحق الصورةَ
 * الظاهرة فلا تختفي مصغّرتُها خارج الإطار، والعدّادُ في المنتصف فعلاً (كان
 * `start-1/2` مع إزاحةٍ فيزيائيّة، فمال في RTL).
 */

import Image from "next/image";
import { useEffect, useRef, useState } from "react";

export interface Shot {
  id: number;
  thumbnail_url: string | null;
  preview_url: string | null;
  is_cover: boolean;
}

function large(shot: Shot): string | null {
  return shot.preview_url ?? shot.thumbnail_url;
}

function Chevron({ flip }: { flip?: boolean }) {
  return (
    <svg
      viewBox="0 0 24 24"
      aria-hidden="true"
      className={`h-5 w-5 ${flip ? "rotate-180" : ""}`}
      fill="none"
      stroke="currentColor"
      strokeWidth="2.2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="m9 6 6 6-6 6" />
    </svg>
  );
}

export function Gallery({ shots, alt }: { shots: Shot[]; alt: string }) {
  const [at, setAt] = useState(0);
  //: ما رُئي يبقى محمَّلاً — الرجوعُ إليه لا يُعيد طلبه.
  const [seen, setSeen] = useState<Set<number>>(() => new Set([0, 1, shots.length - 1]));
  const strip = useRef<HTMLUListElement>(null);
  const touch = useRef<number | null>(null);
  const total = shots.length;

  useEffect(() => {
    const thumb = strip.current?.children[at] as HTMLElement | undefined;
    thumb?.scrollIntoView({ block: "nearest", inline: "nearest", behavior: "smooth" });
  }, [at, total]);

  if (total === 0) {
    return (
      <div className="vd-frame vd-muted flex aspect-[4/3] items-center justify-center rounded-2xl">
        لا توجد صورة
      </div>
    );
  }

  //: الانتقالُ يضمّ الصورةَ وجارتيها إلى ما يُحمَّل في الحدث نفسه — لا في
  //: أثرٍ بعده يعيد الرسم مرّةً ثانية.
  const show = (index: number) => {
    const target = (index + total) % total;
    setAt(target);
    setSeen((old) => {
      const next = new Set(old);
      [target - 1, target, target + 1].forEach((i) => next.add((i + total) % total));
      return next.size === old.size ? old : next;
    });
  };
  const go = (step: number) => show(at + step);

  return (
    <div>
      <div
        className="vd-frame group relative aspect-[4/3] overflow-hidden rounded-2xl outline-none focus-visible:ring-2 focus-visible:ring-secondary"
        tabIndex={total > 1 ? 0 : -1}
        aria-roledescription="معرض صور"
        onKeyDown={(event) => {
          // الصفحةُ RTL: السهمُ الأيسرُ «إلى الأمام» كما يُقرأ الكلام.
          if (event.key === "ArrowLeft") go(1);
          if (event.key === "ArrowRight") go(-1);
        }}
        onTouchStart={(event) => {
          touch.current = event.touches[0]?.clientX ?? null;
        }}
        onTouchEnd={(event) => {
          const start = touch.current;
          const end = event.changedTouches[0]?.clientX;
          touch.current = null;
          if (start === null || end === undefined || Math.abs(end - start) < 40) return;
          go(end < start ? 1 : -1);
        }}
      >
        {shots.map((shot, index) => {
          const src = large(shot);
          if (!src || !seen.has(index)) return null;
          return (
            <Image
              key={shot.id}
              src={src}
              alt={index === at ? alt : ""}
              fill
              unoptimized
              priority={index === 0}
              sizes="(max-width: 1024px) 100vw, 60vw"
              className={`object-contain transition-opacity duration-200 ${
                index === at ? "opacity-100" : "opacity-0"
              }`}
            />
          );
        })}

        <span className="tnum absolute bottom-3 left-1/2 -translate-x-1/2 rounded-full bg-black/55 px-3 py-1 text-caption font-semibold text-white backdrop-blur-sm">
          {at + 1} / {total}
        </span>

        {total > 1 ? (
          <>
            <button
              type="button"
              onClick={() => go(-1)}
              aria-label="الصورة السابقة"
              className="gallery-nav absolute right-3 top-1/2 -translate-y-1/2"
            >
              <Chevron />
            </button>
            <button
              type="button"
              onClick={() => go(1)}
              aria-label="الصورة التالية"
              className="gallery-nav absolute left-3 top-1/2 -translate-y-1/2"
            >
              <Chevron flip />
            </button>
          </>
        ) : null}
      </div>

      {total > 1 ? (
        <ul ref={strip} className="gallery-strip mt-3 flex gap-2 overflow-x-auto pb-1">
          {shots.map((shot, index) => (
            <li key={shot.id} className="shrink-0">
              <button
                type="button"
                onClick={() => show(index)}
                aria-label={`صورة ${index + 1}`}
                aria-current={index === at}
                className={`relative block h-16 w-24 overflow-hidden rounded-xl border-2 transition ${
                  index === at ? "vd-thumb-on" : "vd-thumb opacity-60 hover:opacity-100"
                }`}
              >
                {shot.thumbnail_url ? (
                  <Image
                    src={shot.thumbnail_url}
                    alt=""
                    fill
                    unoptimized
                    sizes="96px"
                    className="object-cover"
                  />
                ) : null}
              </button>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
