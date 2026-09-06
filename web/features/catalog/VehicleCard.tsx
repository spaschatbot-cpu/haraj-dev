/**
 * كرت المركبة — مكوَّن واحد، ولا رسم لكرت خارجه. T1010.
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
 * `state_label`, `condition_label`, `transmission_label` — the Arabic words come
 * from the backend, not from a map in this file. That is rule 3 (**لا قاعدة عمل
 * في الويب**) applied to the smallest possible case, and it matters at exactly
 * this size: a lookup table here is a second definition of what `awarded` means
 * in Arabic, and the day somebody adds a state the app shows it and the web
 * shows the raw enum.
 *
 * ما يُعرض هنا هو ما يعرضه v1 — لا أقلّ ولا أكثر
 * ------------------------------------------------
 * طلب المالك (2026-09-06): «نفس كل حاجة فيه بس بتصميمنا … كاملة بدون أي نقص
 * ولا زيادة»، والقياس في `specs/011-customer-web/v1-card-parity.md` مقروءاً
 * من الإنتاج الحيّ.
 *
 * فالحقول: الموقف · العنوان · سنة الصنع · اللون · الممشى · الحالة · الموقع ·
 * العدّاد · زرّ المزايدة. **ولا سعر**: كرت v1 لا يعرضه، والقائمة نقطةٌ عامّة
 * لا تطلب دخولاً — فسعرٌ فيها يُخبر كلَّ من يفتحها بأقلّ ما يقبله البائع قبل
 * أن يزايد أحد. ويصل السعر من يحتاجه عبر `check_eligibility`.
 *
 * وذهب معه ناقل الحركة والوقود ونوع اللوحة واسم الشركة ونصّ الحالة — ستّةٌ لا
 * يعرضها v1. وليست محذوفةً من النموذج: اللوحة تحرّرها وتقرؤها.
 */

import Image from "next/image";
import Link from "next/link";

import type { Vehicle } from "@/lib/api";
import { count, remaining } from "@/lib/format";

import { Countdown } from "./Countdown";

export type { Vehicle };

export function VehicleCard({
  vehicle,
  /** لحظة إنتاج الرد — منها ينطلق العدّاد. انظر `respondedAt`. */
  now,
}: {
  vehicle: Vehicle;
  now: number;
}) {
  return (
    <article className="overflow-hidden rounded-lg border border-neutral-200 bg-white">
      <Link href={`/vehicles/${vehicle.id}`} className="block">
        <div className="relative aspect-[4/3] bg-neutral-100">
          {vehicle.thumbnail_url ? (
            <Image
              src={vehicle.thumbnail_url}
              alt={vehicle.title}
              fill
              sizes="(max-width: 768px) 100vw, 33vw"
              className="object-cover"
            />
          ) : (
            <div className="flex h-full items-center justify-center text-sm text-neutral-500">
              لا توجد صورة
            </div>
          )}
        </div>

        <div className="p-4">
          <h3 className="font-semibold">{vehicle.title}</h3>

          <p className="mt-1 text-sm text-neutral-600">
            الموقف {count(vehicle.lot_number)} · مزاد {count(vehicle.auction_number)}
          </p>

          {/*
            كل كلمة عربية هنا كلمةُ الخادم (`colour_label`, `condition_label`).
            جدولُ ترجمةٍ في هذا الملفّ يعني تعريفاً ثانياً لما تعنيه القيمة،
            ويوم تُضاف حالةٌ يعرضها التطبيقُ ويعرض الويبُ الرمز الخام.
          */}
          <dl className="mt-3 grid grid-cols-2 gap-x-4 gap-y-1 text-sm text-neutral-700">
            <div className="flex gap-1">
              <dt className="text-neutral-500">سنة الصنع</dt>
              <dd>{count(vehicle.year)}</dd>
            </div>
            <div className="flex gap-1">
              <dt className="text-neutral-500">اللون</dt>
              <dd>{vehicle.colour_label}</dd>
            </div>
            <div className="flex gap-1">
              <dt className="text-neutral-500">الممشى</dt>
              <dd className="money">
                {vehicle.odometer_km === null ? "—" : `${count(vehicle.odometer_km)} كم`}
              </dd>
            </div>
            <div className="flex gap-1">
              <dt className="text-neutral-500">الحالة</dt>
              <dd>{vehicle.condition_label}</dd>
            </div>
          </dl>

          {/*
            الموقع سطرٌ وحده لأنه أطولها («الرياض / طريق الحائر»)، ويُحذف كلّه
            حين يكون فارغاً: عنوانٌ فارغ بشرطة سؤالٌ بلا داعٍ.
          */}
          {vehicle.location ? (
            <p className="mt-2 text-sm text-neutral-600">{vehicle.location}</p>
          ) : null}

          {/*
            العدّاد على الكرت لأن السؤال يُسأل عند الكرت: «كم بقي لهذه؟». وهو
            هنا لا في الصفحة، فيظهر في كل قائمة تعرض مركبة — شبكة الجذر وصفحة
            المزاد والمفضّلة — بلا أن يتذكّره أحد.

            وحين لا يرسل الخادم لحظة الانتهاء لا يُرسم شيء: عدّادٌ من لا شيء
            كذبة، وشرطةٌ مكانه سؤالٌ بلا داعٍ.
          */}
          {vehicle.auction_ends_at ? (
            <Countdown
              endsAt={vehicle.auction_ends_at}
              initial={remaining(vehicle.auction_ends_at, now)}
            />
          ) : null}
        </div>
      </Link>
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
    return <p className="py-12 text-center text-neutral-500">{empty}</p>;
  }

  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {vehicles.map((vehicle) => (
        <VehicleCard key={vehicle.id} vehicle={vehicle} now={now} />
      ))}
    </div>
  );
}
