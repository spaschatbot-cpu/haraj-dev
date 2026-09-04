/**
 * صفحة المركبة — مرندَرة في الخادم ببيانات وصفية حقيقية. T1009 / J5.
 *
 * This is the page the phase was designed around. «كامري 2022 مزاد» is what
 * people type into Google, and this route is what that search can land on — so
 * the name, the year, the mileage and the price are in the HTML that leaves the
 * server, before any script runs. J5 is tested exactly that way: a request with
 * no JavaScript must return the vehicle's name and its price.
 *
 * The price
 * ---------
 * `reserve_price`, and nothing else. It is not computed here, not compared with
 * a bid, not rounded and not formatted with a separator — it is the string the
 * server sent, rendered as it arrived (Article 3-2, and
 * `ops/checks/web_money_is_never_computed.mjs`). A "current price" that this
 * page worked out from anything would be a second answer to a question the
 * backend already answers, and the wrong one the moment a car is awarded to the
 * second bidder.
 *
 * The structured data
 * -------------------
 * A `Vehicle` JSON-LD block, built from the same fields the page renders. It
 * exists so a search result shows the year and the mileage rather than a bare
 * link — and it deliberately contains no `offers` price: an auction lot is not
 * an item at a fixed price, and marking a reserve as an offer price is a claim
 * that would be wrong the moment bidding starts.
 */

import type { Metadata } from "next";
import Image from "next/image";
import Link from "next/link";
import { cookies } from "next/headers";
import { notFound } from "next/navigation";

import { BidBox } from "@/features/bidding/BidBox";
import { LiveBids, type LiveBid } from "@/features/bidding/LiveBids";
import { FavouriteButton } from "@/features/favourites/FavouriteButton";
import { Notice } from "@/features/shell/Notice";
import { PageShell } from "@/features/shell/PageShell";
import { takeFlash } from "@/lib/flash";
import { authHeader, hasSession } from "@/lib/session";
import type { Vehicle } from "@/features/catalog/VehicleCard";
import { ApiError, api, request } from "@/lib/api";
import { amount, count } from "@/lib/format";
import { readNumber } from "@/lib/paging";

export const dynamic = "force-dynamic";

type Params = { params: Promise<{ id: string }> };

async function vehicleOr404(id: number): Promise<Vehicle> {
  try {
    return (await request(() =>
      api.GET("/api/v1/vehicles/{id}/", { params: { path: { id } } }),
    )) as Vehicle;
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) notFound();
    throw error;
  }
}

export async function generateMetadata({ params }: Params): Promise<Metadata> {
  const { id } = await params;
  const vehicle = await vehicleOr404(readNumber(id, 0));

  // A description built from the car's own facts. Not a template with the title
  // repeated: a search result that says the same thing twice is a result people
  // scroll past, and the mileage is the fact buyers actually read.
  const facts = [
    vehicle.condition_label,
    vehicle.transmission_label,
    vehicle.odometer_km === null ? null : `${count(vehicle.odometer_km)} كم`,
  ].filter(Boolean);

  return {
    title: vehicle.title,
    description: `${vehicle.title} — ${facts.join(" · ")}. لوت ${vehicle.lot_number} في مزاد ${vehicle.auction_number}.`,
    openGraph: {
      title: vehicle.title,
      description: facts.join(" · "),
      type: "website",
      ...(vehicle.thumbnail_url ? { images: [{ url: vehicle.thumbnail_url }] } : {}),
    },
  };
}

