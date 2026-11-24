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
import { createPortal } from "react-dom";

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
  const [open, setOpen] = useState(false);
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
        className="vd-frame group relative aspect-[4/3] cursor-zoom-in overflow-hidden rounded-2xl outline-none focus-visible:ring-2 focus-visible:ring-secondary"
        tabIndex={total > 1 ? 0 : -1}
        aria-roledescription="معرض صور"
        onClick={(event) => {
          // الضغطُ على الصورة يكبّرها — لا على أزرارها.
          if (!(event.target as HTMLElement).closest("button")) setOpen(true);
        }}
        onKeyDown={(event) => {
          // الصفحةُ RTL: السهمُ الأيسرُ «إلى الأمام» كما يُقرأ الكلام.
          if (event.key === "ArrowLeft") go(1);
          if (event.key === "ArrowRight") go(-1);
          if (event.key === "Enter") setOpen(true);
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

        <button
          type="button"
          onClick={() => setOpen(true)}
          aria-label="عرض الصور بملء الشاشة"
          className="gallery-nav absolute left-3 top-3"
        >
          <svg
            viewBox="0 0 24 24"
            aria-hidden="true"
            className="h-5 w-5"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M4 9V4h5M20 9V4h-5M4 15v5h5M20 15v5h-5" />
          </svg>
        </button>

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

      {open ? (
        <Lightbox
          shots={shots}
          at={at}
          alt={alt}
          onShow={show}
          onClose={() => setOpen(false)}
        />
      ) : null}
    </div>
  );
}

/**
 * العرضُ بملء الشاشة (المالك، ٢٤ نوفمبر ٢٠٢٦: «الصورة تتوسّع… فول سكرين
 * أتنقّل بينها، أسهم حركة، والشريط تحت يعرض الصور، وإكس فوق تقفل»).
 *
 * **في بوّابةٍ إلى `body`** لا داخل المعرض: لوحُ الصفحة حوله `overflow-hidden`
 * وله حركةُ دخولٍ بـ`transform` — وكلاهما يحبس `position: fixed` داخله فيُقصّ
 * «ملءُ الشاشة» على حدود اللوح.
 *
 * ويُغلق بالإكس، وبـ`Esc`، وبالضغط على الخلفيّة خارج الصورة. والصفحةُ تحته لا
 * تتمرّر ما دام مفتوحاً، والتركيزُ ينتقل إلى زرّ الإغلاق فيُغلق بلوحة المفاتيح.
 */
function Lightbox({
  shots,
  at,
  alt,
  onShow,
  onClose,
}: {
  shots: Shot[];
  at: number;
  alt: string;
  onShow: (index: number) => void;
  onClose: () => void;
}) {
  const close = useRef<HTMLButtonElement>(null);
  const strip = useRef<HTMLUListElement>(null);
  const touch = useRef<number | null>(null);
  const total = shots.length;
  const shot = shots[at] ?? shots[0]!;
  const src = large(shot);

  useEffect(() => {
    const before = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = before;
    };
  }, []);

  useEffect(() => {
    close.current?.focus();
  }, []);

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
      // RTL: السهمُ الأيسرُ «إلى الأمام».
      if (event.key === "ArrowLeft") onShow(at + 1);
      if (event.key === "ArrowRight") onShow(at - 1);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [at, onClose, onShow]);

  useEffect(() => {
    const thumb = strip.current?.children[at] as HTMLElement | undefined;
    thumb?.scrollIntoView({ block: "nearest", inline: "center", behavior: "smooth" });
  }, [at]);

  return createPortal(
    <div
      role="dialog"
      aria-modal="true"
      aria-label={`صور ${alt}`}
      className="lightbox fixed inset-0 z-[100] flex flex-col text-white"
    >
      <div className="flex items-center justify-between gap-4 px-4 py-3 md:px-6">
        <p className="min-w-0 truncate text-label-md font-semibold">{alt}</p>
        <div className="flex items-center gap-3">
          <span className="tnum rounded-full bg-white/10 px-3 py-1 text-caption font-semibold">
            {at + 1} / {total}
          </span>
          <button
            ref={close}
            type="button"
            onClick={onClose}
            aria-label="إغلاق"
            className="lightbox-btn flex h-10 w-10 items-center justify-center rounded-full"
          >
            <svg
              viewBox="0 0 24 24"
              aria-hidden="true"
              className="h-5 w-5"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.2"
              strokeLinecap="round"
            >
              <path d="M6 6l12 12M18 6 6 18" />
            </svg>
          </button>
        </div>
      </div>

      <div
        className="relative min-h-0 flex-1"
        onClick={(event) => {
          // الضغطُ على الفراغ حول الصورة يُغلق — لا على الصورة ولا الأزرار.
          if (event.target === event.currentTarget) onClose();
        }}
        onTouchStart={(event) => {
          touch.current = event.touches[0]?.clientX ?? null;
        }}
        onTouchEnd={(event) => {
          const start = touch.current;
          const end = event.changedTouches[0]?.clientX;
          touch.current = null;
          if (start === null || end === undefined || Math.abs(end - start) < 40) return;
          onShow(end < start ? at + 1 : at - 1);
        }}
      >
        {src ? (
          <div className="pointer-events-none absolute inset-0 px-2 py-2 md:px-20">
            <div className="relative h-full w-full">
              <Image
                key={shot.id}
                src={src}
                alt={alt}
                fill
                unoptimized
                sizes="100vw"
                className="lightbox-img object-contain"
              />
            </div>
          </div>
        ) : null}

        {total > 1 ? (
          <>
            <button
              type="button"
              onClick={() => onShow(at - 1)}
              aria-label="الصورة السابقة"
              className="lightbox-btn absolute right-3 top-1/2 flex h-12 w-12 -translate-y-1/2 items-center justify-center rounded-full md:right-6"
            >
              <Chevron />
            </button>
            <button
              type="button"
              onClick={() => onShow(at + 1)}
              aria-label="الصورة التالية"
              className="lightbox-btn absolute left-3 top-1/2 flex h-12 w-12 -translate-y-1/2 items-center justify-center rounded-full md:left-6"
            >
              <Chevron flip />
            </button>
          </>
        ) : null}
      </div>

      {total > 1 ? (
        <ul
          ref={strip}
          className="gallery-strip flex gap-2 overflow-x-auto px-4 py-3 md:justify-center"
        >
          {shots.map((item, index) => (
            <li key={item.id} className="shrink-0">
              <button
                type="button"
                onClick={() => onShow(index)}
                aria-label={`صورة ${index + 1}`}
                aria-current={index === at}
                className={`relative block h-14 w-20 overflow-hidden rounded-lg border-2 transition md:h-16 md:w-24 ${
                  index === at ? "border-white" : "border-transparent opacity-50 hover:opacity-100"
                }`}
              >
                {item.thumbnail_url ? (
                  <Image
                    src={item.thumbnail_url}
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
    </div>,
    document.body,
  );
}
