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
 */

import Image from "next/image";
import { useState } from "react";

export interface Shot {
  id: number;
  thumbnail_url: string | null;
  preview_url: string | null;
  is_cover: boolean;
}

/** الأكبر المتاح لهذه الصورة. طبقةٌ ناقصة على القرص لا تعني إطاراً فارغاً. */
function large(shot: Shot): string | null {
  return shot.preview_url ?? shot.thumbnail_url;
}

export function Gallery({ shots, alt }: { shots: Shot[]; alt: string }) {
  const [at, setAt] = useState(0);

  if (shots.length === 0) {
    return (
      <div className="flex aspect-[4/3] items-center justify-center rounded-lg bg-neutral-100 text-neutral-500">
        لا توجد صورة
      </div>
    );
  }

  //: `?? shots[0]` لأن `noUncheckedIndexedAccess` محقّ: الفهرس مقيَّد بالطول
  //: في السطر نفسه، لكن السلامة تأتي من النوع لا من قراءةِ من يمرّ.
  const shown = shots[Math.min(at, shots.length - 1)] ?? shots[0]!;

  //: بالباقي لا بحدٍّ عند الطرف: الدوران هو ما يتوقّعه من يضغط «التالي» على
  //: آخر صورة، وزرٌّ لا يفعل شيئاً يُقرأ عطلاً.
  const go = (step: number) => setAt((i) => (i + step + shots.length) % shots.length);

  return (
    <div>
      <div className="relative aspect-[4/3] overflow-hidden rounded-lg bg-neutral-100">
        {large(shown) ? (
          <Image
            src={large(shown) as string}
            alt={alt}
            fill
            sizes="(max-width: 1024px) 100vw, 50vw"
            className="object-cover"
            //: الصورة الأولى وحدها: هي أكبر ما يُرسم في هذه الصفحة (LCP).
            priority={at === 0}
          />
        ) : (
          <div className="flex h-full items-center justify-center text-neutral-500">
            لا توجد صورة
          </div>
        )}

        {/*
          العدّاد `1 / 9` كما يعرضه v1، على الصورة أسفلها. ويُعرض حتى مع صورةٍ
          واحدة — «1 / 1» جوابٌ عن سؤال «هل في غيرها؟»، وغيابه ليس جواباً.
        */}
        <span className="money absolute bottom-2 start-1/2 -translate-x-1/2 rounded bg-neutral-900/75 px-2 py-0.5 text-xs tabular-nums text-white">
          {at + 1} / {shots.length}
        </span>

        {shots.length > 1 ? (
          <>
            {/*
              زرّان حقيقيان لا `div` عليه `onClick`: التنقّل بلوحة المفاتيح
              ونطقُ الاسم على قارئ الشاشة يأتيان من الوسم، لا من سمةٍ تُضاف.
            */}
            <button
              type="button"
              onClick={() => go(-1)}
              aria-label="الصورة السابقة"
              className="absolute end-2 top-1/2 -translate-y-1/2 rounded-full bg-white/90 px-3 py-2 text-neutral-900 shadow"
            >
              ›
            </button>
            <button
              type="button"
              onClick={() => go(1)}
              aria-label="الصورة التالية"
              className="absolute start-2 top-1/2 -translate-y-1/2 rounded-full bg-white/90 px-3 py-2 text-neutral-900 shadow"
            >
              ‹
            </button>
          </>
        ) : null}
      </div>

      {shots.length > 1 ? (
        <ul className="mt-3 flex gap-2 overflow-x-auto pb-1">
          {shots.map((shot, index) => (
            <li key={shot.id}>
              <button
                type="button"
                onClick={() => setAt(index)}
                aria-label={`صورة ${index + 1}`}
                aria-current={index === at}
                //: الحدّ لا اللون وحده: المختارة تُميَّز بإطارٍ أثخن، فيُقرأ
                //: التمييز على شاشةٍ رماديةٍ وعلى عينٍ لا تفرّق الألوان.
                className={`relative block h-16 w-24 overflow-hidden rounded border-2 ${
                  index === at ? "border-neutral-900" : "border-transparent opacity-70"
                }`}
              >
                {shot.thumbnail_url ? (
                  <Image
                    src={shot.thumbnail_url}
                    alt=""
                    fill
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
