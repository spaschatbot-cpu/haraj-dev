/**
 * كرت المركبة — مكوَّن واحد، ولا رسم لكرت خارجه. T1010، وتصميمه T1032.
 *
 * In v1 the home page alone had **four** ways of drawing this card and three
 * different field lists, so a field added to the product appeared in some
 * places and silently vanished from the others — nobody noticed until a
 * customer asked why the mileage showed on the auction page and not in search
 * results. Phase 005 closed the same hole on the backend side (T413,
 * `ops/checks/one_vehicle_card.py`); this is its counterpart in the web, and
 * `ops/checks/web_one_vehicle_card.mjs` fails the build on a second drawing.
 *
 * Everything shown here is a field the server already decided
 * ------------------------------------------------------------
 * `condition_label`, `colour_label` — the Arabic words come from the backend,
 * not from a map in this file. That is rule 3 (**لا قاعدة عمل في الويب**)
 * applied to the smallest possible case, and it matters at exactly this size:
 * a lookup table here is a second definition of what `accident` means in
 * Arabic, and the day somebody adds a condition the app shows it and the web
 * shows the raw enum.
 *
 * ما يُعرض هنا هو ما يعرضه v1 — لا أقلّ ولا أكثر
 * ------------------------------------------------
 * طلب المالك (2026-09-06): «نفس كل حاجة فيه بس بتصميمنا … كاملة بدون أي نقص
 * ولا زيادة»، والقياس في `specs/011-customer-web/v1-card-parity.md` مقروءاً
 * من الإنتاج الحيّ.
 *
 * فالحقول الأحد عشر: الرقم المرجعي · الصورة · العنوان · الموقف · سنة الصنع ·
 * اللون · الممشى · الحالة · الموقع · العدّاد · زرّ المزايدة. **ولا سعر**: كرت
 * v1 لا يعرضه، والقائمة نقطةٌ عامّة لا تطلب دخولاً — فسعرٌ فيها يُخبر كلَّ من
 * يفتحها بأقلّ ما يقبله البائع قبل أن يزايد أحد. ويصل السعر من يحتاجه عبر
 * `check_eligibility`.
 *
 * التصميم: مصفوفة مواصفاتٍ في وعاءٍ غائر
 * ---------------------------------------
 * الحقول الأربعة (سنة · لون · ممشى · حالة) في شبكة ٢×٢ داخل لوحٍ أفتح، وليس
 * زخرفة: العين تمسح **عموداً** من التسميات وعموداً من القيم بدل أن تتعقّب
 * أزواجاً متناثرة، وذلك ما يجعل مقارنة كرتين بنظرةٍ ممكنة. والموقع وحده سطرٌ
 * كامل لأنه أطولها («الرياض / طريق الحائر») وقسمتُه على عمودٍ نصفيّ تلفّه
 * سطرين.
 *
 * والحالة الضارّة (حادث · حريق · غرق) تُكتب بلون الخطأ **وبثخنٍ أزيد** —
 * لونٌ وحده لا يكفي لمن لا يفرّق الأحمر، والفرق هنا يقرّر شراءً.
 */

import Image from "next/image";
import Link from "next/link";

import type { Vehicle } from "@/lib/api";
import { count, remaining } from "@/lib/format";

import { Countdown } from "./Countdown";

export type { Vehicle };

/**
 * حالاتُ الضرر التي تُكتب بلون الخطأ.
 *
 * **قيمٌ لا نصوص**: `condition` رمزٌ من الخادم و`condition_label` كلمته
 * العربية. المقارنة بالرمز تنجو من تغيير الصياغة؛ ومقارنةُ «حادث» نصّاً تنكسر
 * صامتةً يوم تصير «مصدومة». وهذه ليست قاعدة عمل — لا تقرّر شيئاً، بل تختار
 * ثخانةً — والقرار (أيّ حالةٍ لهذه السيارة) اتُّخذ في الخادم.
 */
const DAMAGE = new Set(["accident", "fire", "flood"]);

/** شارةُ الطور فوق الصورة — كلمةٌ ولون، من `phase` وحده. */
const PHASE_BADGE: Record<string, { label: string; className: string }> = {
  soon: {
    label: "قريباً",
    className: "bg-warn-surface text-warn",
  },
  active: {
    label: "مفتوح للمزايدة",
    className: "bg-secondary-fixed text-on-secondary-fixed",
  },
  ended: {
    label: "منتهي",
    className: "bg-surface-container text-on-surface-variant",
  },
};