export default async function VehiclePage({ params }: Params) {
  const { id } = await params;
  const vehicle = await vehicleOr404(readNumber(id, 0));

  // Read here rather than inside the box: a server component reads cookies, and
  // pulling the flash once at the top is what keeps it a *one-shot* message —
  // two readers would consume it twice and show it in one place only, at random.
  const store = await cookies();
  const signedIn = hasSession(store);
  const flash = takeFlash(store);

  // Whether *this* customer has marked this car. Read from the server rather
  // than remembered in the browser: a heart that reflects a client-side toggle
  // shows filled for a request that failed, and the car is missing from the
  // list later with no clue when it went.
  // The caller's standing bid on this car, rendered by the server so the live
  // component has something correct to show before it connects — and so a
  // visitor whose script never runs still sees a true number.
  let standing: LiveBid | null = null;
  let marked = false;
  if (signedIn) {
    try {
      const mine = await request(() =>
        api.GET("/api/v1/bids/mine/", {
          headers: authHeader(store),
          params: { query: { limit: 100, offset: 0 } },
        }),
      );
      standing =
        ((mine.results ?? []).find(
          (row) => (row as { vehicle_id: number }).vehicle_id === vehicle.id,
        ) as LiveBid | undefined) ?? null;
    } catch {
      standing = null;
    }

    try {
      const saved = await request(() =>
        api.GET("/api/v1/favourites/", {
          headers: authHeader(store),
          params: { query: { limit: 100, offset: 0 } },
        }),
      );
      marked = (saved.results ?? []).some(
        (row) => (row as { id: number }).id === vehicle.id,
      );
    } catch {
      // A favourites read that fails must not take the page down with it. The
      // car, its price and its specification are what this page is for, and a
      // hollow heart is a smaller loss than a 500 on a page arriving from a
      // search result.
      marked = false;
    }
  }

  const structured = {
    "@context": "https://schema.org",
    "@type": "Vehicle",
    name: vehicle.title,
    brand: { "@type": "Brand", name: vehicle.make },
    model: vehicle.model,
    vehicleModelDate: String(vehicle.year),
    vehicleTransmission: vehicle.transmission_label,
    fuelType: vehicle.fuel_type_label,
    ...(vehicle.odometer_km === null
      ? {}
      : {
          mileageFromOdometer: {
            "@type": "QuantitativeValue",
            value: vehicle.odometer_km,
            unitCode: "KMT",
          },
        }),
    ...(vehicle.thumbnail_url ? { image: vehicle.thumbnail_url } : {}),
  };

  const specifications: Array<[string, string]> = [
    ["الماركة", vehicle.make],
    ["الطراز", vehicle.model],
    ["سنة الصنع", String(vehicle.year)],
    ["الحالة", vehicle.condition_label],
    ["ناقل الحركة", vehicle.transmission_label],
    ["الوقود", vehicle.fuel_type_label],
    ["نوع اللوحة", vehicle.plate_type_label],
    ["الممشى", vehicle.odometer_km === null ? "—" : `${count(vehicle.odometer_km)} كم`],
    ["رقم اللوت", count(vehicle.lot_number)],
    ["المالك", vehicle.owner_company_name ?? "—"],
  ];

  return (
    <PageShell>
      <script
        type="application/ld+json"
        // The object is built above from typed fields, so there is no user text
        // reaching this string that was not already rendered on the page.
        dangerouslySetInnerHTML={{ __html: JSON.stringify(structured) }}
      />

      <nav className="mb-4 text-sm text-neutral-600">
        <Link href="/" className="hover:underline">
          المزادات
        </Link>
        {" · "}
        <Link href={`/auctions/${vehicle.auction_number}`} className="hover:underline">
          مزاد {count(vehicle.auction_number)}
        </Link>
      </nav>

      <div className="grid gap-8 lg:grid-cols-2">
        <div className="relative aspect-[4/3] overflow-hidden rounded-lg bg-neutral-100">
          {vehicle.thumbnail_url ? (
            <Image
              src={vehicle.thumbnail_url}
              alt={vehicle.title}
              fill
              sizes="(max-width: 1024px) 100vw, 50vw"
              className="object-cover"
              priority
            />
          ) : (
            <div className="flex h-full items-center justify-center text-neutral-500">
              لا توجد صورة
            </div>
          )}
        </div>

        <div>
          <h1 className="text-2xl font-bold">{vehicle.title}</h1>

          <div className="mt-2 flex flex-wrap items-center gap-3">
            <p className="text-sm text-neutral-600">
              {vehicle.state_label} · لوت {count(vehicle.lot_number)}
            </p>
            {signedIn ? (
              <FavouriteButton
                vehicleId={vehicle.id}
                marked={marked}
                back={`/vehicles/${vehicle.id}`}
              />
            ) : null}
          </div>

          <p className="mt-6 flex items-baseline gap-2">
            <span className="text-neutral-500">سعر الوقوف</span>
            {vehicle.reserve_price === null ? (
              <span className="text-neutral-500">لم يُحدَّد</span>
            ) : (
              <span className="money text-2xl font-bold">
                {amount(vehicle.reserve_price)} ريال
              </span>
            )}
          </p>

          <dl className="mt-6 divide-y divide-neutral-200 border-y border-neutral-200 text-sm">
            {specifications.map(([label, value]) => (
              <div key={label} className="flex justify-between gap-4 py-2">
                <dt className="text-neutral-500">{label}</dt>
                <dd className="text-neutral-900">{value}</dd>
              </div>
            ))}
          </dl>

          <Notice
            message={flash?.message ?? ""}
            tone={flash?.code === "bid_placed" ? "info" : "error"}
          />

          {signedIn ? (
            <>
              <LiveBids vehicleId={vehicle.id} initial={standing} />
              <BidBox vehicleId={vehicle.id} flash={flash} />
            </>
          ) : (
            /*
              A link, not a disabled box. Somebody who is not signed in cannot
              bid, and that is a fact about the session rather than a judgement
              about them — so the page says what to do instead of showing a
              control that refuses.
            */
            <p className="mt-8 rounded-lg border border-neutral-200 bg-white p-4 text-sm">
              <Link href="/sign-in" className="underline">
                سجّل دخولك
              </Link>{" "}
              للمزايدة على هذه المركبة.
            </p>
          )}
        </div>
      </div>
    </PageShell>
  );
}
