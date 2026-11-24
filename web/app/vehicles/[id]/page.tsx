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

type Neighbour = { id: number; lot_number: number; title: string };

/**
 * السيّارةُ قبلها وبعدها في المزاد نفسه، بترتيب الموقف — لسهمَي «السابقة»
 * و«التالية» (المالك، ٢٤ نوفمبر ٢٠٢٦: «سهمين تحرّك بين السيارات… للمزاد
 * الواحد»).
 *
 * **ولا حقلَ جديدٌ في العقد لهذا.** قائمةُ المركبات مرتّبةٌ في الخادم
 * بـ`(auction_id, lot_number)` (`apps/auctions/listing.py`) وتُصفّى بالمزاد،
 * فالجارتان هما ما قبلها وما بعدها في تلك القائمة نفسِها — بالتصفية نفسِها
 * التي يراها العميل، فلا يقود السهمُ إلى مركبةٍ لا تُعرض.
 *
 * والمواقفُ في v1 متتالية في الغالب (١، ٢، ٣…)، فالمحاولةُ الأولى نافذةٌ من
 * ثلاثٍ حول `lot - 1`: طلبٌ واحد. وحين تكون فيها فجوةٌ (موقفٌ سُحب) لا تقع
 * السيّارةُ في الوسط، فتُقرأ القائمةُ صفحاتٍ من مئة حتى تُوجد — والمزادُ
 * الأكبرُ ٤٠٦ سيّارات، أي خمسُ طلباتٍ في أسوأ حال.
 */