export function VehicleCard({
  vehicle,
  /** لحظة إنتاج الرد — منها ينطلق العدّاد. انظر `respondedAt`. */
  now,
  /**
   * أهذه أول بطاقة في الشبكة؟
   *
   * صورتها هي **أكبر عنصرٍ يُرسم** في الصفحة (LCP)، وNext يُحمّل صور
   * `next/image` كسولةً افتراضاً — فتُؤجَّل الصورةُ التي يقيس المتصفّح
   * سرعةَ الصفحة بها. والأولوية للأولى وحدها: إعطاؤها للعشرين يعني عشرين
   * طلباً متسابقاً، وهو عكس المقصود.
   */
  priority = false,
}: {
  vehicle: Vehicle;
  now: number;
  priority?: boolean;
}) {
  const countsTo =
    vehicle.phase === "soon" ? vehicle.auction_starts_at : vehicle.auction_ends_at;
  const badge = PHASE_BADGE[vehicle.phase ?? ""] ?? null;
  const damaged = DAMAGE.has(vehicle.condition);

  return (
    <article className="flex flex-col justify-between overflow-hidden rounded-xl bg-surface-lowest shadow-sm transition-transform duration-200 hover:-translate-y-1">
      <Link href={`/vehicles/${vehicle.id}`} className="block">
        <div className="relative aspect-[4/3] bg-surface-container">
          {/*
            الرقم المرجعي على الصورة، كما يضعه v1 (`#10565`). يذكره العميل حين
            يسأل الدعم، فموضعه حيث تقع العين أولاً لا في سطرٍ أسفل.
          */}
          <span className="tnum absolute end-3 top-3 z-10 rounded-sm bg-inverse-surface/85 px-2.5 py-1 text-caption font-bold tracking-wide text-inverse-on-surface backdrop-blur-md">
            {vehicle.reference}
          </span>

          {badge ? (
            <span
              className={`absolute start-3 top-3 z-10 flex items-center gap-1.5 rounded-sm px-2.5 py-1 text-label-sm ${badge.className}`}
            >
              <span
                aria-hidden="true"
                className="h-1.5 w-1.5 rounded-full bg-current"
              />
              {badge.label}
            </span>
          ) : null}

          {vehicle.thumbnail_url ? (
            <Image
              src={vehicle.thumbnail_url}
              alt={vehicle.title}
              fill
              priority={priority}
              sizes="(max-width: 768px) 100vw, 33vw"
              className="object-cover"
            />
          ) : (
            <div className="flex h-full flex-col items-center justify-center gap-1 text-on-surface-variant">
              <span aria-hidden="true" className="text-4xl opacity-40">
                🚗
              </span>
              <span className="text-label-md">لا توجد صورة</span>
            </div>
          )}
        </div>

        <div className="flex flex-col gap-3 p-6">
          <div className="flex items-start justify-between gap-2">
            <h3 className="text-headline-sm">{vehicle.title}</h3>
            {/* «الموقف» وحده. رقم المزاد لا يظهر على كرت v1. */}
            <span className="shrink-0 rounded-sm bg-surface-container px-2 py-0.5 text-label-sm font-medium">
              الموقف <span className="tnum">{count(vehicle.lot_number)}</span>
            </span>
          </div>

          {/*
            كل كلمة عربية هنا كلمةُ الخادم (`colour_label`, `condition_label`).
            جدولُ ترجمةٍ في هذا الملفّ يعني تعريفاً ثانياً لما تعنيه القيمة،
            ويوم تُضاف حالةٌ يعرضها التطبيقُ ويعرض الويبُ الرمز الخام.
          */}
          <dl className="grid grid-cols-2 gap-x-3 gap-y-2 rounded-lg bg-surface-low p-3 text-body-sm">
            <div className="flex items-center justify-between gap-2">
              <dt className="text-caption text-on-surface-variant">سنة الصنع:</dt>
              {/* بلا فاصل آلاف: السنة اسمٌ لا كمّية، و«2,022» خطأٌ يُقرأ. */}
              <dd className="tnum font-semibold">{vehicle.year}</dd>
            </div>
            <div className="flex items-center justify-between gap-2">
              <dt className="text-caption text-on-surface-variant">اللون:</dt>
              <dd className="font-semibold">{vehicle.colour_label}</dd>
            </div>
            <div className="flex items-center justify-between gap-2">
              <dt className="text-caption text-on-surface-variant">الممشى:</dt>
              <dd className="tnum font-semibold">
                {vehicle.odometer_km === null ? "—" : `${count(vehicle.odometer_km)} كم`}
              </dd>
            </div>
            <div className="flex items-center justify-between gap-2">
              <dt className="text-caption text-on-surface-variant">الحالة:</dt>
              <dd className={damaged ? "font-bold text-error" : "font-semibold"}>
                {vehicle.condition_label}
              </dd>
            </div>

            {/*
              الموقع سطرٌ كامل لأنه أطولها، ويُحذف كلّه حين يكون فارغاً: عنوانٌ
              فارغ بشرطة سؤالٌ بلا داعٍ.
            */}
            {vehicle.location ? (
              <div className="col-span-2 flex items-center justify-between gap-2 pt-1">
                <dt className="text-caption text-on-surface-variant">الموقع:</dt>
                <dd className="font-medium">{vehicle.location}</dd>
              </div>
            ) : null}
          </dl>
        </div>
      </Link>

      <div className="flex flex-col gap-2 p-6 pt-0">
        {/*
          العدّاد على الكرت لأن السؤال يُسأل عند الكرت: «كم بقي لهذه؟». وهو
          هنا لا في الصفحة، فيظهر في كل قائمة تعرض مركبة — شبكة الجذر وصفحة
          المزاد والمفضّلة — بلا أن يتذكّره أحد.

          ومزادٌ لم يبدأ يُعدّ إلى **بدايته** لا إلى نهايته، وكرت v1 يقول
          «يبدأ خلال». وقبل هذا كانت البطاقة تعدّ إلى الإغلاق وتكتب «يغلق بعد»
          على مزادٍ لم يفتح بعد — رقمٌ صحيح تحت عنوانٍ خاطئ، وهو أسوأ من لا
          رقم. وحين لا يرسل الخادم لحظةً لا يُرسم شيء: عدّادٌ من لا شيء كذبة.
        */}
        {countsTo ? (
          <Countdown
            endsAt={countsTo}
            label={vehicle.phase === "soon" ? "يبدأ خلال" : "يغلق بعد"}
            initial={remaining(countsTo, now)}
            now={now}
          />
        ) : null}

        {/*
          زرّ «مزايدة» — الحادي عشر في قائمة v1.

          **خارج `Link` لا داخله**: رابطٌ في رابطٍ وسمٌ غير صالح، والمتصفّحات
          تفكّه كلٌّ على هواها.

          ومزادٌ لم يبدأ يعرض الزرّ **معطَّلاً** كما يفعل v1 حرفياً (`disabled`
          على كل كرتٍ في تبويب «قريباً»). وليس هذا حكماً بالأهلية — تلك يقولها
          `check_eligibility` وحده ولا يُسأل هنا — بل هو الطور الذي قرّره
          الخادم وأرسله في `phase`، نفسه الذي يختار كلمة العدّاد فوقه. ومن
          يضغط الزرّ المفعَّل يصل صندوق المزايدة، وهناك يقول الخادم نعم أو لا
          بسببه المُعدَّد.

          والنصّ يتغيّر مع الحالة: «المزاد لم يبدأ بعد» و«المزاد مغلق» تقولان
          **لماذا** لا يعمل الزرّ، والرمادُ وحده لا يقول شيئاً.
        */}
        {vehicle.phase === "active" ? (
          <Link
            href={`/vehicles/${vehicle.id}`}
            className="flex h-11 items-center justify-center rounded-lg bg-primary text-label-md text-on-primary transition-opacity hover:opacity-90"
          >
            مزايدة
          </Link>
        ) : (
          <span
            aria-disabled="true"
            className="flex h-11 cursor-not-allowed items-center justify-center gap-2 rounded-lg bg-surface-container text-label-md text-on-surface-variant"
          >
            <span aria-hidden="true">🔒</span>
            {vehicle.phase === "ended" ? "المزاد مغلق" : "المزاد لم يبدأ بعد"}
          </span>
        )}
      </div>
    </article>
  );
}

