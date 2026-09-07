/**
 * صفحة المركبة — مرندَرة في الخادم ببيانات وصفية حقيقية. T1009 / J5.
 *
 * This is the page the phase was designed around. «كامري 2022 مزاد» is what
 * people type into Google, and this route is what that search can land on — so
 * the name, the year, the mileage and the price are in the HTML that leaves the
 * server, before any script runs. J5 is tested exactly that way: a request with
 * no JavaScript must return the vehicle's name and its price.
 *
 * ولا سعرَ على الصفحة — ولا مبلغٌ يُحسب فيها
 * ==========================================
 * نافذة v1 لا تعرض سعراً للسيارة، وهذه الصفحة نظيرها: الصفحة تُفتح بلا دخول،
 * فسعرٌ عليها يُخبر كلَّ من يفتحها بأقلّ ما يقبله البائع قبل أن يزايد أحد.
 * والمبالغ الوحيدة التي تظهر هنا هي رسوم المزايدة، وتصل **محسوبةً من الخادم**
 * (`admin_fee`, `admin_fee_with_vat`) — لا يضرب هذا الملفّ مبلغاً في نسبة،
 * ولا يقارنه بشيء (المادة ٣-٢، و`ops/checks/web_money_is_never_computed.mjs`).
 *
 * ومعرض الصور نداءٌ ثانٍ لا حقلٌ على الكرت — HR-12ب، والسبب في
 * `VehicleImageListView`.
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
import Link from "next/link";
import { cookies } from "next/headers";
import { notFound } from "next/navigation";

import { BidBox } from "@/features/bidding/BidBox";
import { Gallery, type Shot } from "@/features/catalog/Gallery";
import { LiveBids, type LiveBid } from "@/features/bidding/LiveBids";
import { FavouriteButton } from "@/features/favourites/FavouriteButton";
import { Notice } from "@/features/shell/Notice";
import { PageShell } from "@/features/shell/PageShell";
import { readFlash } from "@/lib/flash";
import { authHeader, hasSession } from "@/lib/session";
import type { Vehicle } from "@/features/catalog/VehicleCard";
import { ApiError, api, request } from "@/lib/api";
import { count } from "@/lib/format";
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
    vehicle.colour_label,
    vehicle.odometer_km === null ? null : `${count(vehicle.odometer_km)} كم`,
  ].filter(Boolean);

  return {
    title: vehicle.title,
    description: `${vehicle.title} — ${facts.join(" · ")}. الموقف ${vehicle.lot_number} في مزاد ${vehicle.auction_number}.`,
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

  // معرض الصور — نقطةٌ ثانية لأن الكرت لا يحملها (HR-12ب، وسببُ الانفصال في
  // `VehicleImageListView`). ويُقرأ هنا في الخادم فتصل الصورة الأولى وعدّادُها
  // في الـHTML، ويفشل بلا أن يُسقط الصفحة: سيارةٌ بلا معرضٍ أهونُ من 500 على
  // صفحةٍ قادمةٍ من نتيجة بحث.
  let shots: Shot[] = [];
  try {
    const gallery = await request(() =>
      api.GET("/api/v1/vehicles/{id}/images/", { params: { path: { id: vehicle.id } } }),
    );
    shots = (gallery.results ?? []) as Shot[];
  } catch {
    shots = [];
  }

  // Read here rather than inside the box: a server component reads cookies, and
  // pulling the flash once at the top is what keeps it a *one-shot* message —
  // two readers would consume it twice and show it in one place only, at random.
  const store = await cookies();
  const signedIn = hasSession(store);
  const flash = readFlash(store);

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
    color: vehicle.colour_label,
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

  // «مواصفات المركبة» كما تعرضها نافذة v1 عند الضغط على الكرت — خمسةٌ لا غير،
  // مقروءةٌ من الإنتاج الحيّ (`specs/011-customer-web/v1-card-parity.md`).
  // والممشى الفارغ شرطةٌ لا صفر، كما يفعل v1 حرفياً: مركبةٌ لم يُقَس ممشاها
  // ليست مركبةً ممشاها صفر.
  const specifications: Array<[string, string]> = [
    ["الموديل", `${vehicle.make} ${vehicle.model}`],
    ["سنة الصنع", String(vehicle.year)],
    ["اللون", vehicle.colour_label],
    ["الممشى", vehicle.odometer_km === null ? "—" : `${count(vehicle.odometer_km)} كم`],
    ["المدينة", vehicle.location || "—"],
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
        {/*
          المعرض لا صورةً واحدة. وحين لا يجيب نداءُ الصور تُعرض صورة الغلاف
          التي وصلت مع الكرت أصلاً — فالصفحة لا تفقد صورتها لأن نداءً ثانياً
          سقط.
        */}
        <Gallery
          shots={
            shots.length > 0
              ? shots
              : vehicle.thumbnail_url
                ? [
                    {
                      id: vehicle.id,
                      thumbnail_url: vehicle.thumbnail_url,
                      preview_url: null,
                      is_cover: true,
                    },
                  ]
                : []
          }
          alt={vehicle.title}
        />

        <div>
          <h1 className="text-2xl font-bold">{vehicle.title}</h1>

          <div className="mt-2 flex flex-wrap items-center gap-3">
            <p className="text-sm text-neutral-600">
              الموقف {count(vehicle.lot_number)}
            </p>
            {signedIn ? (
              <FavouriteButton
                vehicleId={vehicle.id}
                marked={marked}
                back={`/vehicles/${vehicle.id}`}
              />
            ) : null}
          </div>

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
              <BidBox
                vehicleId={vehicle.id}
                flash={flash}
                adminFee={vehicle.admin_fee}
                adminFeeWithVat={vehicle.admin_fee_with_vat}
              />
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