async function neighboursOf(
  vehicle: Vehicle,
): Promise<{ previous: Neighbour | null; next: Neighbour | null }> {
  type Card = { id: number; lot_number: number; title: string };
  const slice = async (offset: number, limit: number): Promise<{ rows: Card[]; total: number }> => {
    const page = await request(() =>
      api.GET("/api/v1/vehicles/", {
        // ‏والطورُ صراحةً: بلاه يختار الخادمُ تبويباً بنفسه (نشط ← قريب ←
        // منتهي)، فقد تُقرأ قائمةٌ غيرُ التي فيها هذه السيّارة.
        params: {
          query: {
            auction: vehicle.auction_id,
            phase: (vehicle.phase ?? "") as "soon" | "active" | "ended" | "",
            offset,
            limit,
          },
        },
      }),
    );
    return { rows: (page.results ?? []) as Card[], total: page.total ?? 0 };
  };
  const around = (rows: Card[], index: number) => ({
    previous: rows[index - 1] ?? null,
    next: rows[index + 1] ?? null,
  });

  try {
    const offset = Math.max(0, vehicle.lot_number - 2);
    const first = await slice(offset, 3);
    const index = first.rows.findIndex((row) => row.id === vehicle.id);
    // في الوسط، أو أوّلُ القائمة كلِّها، أو آخرُها — فالنافذةُ تكفي.
    if (index === 1 || (index === 0 && offset === 0) || (index >= 0 && offset + index === first.total - 1)) {
      return around(first.rows, index);
    }
    for (let start = 0; start < Math.min(first.total, 1000); start += 100) {
      const { rows } = await slice(Math.max(0, start - 1), 102);
      const at = rows.findIndex((row) => row.id === vehicle.id);
      if (at >= 0) return around(rows, at);
    }
  } catch {
    // السهمان راحةٌ لا شرط: صفحةُ المركبة تُعرض بلاهما.
  }
  return { previous: null, next: null };
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
  const neighbours = await neighboursOf(vehicle);

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
  //: ‏بيانات v1 تكتب الاسمَ كاملاً في الصانع والطراز معاً («بكب جمس سيرا»
  //: في الاثنين)، فكان السطرُ «بكب جمس سيرا بكب جمس سيرا». يُعرض الطرازُ
  //: وحده حين يحمل الصانعَ في أوّله، أو حين يتطابقان.
  const model = vehicle.model.trim();
  const make = vehicle.make.trim();
  const modelLine = !make || model === make || model.startsWith(make) ? model || make : `${make} ${model}`;

  const specifications: Array<{ label: string; value: string; icon: SpecIcon }> = [
    { label: "الموديل", value: modelLine, icon: "car" },
    { label: "سنة الصنع", value: String(vehicle.year), icon: "calendar" },
    { label: "اللون", value: vehicle.colour_label, icon: "palette" },
    {
      label: "الممشى",
      value: vehicle.odometer_km === null ? "—" : `${count(vehicle.odometer_km)} كم`,
      icon: "gauge",
    },
    { label: "الحالة", value: vehicle.condition_label, icon: "shield" },
    //: الوقودُ وناقلُ الحركة يُحذفان حين لا يعرفهما الخادم («غير محدد»):
    //: بلاطةٌ تقول «لا نعرف» تأخذ مكانَ معلومةٍ ولا تعطي شيئاً. ونقلُ v1 لا
    //: يحملهما في أغلب السيّارات.
    ...(known(vehicle.fuel_type_label)
      ? [{ label: "الوقود", value: vehicle.fuel_type_label, icon: "fuel" as const }]
      : []),
    ...(known(vehicle.transmission_label)
      ? [{ label: "ناقل الحركة", value: vehicle.transmission_label, icon: "gear" as const }]
      : []),
  ];

  //: ‏ما يعرضه v1 في نافذة «مواصفات المركبة» (`index.php` ‏`#specsModal`) ولم
  //: تكن الصفحةُ تقوله وهو عندنا: رقمُ الهيكل وحالةُ المحرّك والمفاتيح ونوعُ
  //: اللوحة والموقع (المالك، ٢٤ نوفمبر ٢٠٢٦: «بيانات السيارة مش كاملة»).
  const registration: Array<{ label: string; value: string; mono?: boolean }> = [
    { label: "رقم الهيكل", value: vehicle.vin, mono: true },
    { label: "حالة المحرّك", value: vehicle.runs_status },
    { label: "المفاتيح", value: vehicle.key_status },
    { label: "نوع اللوحة", value: vehicle.plate_type_label },
    { label: "الموقع", value: vehicle.location },
    { label: "الرقم المرجعي", value: vehicle.reference, mono: true },
  ].filter((row) => known(row.value));
  //: الموديلُ بعرض السطر، وما بعده زوجان زوجان — والأخيرُ يمتدّ إن بقي فرداً.
  const wide = (index: number) =>
    index === 0 || (index === specifications.length - 1 && (specifications.length - 1) % 2 === 1);

  return (
    <PageShell>
      <script
        type="application/ld+json"
        // The object is built above from typed fields, so there is no user text
        // reaching this string that was not already rendered on the page.
        dangerouslySetInnerHTML={{ __html: JSON.stringify(structured) }}
      />

      {/*
        **المسارُ في برواز مدوَّرٍ لبنيّ** (قرارُ المالكة، ٥ أكتوبر ٢٠٢٦).
        كان سطراً رماديّاً عائماً فوق الصورة، يُقرأ هامشاً لا طريقاً — وهو
        طريقُ الرجوع: «المزادات» و«مزاد ١٩١٤» رابطان يُضغطان.

        و`inline-block` لا `block`: البروازُ يلفّ الكلامَ وحدَه لا عرضَ
        الصفحة — إطارٌ ممتدٌّ على فراغٍ يُقرأ شريطاً فارغاً. **ولا
        `inline-flex`**: جُرّبت فابتلعت المسافاتِ حول الفاصلة فصارت
        «المزادات·مزاد ١٩١٤» — العناصرُ في `flex` صناديقُ لا كلماتٌ في سطر،
        والمسافةُ النصّيّةُ بينها تُطوى.

        واللونُ من عائلة المشروع (`--color-surface-low` و`--color-surface-high`)
        لا لبنيٌّ يُخترع: الصفحةُ كلُّها على هذه العائلة، ولونٌ خامسٌ يجعل
        الشاشةَ تقول خمسةَ أشياء.
      */}
      {/*
        شريطُ الصفحة: «رجوع» يخرج إلى القائمة، والمسارُ في الوسط، وسهمان إلى
        السيّارة السابقة والتالية في المزاد نفسه (المالك، ٢٤ نوفمبر ٢٠٢٦).

        و«رجوع» رابطٌ إلى تبويب حالتها لا `history.back()`: من تنقّل بين عشر
        سيّاراتٍ بالسهمين يعني بـ«رجوع» الخروجَ من التفاصيل، لا السيّارةَ
        التاسعة. والسهمان `replace` للسبب نفسِه — لا يُراكمان التاريخ، فزرُّ
        الرجوع في المتصفّح يخرج كذلك.
      */}
      <div className="mb-4 flex flex-wrap items-center gap-2">
        <Link href={`/?phase=${vehicle.phase ?? "active"}`} className="vd-nav-btn inline-flex items-center gap-1.5 rounded-full px-3.5 py-1.5 text-label-md">
          <svg viewBox="0 0 24 24" aria-hidden="true" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M9 6l6 6-6 6" />
          </svg>
          رجوع
        </Link>

      <nav className="tone-navy inline-block rounded-full border px-4 py-1.5 text-sm font-medium">
        <Link href="/" className="hover:underline">
          المزادات
        </Link>
        {" · "}
        {/* ‏المعرّفُ في الرابط، والرقمُ في النصّ — وهما شيئان مختلفان.
            كان الاثنان `auction_number`، فكانت كلُّ مركبةٍ تربط إلى ٤٠٤:
            الممرُّ `/auctions/[id]` يسأل `/api/v1/auctions/{id}/` بالمفتاح،
            ورقمُ المزاد رقمٌ معروضٌ للناس لا مفتاحٌ في القاعدة. قِيس على
            مركبة 25970 (مزادُها رقمُه 992833 ومفتاحُه 61): الرابطُ بالرقم
            يردّ 404 وبالمفتاح 200. */}
        <Link href={`/auctions/${vehicle.auction_id}`} className="hover:underline">
          مزاد <span className="tnum">{vehicle.auction_number}</span>
        </Link>
      </nav>

        {neighbours.previous || neighbours.next ? (
          <div className="ms-auto flex items-center gap-2">
            {neighbours.previous ? (
              <Link
                href={`/vehicles/${neighbours.previous.id}`}
                replace
                title={neighbours.previous.title}
                aria-label={`السيّارة السابقة: ${neighbours.previous.title}`}
                className="vd-nav-btn inline-flex items-center gap-1.5 rounded-full px-3.5 py-1.5 text-label-md"
              >
                <svg viewBox="0 0 24 24" aria-hidden="true" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M9 6l6 6-6 6" />
                </svg>
                السابقة
                <span className="tnum text-caption opacity-70">#{neighbours.previous.lot_number}</span>
              </Link>
            ) : null}
            {neighbours.next ? (
              <Link
                href={`/vehicles/${neighbours.next.id}`}
                replace
                title={neighbours.next.title}
                aria-label={`السيّارة التالية: ${neighbours.next.title}`}
                className="vd-nav-btn inline-flex items-center gap-1.5 rounded-full px-3.5 py-1.5 text-label-md"
              >
                <span className="tnum text-caption opacity-70">#{neighbours.next.lot_number}</span>
                التالية
                <svg viewBox="0 0 24 24" aria-hidden="true" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M15 6l-6 6 6 6" />
                </svg>
              </Link>
            ) : null}
          </div>
        ) : null}
      </div>

      <div className="grid items-start gap-6 lg:grid-cols-[minmax(0,1.25fr)_minmax(0,1fr)]">
        {/*
          المعرض لا صورةً واحدة. وحين لا يجيب نداءُ الصور تُعرض صورة الغلاف
          التي وصلت مع الكرت أصلاً — فالصفحة لا تفقد صورتها لأن نداءً ثانياً
          سقط.
        */}
        {/*
          **برواز حول الصورة** (قرارُ المالكة، ٥ أكتوبر ٢٠٢٦). كانت الصورةُ
          تلتصق بخلفيّة الصفحة بلا حدّ، وأكثرُ صور المزاد داكنةٌ أو بيضاء —
          فالداكنةُ تسيل في الصفحة والبيضاءُ تذوب فيها، وفي الحالتين لا
          يُعرف أين تنتهي.

          والإطارُ على الغلاف لا على الصورة نفسِها: `Gallery` يبني مصغّراتٍ
          تحتها، وإطارٌ داخلَه كان سيؤطّر كلَّ مصغَّرةٍ وحدَها.
        */}
        <div className="spec-panel vd-panel overflow-hidden rounded-3xl p-2.5">
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
        </div>

        {/*
          **إطارٌ حول العمود الأيمن.** كان الاسمُ والمواصفاتُ وسطرُ المزايدة
          عائمةً على خلفيّة الصفحة بلا حدّ، فلا يُقرأ أين تبدأ كتلةُ القرار
          وأين تنتهي. والبطاقةُ بيضاءُ بحدٍّ شعريّ — كبطاقات المركبات في
          الشبكة، فتتّفق الشاشتان.
        */}
        <div className="spec-panel vd-panel rounded-3xl p-5 md:p-6">
          {/*
            **الاسمُ في إطارٍ ملوّن** (قرارُ المالكة، ٥ أكتوبر ٢٠٢٦). وهو
            أوّلُ ما تقع عليه العين في العمود، وكان نصّاً عارياً فوق سطورٍ
            رماديّة: يُقرأ جزءاً من القائمة لا عنواناً لها.

            والشريطُ الملوّن على الحافّة لا إطارٌ كامل: إطارٌ من أربع جهاتٍ
            حول عنوانٍ داخل بطاقةٍ لها إطارُها يصير إطارين متداخلين. والشريطُ
            يقول «هنا يبدأ» بخطٍّ واحد.

            واللونُ كحليُّ الباليت «ج» نفسُه الذي في الرئيسيّة (٥ أكتوبر ٢٠٢٦:
            «طبّقي نفس الألوان على صفحة المركبة») — لا لونٌ يُخترع لهذه الصفحة.
            والألوانُ كلُّها في `globals.css` (`.vd-*` و`tone-navy`).
          */}
          <div className="tone-navy vd-title rounded-2xl border p-5">
            <h1 className="text-3xl font-bold leading-tight md:text-4xl">
              {vehicle.title}
            </h1>
          </div>

          <div className="mt-3 flex flex-wrap items-center gap-3">
            {/* الموقفُ شريحةٌ لا سطرٌ باهت: هو ما يُنادى به في الحوش. */}
            <p className="tone-navy rounded-full border px-3.5 py-1 text-sm font-medium">
              الموقف <span className="tnum font-medium">{vehicle.lot_number}</span>
            </p>
            {signedIn ? (
              <FavouriteButton
                vehicleId={vehicle.id}
                marked={marked}
                back={`/vehicles/${vehicle.id}`}
              />
            ) : null}
          </div>

          {/*
            **نفسُ التنظيم، وأوضحُ قراءةً** (قرارُ المالكة، ٥ أكتوبر ٢٠٢٦:
            «نفس التنظيم بس نغيّر في فونت الكلام ونكبّر الكلام»). السطورُ
            كما هي: الاسمُ يميناً والقيمةُ يساراً، بالترتيب نفسِه — ولا كلمةَ
            تتغيّر.

            والذي تغيّر ثلاثةٌ: **القيمةُ أكبرُ وأثقل** من اسمها فيُقرأ
            «2022» قبل «سنة الصنع» — وهو ما تبحث عنه العين؛ و**الاسمُ
            بحروفٍ متباعدة** قليلاً فيُقرأ عنواناً لا جاراً للقيمة؛ وصفٌّ
            يُضيء عند المرور عليه فيُتتبَّع بالعين إلى آخره — والفراغُ
            الممتدُّ بين الطرفين هو ما كان يُفقد التتبّع.

            والخطُّ هو هو (`--font-arabic` في `globals.css`): خطٌّ ثانٍ على
            صفحةٍ واحدةٍ يُحمَّل ملفّاً ويتأخّر فيقفز النصّ.
          */}
          {/*
            بلاطاتٌ لا سطورٌ مخطّطة (٢٤ نوفمبر ٢٠٢٦، المالك: «الموديل وسنة
            الصنع واللون والممشى… داخلة في بعضها»). كانت صفوفاً متناوبةَ
            اللون بحافّةٍ ملوّنة، فتلتصق القيمةُ الطويلة بالاسم ويُقرأ صفّان
            واحداً. وكلُّ بلاطةٍ الآن وحدةٌ مقفلة: أيقونة، ثم الاسمُ صغيراً،
            ثم القيمةُ كبيرة — والعينُ تبحث عن القيمة.
          */}
          <dl className="mt-5 grid grid-cols-2 gap-2.5">
            {specifications.map(({ label, value, icon }, index) => (
              <div
                key={label}
                style={{ animationDelay: `${index * 45}ms` }}
                className={`spec-tile flex items-center gap-3 rounded-xl p-3 ${
                  wide(index) ? "col-span-2" : ""
                }`}
              >
                <span aria-hidden="true" className="spec-tile-icon flex h-9 w-9 shrink-0 items-center justify-center rounded-lg">
                  <SpecGlyph name={icon} />
                </span>
                <div className="min-w-0">
                  <dt className="spec-label text-caption">{label}</dt>
                  <dd className="truncate text-base font-semibold" title={value}>
                    {value}
                  </dd>
                </div>
              </div>
            ))}
          </dl>

          {registration.length > 0 ? (
            <section className="mt-5" aria-labelledby="reg-title">
              <h2 id="reg-title" className="mb-2 text-label-md font-bold text-on-surface-variant">
                بيانات المركبة
              </h2>
              <dl className="reg-list divide-y overflow-hidden rounded-xl border">
                {registration.map(({ label, value, mono }) => (
                  <div key={label} className="flex items-center justify-between gap-4 px-4 py-2.5">
                    <dt className="text-body-sm">{label}</dt>
                    <dd
                      dir={mono ? "ltr" : undefined}
                      className={`text-end font-semibold ${mono ? "tnum tracking-wide" : ""}`}
                    >
                      {value}
                    </dd>
                  </div>
                ))}
              </dl>
            </section>
          ) : null}

          {/*
            «تفاصيل المزايدة» في v1: الرسومُ الإداريّة ومعها الضريبة، قبل أن
            يُسأل الزائرُ أن يدخل. والمسجّلُ يراها داخل صندوق المزايدة
            (`BidBox`)، فهنا لمن لم يدخل وحده — ولا تُكتب مرّتين.
          */}
          {signedIn ? null : (
            <div className="fee-card mt-5 grid grid-cols-2 gap-3 rounded-xl p-4">
              <div>
                <p className="text-caption">الرسوم الإداريّة</p>
                <p className="money tnum text-lg font-bold">{amount(vehicle.admin_fee)} ر.س</p>
              </div>
              <div>
                <p className="text-caption">مع الضريبة (15%)</p>
                <p className="money tnum text-lg font-bold">{amount(vehicle.admin_fee_with_vat)} ر.س</p>
              </div>
            </div>
          )}

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
            <p className="tone-navy mt-8 rounded-2xl border p-4 text-base">
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

//: ‏قيمةٌ تُعرض: لا فراغ ولا «غير محدد» — الخادمُ يكتبها لما لا يعرفه.
function known(value: string | null | undefined): value is string {
  const v = (value ?? "").trim();
  return v !== "" && v !== "—" && v !== "غير محدد";
}

type SpecIcon = "car" | "calendar" | "palette" | "gauge" | "shield" | "pin" | "fuel" | "gear";

const GLYPHS: Record<SpecIcon, React.ReactNode> = {
  car: (
    <>
      <path d="M5 16.5h14M5 16.5V13l1.8-4.2A2 2 0 0 1 8.6 7.5h6.8a2 2 0 0 1 1.8 1.3L19 13v3.5" />
      <circle cx="8" cy="16.5" r="1.6" />
      <circle cx="16" cy="16.5" r="1.6" />
    </>
  ),
  calendar: (
    <>
      <rect x="4" y="5.5" width="16" height="14" rx="2" />
      <path d="M4 10h16M8.5 3.5v4M15.5 3.5v4" />
    </>
  ),
  palette: (
    <>
      <path d="M12 4a8 8 0 1 0 0 16c1.2 0 1.6-.9 1.2-1.8-.5-1-.1-2.2 1.2-2.2H17a3 3 0 0 0 3-3c0-5-3.6-9-8-9Z" />
      <circle cx="8.5" cy="11" r="1" />
      <circle cx="11.5" cy="8" r="1" />
      <circle cx="15" cy="9.5" r="1" />
    </>
  ),
  gauge: (
    <>
      <path d="M4.5 16a7.5 7.5 0 1 1 15 0" />
      <path d="m12 16 3.5-4.5" />
      <circle cx="12" cy="16" r="1.2" />
    </>
  ),
  shield: (
    <>
      <path d="M12 3.5 5 6v5.5c0 4.2 3 7.3 7 8.5 4-1.2 7-4.3 7-8.5V6z" />
      <path d="m9 12 2 2 4-4" />
    </>
  ),
  fuel: (
    <>
      <path d="M6 20V6a2 2 0 0 1 2-2h5a2 2 0 0 1 2 2v14M5 20h11M6 10h9" />
      <path d="M15 8h1.5a1.5 1.5 0 0 1 1.5 1.5V15a1.5 1.5 0 0 0 3 0V8l-2.5-2.5" />
    </>
  ),
  gear: (
    <>
      <circle cx="6" cy="6" r="1.8" />
      <circle cx="12" cy="6" r="1.8" />
      <circle cx="18" cy="6" r="1.8" />
      <circle cx="6" cy="18" r="1.8" />
      <circle cx="12" cy="18" r="1.8" />
      <path d="M6 8v8M12 8v8M18 8v4H6" />
    </>
  ),
  pin: (
    <>
      <path d="M12 20s6-5.6 6-10.5a6 6 0 0 0-12 0C6 14.4 12 20 12 20Z" />
      <circle cx="12" cy="9.5" r="2.2" />
    </>
  ),
};

function SpecGlyph({ name }: { name: SpecIcon }) {
  return (
    <svg
      viewBox="0 0 24 24"
      className="h-5 w-5"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      {GLYPHS[name]}
    </svg>
  );
}
