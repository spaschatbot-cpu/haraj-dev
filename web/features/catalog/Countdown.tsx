"use client";

/**
 * العدّاد التنازلي على الكرت — يبدأ من قيمة الخادم، ولا يحكم على المزاد. T1030.
 *
 * يبدأ مرندَراً، ولا فراغ قبل أن يعمل
 * ====================================
 * `initial` هي المدّة كما حسبها **الخادم** وهي في الـHTML قبل أن يُحمَّل أي
 * سكربت: زائرٌ بلا جافاسكربت يقرأ «يومان و٣ ساعات» ويبقى يقرؤها، وزائرٌ معه
 * جافاسكربت يراها هي نفسها ثم تبدأ بالنزول. لا وميضَ ولا شرطةٌ مكانها ولا
 * هيكلٌ رماديّ ينتظر — وهو معيار J5 مطبَّقاً على الجزء الوحيد في هذه الشاشة
 * الذي يحتاج المتصفح فعلاً.
 *
 * ولذلك أيضاً `useState(initial)` ثم التحديث في `useEffect` وحده: أول رندرة في
 * المتصفح يجب أن تُنتج نفس النصّ الذي أنتجه الخادم، وإلا كان اختلافاً في
 * الترطيب سببه ساعتان مختلفتان — أي وميضٌ في كل كرت عند كل تحميل.
 *
 * واللون يقول قُرب الموعد
 * ========================
 * طلب المالك (2026-09-07): «عدّاد كبير وواضح ولونه يتغيّر حسب اقتراب موعد
 * النهاية». فالنبرة تُشتقّ من المدّة الباقية بثلاث عتبات، ومن **المصدر نفسه**
 * الذي يُشتقّ منه النصّ — فلا يقع أن يُكتب رقمٌ بلون درجةٍ أخرى.
 *
 * والعتبة الأولى (`initial`) تُحسب على الخادم أيضاً، وإلا اختلف اللون بين
 * رندرة الخادم وأول رندرة في المتصفح — وهو اختلاف ترطيبٍ حقيقيّ، لا الذي
 * تُحدثه إضافةُ متصفّح.
 *
 * **واللون وحده لا يكفي** (المادة: ما يُميَّز بلونٍ يُميَّز بغيره أيضاً):
 * الدقائق الأخيرة تُكتب أثخنَ وأكبر، ويحمل العنصر `aria-live` فيُسمَع تغيّرها
 * على قارئ الشاشة. ولا يعتمد المعنى على تمييز أحمرَ من كهرمانيّ.
 *
 * وما لا يقوله هذا المكوّن أبداً: «انتهى المزاد»
 * ==============================================
 * حين تمضي اللحظة المعلَنة بحسب **ساعة هذا الجهاز**، تُعرض جملةٌ عن الوقت
 * المعلَن لا عن المزاد. الفرق ليس لفظياً: في v1 كان العدّاد يقارن الوقت في
 * المتصفح ثم يكتب «انتهى»، فرأى العملاءُ الذين ساعاتهم متقدّمة مزاداً مغلقاً
 * وهو مفتوح — ولم يزايدوا. حالة المزاد يقولها الخادم، وهذه هي الحقيقة الوحيدة
 * هنا.
 */

import { useEffect, useState } from "react";

import { remaining } from "@/lib/format";

//: تُقرأ مرة في الثانية لأن آخر دقيقة هي التي تُتابَع؛ وما فوق اليوم يتغيّر
//: نصّه مرة كل ساعة على أي حال، فالتكلفة رخيصة والفرع الإضافي ليس كذلك.
const TICK = 1000;

const MINUTE = 60 * 1000;
const HOUR = 60 * MINUTE;

/**
 * العتبات، وسببُ كلٍّ منها.
 *
 * **ساعة** لأنها آخرُ فرصةٍ لشحن المحفظة ووضع مزايدة بلا عجلة؛ و**عشر دقائق**
 * لأنها المدّة التي لا يكفي فيها شيءٌ إلا المزايدة الآن. وما فوق الساعة لا
 * لون له: تلوينُ كل عدّاد على الشاشة يجعل اللون بلا معنى حين يلزم.
 */
