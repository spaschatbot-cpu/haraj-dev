/**
 * كرت المزاد — نظير `VehicleCard`، وللسبب نفسه.
 *
 * One component, one field list. The auction list and any future place that
 * shows an auction read the same rows, so a field added here appears in both
 * rather than in whichever one somebody remembered.
 *
 * `state_label` and the counts come from the server. The web does not decide
 * what «جارٍ» means, and does not count vehicles itself: `vehicle_count` and
 * `open_vehicle_count` are annotated once in `apps/auctions/listing.py`, which
 * is what stops the app and the web disagreeing about how many cars an auction
 * holds.
 */

import Link from "next/link";

import type { components } from "@/lib/api";
import { count, dateTime } from "@/lib/format";

export type Auction = components["schemas"]["AuctionCard"];

export function AuctionCard({ auction }: { auction: Auction }) {
  return (
    <article className="rounded-lg border border-neutral-200 bg-white p-4">
      <Link href={`/auctions/${auction.id}`} className="block">
        <div className="flex items-baseline justify-between gap-2">
          <h3 className="font-semibold">{auction.title}</h3>
          <span className="shrink-0 rounded bg-neutral-100 px-2 py-0.5 text-xs text-neutral-700">
            {auction.state_label}
          </span>
        </div>

        <p className="mt-1 text-sm text-neutral-600">مزاد رقم {count(auction.number)}</p>

        <dl className="mt-3 space-y-1 text-sm text-neutral-700">
          <div className="flex gap-2">
            <dt className="text-neutral-500">يبدأ</dt>
            <dd>{dateTime(auction.starts_at)}</dd>
          </div>
          <div className="flex gap-2">
            <dt className="text-neutral-500">ينتهي</dt>
            <dd>{dateTime(auction.ends_at)}</dd>
          </div>
          <div className="flex gap-2">
            <dt className="text-neutral-500">المركبات</dt>
            {/*
              Both numbers, because they answer different questions: how big is
              this auction, and how much of it can still be bid on. Showing only
              the total is what made a nearly-sold auction look full in v1.
            */}
            <dd className="money">
              {count(auction.open_vehicle_count)} مفتوحة من {count(auction.vehicle_count)}
            </dd>
          </div>
        </dl>
      </Link>
    </article>
  );
}
