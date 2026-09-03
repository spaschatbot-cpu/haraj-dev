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
 * The price is `reserve_price` and nothing else (T1009). It is rendered as the
 * string it arrived as: no `Number`, no rounding, no separator. See
 * `lib/format.ts`.
 */

import Image from "next/image";
import Link from "next/link";

import type { components } from "@/lib/api";
import { amount, count } from "@/lib/format";

export type Vehicle = components["schemas"]["VehicleCard"];

export function VehicleCard({ vehicle }: { vehicle: Vehicle }) {
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
            <div className="flex h-full items-center justify-center text-sm text-neutral-400">
              لا توجد صورة
            </div>
          )}
        </div>

        <div className="p-4">
          <h3 className="font-semibold">{vehicle.title}</h3>

          <p className="mt-1 text-sm text-neutral-600">
            لوت {count(vehicle.lot_number)} · مزاد {count(vehicle.auction_number)}
          </p>

          {/*
            Every label is the server's own word. A translation table here would
            be a second place that decides what a state is called in Arabic.
          */}
          <dl className="mt-3 grid grid-cols-2 gap-x-4 gap-y-1 text-sm text-neutral-700">
            <div className="flex gap-1">
              <dt className="text-neutral-500">الحالة</dt>
              <dd>{vehicle.state_label}</dd>
            </div>
            <div className="flex gap-1">
              <dt className="text-neutral-500">الممشى</dt>
              <dd className="money">
                {vehicle.odometer_km === null ? "—" : `${count(vehicle.odometer_km)} كم`}
              </dd>
            </div>
            <div className="flex gap-1">
              <dt className="text-neutral-500">ناقل الحركة</dt>
              <dd>{vehicle.transmission_label}</dd>
            </div>
            <div className="flex gap-1">
              <dt className="text-neutral-500">الوقود</dt>
              <dd>{vehicle.fuel_type_label}</dd>
            </div>
          </dl>

          <p className="mt-3 flex items-baseline gap-2">
            <span className="text-sm text-neutral-500">سعر الوقوف</span>
            {vehicle.reserve_price === null ? (
              // Not "0", and not blank: a car whose owner has not set a floor is
              // a different thing from a car whose floor is zero, and printing a
              // number for the first is a number nobody chose.
              <span className="text-neutral-500">لم يُحدَّد</span>
            ) : (
              <span className="money text-lg font-semibold">
                {amount(vehicle.reserve_price)} ريال
              </span>
            )}
          </p>
        </div>
      </Link>
    </article>
  );
}

/** The grid every list uses, so spacing is not decided per screen either. */
export function VehicleGrid({ vehicles }: { vehicles: Vehicle[] }) {
  if (vehicles.length === 0) {
    return <p className="py-12 text-center text-neutral-500">لا مركبات مطابقة.</p>;
  }

  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {vehicles.map((vehicle) => (
        <VehicleCard key={vehicle.id} vehicle={vehicle} />
      ))}
    </div>
  );
}