const URGENT = 10 * MINUTE;
const SOON = HOUR;

type Tone = "calm" | "soon" | "urgent" | "past";

function toneFor(endsAt: string, now: number): Tone {
  const end = Date.parse(endsAt);
  if (Number.isNaN(end)) return "past";
  const left = end - now;
  if (left <= 0) return "past";
  if (left <= URGENT) return "urgent";
  if (left <= SOON) return "soon";
  return "calm";
}

/**
 * لكل درجةٍ **شريطها**: خلفيةٌ ونصٌّ وكلمةٌ تقول ما هذا الوقت.

 * الشريط لا اللون على الرقم وحده (T1032): العدّاد آخر ما تقرؤه العين في
 * البطاقة، ولوحٌ ملوَّن يُرى في مسحٍ سريع لشبكةٍ من عشرين — أما رقمٌ أحمر بين
 * نصٍّ أسود فيحتاج قراءة.
 *
 * والصفوف مكتوبةٌ كاملةً لا مركَّبةً بقصّ نصّ — Tailwind يقرأ الملفّ نصّاً،
 * وصفٌّ يُبنى في زمن التشغيل لا يصل ملفّ الأنماط أصلاً.
 */
const TONES: Record<Tone, { band: string; digits: string }> = {
  calm: {
    band: "bg-surface-container text-on-surface",
    digits: "text-headline-sm font-bold",
  },
  soon: {
    band: "bg-warn-surface text-warn",
    digits: "text-headline-sm font-bold",
  },
  urgent: {
    band: "bg-critical-surface text-critical",
    digits: "text-headline-sm font-extrabold",
  },
  past: {
    band: "bg-surface-container text-on-surface-variant",
    digits: "text-label-md font-semibold",
  },
};

export function Countdown({
  /** لحظة انتهاء المزاد بتوقيت UTC، كما أرسلها الخادم. */
  endsAt,
  /** المدّة كما حسبها الخادم — نقطة البداية، فلا فراغ قبل أول نبضة. */
  initial,
  /** لحظةُ ردّ الخادم — منها تُحسب النبرة الأولى، فتتطابق الرندرتان. */
  now,
  /**
   * ماذا يُعدّ إليه: «يغلق بعد» أو «يبدأ خلال».
   *
   * الكلمة من المنادي لا من هنا، لأن الطور هو ما يقرّرها والطورُ يعرفه الكرت.
   * وقبلها كان المكوّن يكتب «يغلق بعد» دائماً — على مزادٍ لم يفتح بعد أيضاً.
   */
  label = "يغلق بعد",
}: {
  endsAt: string;
  initial: string | null;
  now: number;
  label?: string;
}) {
  const [left, setLeft] = useState<string | null>(initial);
  const [tone, setTone] = useState<Tone>(() => toneFor(endsAt, now));

  useEffect(() => {
    const tick = () => {
      const at = Date.now();
      setLeft(remaining(endsAt, at));
      setTone(toneFor(endsAt, at));
    };
    tick();
    const timer = setInterval(tick, TICK);
    return () => clearInterval(timer);
  }, [endsAt]);

  const past = left === null;
  const shown = TONES[past ? "past" : tone];

  return (
    <p
      className={`flex items-center justify-between gap-2 rounded-lg px-3 py-2 ${shown.band}`}
    >
      <span className="text-label-sm opacity-80">
        {past ? "الوقت المعلَن" : label}
      </span>
      <time
        dateTime={endsAt}
        //: يُنطق تغيّرُه على قارئ الشاشة عند الدقائق الأخيرة وحدها — إعلانٌ كل
        //: ثانية طوال اليوم ضجيجٌ يُطفئ القارئ.
        aria-live={tone === "urgent" ? "polite" : "off"}
        className={`money tabular-nums tracking-wider ${shown.digits}`}
      >
        {left ?? "مضى — الحالة من الخادم"}
      </time>
    </p>
  );
}