/**
 * The grid every list uses, so spacing is not decided per screen either.
 *
 * `empty` تُمرَّر لأن **سبب** الفراغ يختلف باختلاف الشاشة: شبكةٌ فارغة في تبويب
 * «قريباً» تعني «لا مزاد قادم»، وفي نتيجة بحث تعني «لا مطابق لبحثك»، والجملتان
 * لا تُستنتج إحداهما من الأخرى هنا — من يعرف السياق هو من يستدعي. وما يبقى
 * واحداً هو أن الفراغ **يُشرح** ولا يُترك شبكةً بيضاء.
 */
export function VehicleGrid({
  vehicles,
  now,
  empty = "لا مركبات مطابقة.",
}: {
  vehicles: Vehicle[];
  now: number;
  empty?: string;
}) {
  if (vehicles.length === 0) {
    return (
      <div className="flex flex-col items-center gap-3 rounded-xl bg-surface-lowest p-12 text-center shadow-sm">
        <span aria-hidden="true" className="text-4xl opacity-40">
          🔍
        </span>
        <p className="text-body-md text-on-surface-variant">{empty}</p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
      {vehicles.map((vehicle, index) => (
        <VehicleCard
          key={vehicle.id}
          vehicle={vehicle}
          now={now}
          priority={index === 0}
        />
      ))}
    </div>
  );
}
