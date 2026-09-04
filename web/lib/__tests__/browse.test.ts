/**
 * T1008–T1010 — التصفّح: ما يصل في الـHTML، وما لا يُحسب في الويب أبداً.
 * وقائمة المزادات T1007 أُحيلت إلى الجذر (لا قائمة للعميل)، فاختبارها هنا
 * تحويلٌ لا رندرة.
 *
 * The acceptance criteria here are all about the *server-rendered* output, so
 * the pages are rendered the way a visitor without JavaScript gets them — the
 * server component is called and its React tree is turned into a string — and
 * the assertions are about what is in that string.
 *
 * `renderToStaticMarkup` deliberately: it produces exactly the markup with no
 * hydration data attached, which is the closest thing in a unit test to
 * `curl`ing the route. A test that asserted on a client-rendered tree would
 * prove the opposite of what J5 asks.
 *
 * The API is stubbed at `fetch`, not at our client. What is under test includes
 * *which request the page makes* — the filters have to reach the backend rather
 * than be applied here (T1008) — and stubbing our own client would hide that.
 */

import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

/*
  The vehicle page reads the session cookie (to decide whether to offer the bid
  box) and can call `notFound()`. Both are Next request-scoped APIs with no
  meaning outside a request, so they are stood in for here — a signed-out
  visitor, which is what a crawler and a first-time reader are, and which is the
  audience every assertion in this file is about.
*/
vi.mock("next/headers", () => ({
  cookies: async () => ({
    get: () => undefined,
    set: () => {},
    delete: () => {},
  }),
}));

vi.mock("next/navigation", () => ({
  notFound: () => {
    throw new Error("NEXT_NOT_FOUND");
  },
  redirect: (to: string) => {
    throw new Error(`NEXT_REDIRECT:${to}`);
  },
}));

import AuctionsPage from "@/app/auctions/page";
import AuctionPage from "@/app/auctions/[id]/page";
import VehiclePage from "@/app/vehicles/[id]/page";
import { generateMetadata as vehicleMetadata } from "@/app/vehicles/[id]/page";

const AUCTION = {
  id: 7,
  number: 811,
  title: "مزاد الرياض الأسبوعي",
  state: "live",
  state_label: "جارٍ",
  starts_at: "2026-09-03T08:00:00Z",
  ends_at: "2026-09-03T16:00:00Z",
  vehicle_count: 40,
  open_vehicle_count: 12,
};

const VEHICLE = {
  id: 91,
  auction_number: 811,
  auction_state: "live",
  lot_number: 14,
  title: "تويوتا كامري 2022",
  make: "تويوتا",
  model: "كامري",
  year: 2022,
  odometer_km: 84000,
  transmission: "automatic",
  transmission_label: "أوتوماتيك",
  fuel_type: "petrol",
  fuel_type_label: "بنزين",
  condition: "good",
  condition_label: "جيدة",
  plate_type: "private",
  plate_type_label: "خصوصي",
  reserve_price: "48500.75",
  state: "listed",
  state_label: "معروضة",
  listing_state: "open",
  owner_company_name: "شركة المعارض",
  thumbnail_url: null,
};

/** Every url the page asked for, so a test can assert on the request itself. */
let asked: string[] = [];

function answer(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

beforeEach(() => {
  asked = [];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL) => {
      // `Request.toString()` is "[object Request]", not the url — and
      // openapi-fetch hands `fetch` a Request. Reading `.url` is the difference
      // between a stub that answers and one that silently 404s everything.
      const url =
        typeof input === "string"
          ? input
          : input instanceof URL
            ? input.href
            : input.url;
      asked.push(url);

      if (url.includes("/api/v1/auctions/") && url.includes("/vehicles/")) {
        return answer({ total: 1, results: [VEHICLE] });
      }
      if (/\/api\/v1\/auctions\/\d+\/(\?|$)/.test(url)) return answer(AUCTION);
      if (url.includes("/api/v1/auctions/")) {
        return answer({ total: 1, results: [AUCTION] });
      }
      if (url.includes("/api/v1/vehicles/")) return answer(VEHICLE);

      return answer({ error: { code: "not_found", message: "غير موجود.", detail: {} } }, 404);
    }),
  );
});

afterEach(() => {
  vi.unstubAllGlobals();
});

async function render(element: Promise<React.ReactElement> | React.ReactElement) {
  return renderToStaticMarkup(await element);
}

const noParams = Promise.resolve({});

// ---------------------------------------------------------------------------
// `/auctions` تحوِّل إلى الجذر — لا قائمة مزادات للعميل
// ---------------------------------------------------------------------------

describe("قائمة المزادات المحالة", () => {
  it("تحوِّل إلى الجذر بدل رندرة قائمة", () => {
    // المزاد أسبوعي واحد بحالات، فلا قائمة يختار منها العميل: رابط قديم
    // مشارَك أو مفهرَس يهبط على المزادات لا على 404.
    expect(() => AuctionsPage()).toThrow("NEXT_REDIRECT:/");
  });

  it("لا تسأل الخادم عن شيء قبل التحويل", () => {
    expect(() => AuctionsPage()).toThrow("NEXT_REDIRECT:/");

    expect(asked).toHaveLength(0);
  });
});

// ---------------------------------------------------------------------------
// T1008 — filtering happens on the server
// ---------------------------------------------------------------------------

describe("ترشيح مركبات المزاد", () => {
  const params = Promise.resolve({ id: "7" });

  it("النموذج GET، فيعمل بلا جافاسكربت", async () => {
    const html = await render(AuctionPage({ params, searchParams: noParams }));

    expect(html).toContain('method="get"');
    expect(html).toContain('action="/auctions/7"');
    expect(html).toContain('name="search"');
    expect(html).toContain('name="year_from"');
  });

  it("يمرّر المعايير إلى الخادم بدل ترشيحها في المتصفح", async () => {
    // The second half of the criterion: for one set of criteria the app and the
    // web return the same cars, because there is one implementation of "which
    // cars match" and neither channel has a copy of it.
    await render(
      AuctionPage({
        params,
        searchParams: Promise.resolve({ search: "كامري", year_from: "2020" }),
      }),
    );

    const vehiclesCall = asked.find((url) => url.includes("/vehicles/"));
    expect(vehiclesCall).toBeDefined();
    expect(decodeURIComponent(vehiclesCall!)).toContain("search=كامري");
    expect(vehiclesCall).toContain("year_from=2020");
  });

  it("يتجاهل معاملاً لا يعرفه العقد بدل تمريره ليُرفَض", async () => {
    await render(
      AuctionPage({ params, searchParams: Promise.resolve({ nonsense: "x" }) }),
    );

    const vehiclesCall = asked.find((url) => url.includes("/vehicles/"));
    expect(vehiclesCall).not.toContain("nonsense");
  });

  it("يحتفظ بالترشيح عبر صفحات النتائج", async () => {
    // A filter lost on page two is a filter people stop using. Needs more
    // results than a page holds, or there is no next link to carry it.
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        const url = typeof input === "string" ? input : (input as Request).url;
        if (url.includes("/vehicles/")) return answer({ total: 40, results: [VEHICLE] });
        return answer(AUCTION);
      }),
    );

    const html = await render(
      AuctionPage({
        params,
        searchParams: Promise.resolve({ search: "كامري" }),
      }),
    );

    expect(html).toContain("search=");
    expect(html).toContain("offset=12");
  });
});

// ---------------------------------------------------------------------------
// T1009 / J5 — the vehicle page, in the HTML
// ---------------------------------------------------------------------------

describe("صفحة المركبة", () => {
  const params = Promise.resolve({ id: "91" });

  it("J5 — الاسم والسعر في الـHTML بلا جافاسكربت", async () => {
    const html = await render(VehiclePage({ params }));

    expect(html).toContain("تويوتا كامري 2022");
    expect(html).toContain("48500.75");
  });

  it("السعر كما وصل بالضبط — بلا تقريب ولا فاصل آلاف", async () => {
    // Article 3-2 at the last possible moment. A separator inserted here is a
    // display transformation a customer has to undo in their head before they
    // can compare this page with an invoice.
    const html = await render(VehiclePage({ params }));

    expect(html).toContain("48500.75");
    expect(html).not.toContain("48,500");
    expect(html).not.toContain("48500.8");
  });

  it("بيانات وصفية حقيقية، لا العنوان مكرَّراً", async () => {
    const metadata = await vehicleMetadata({ params });

    expect(metadata.title).toBe("تويوتا كامري 2022");
    expect(metadata.description).toContain("84,000 كم");
    expect(metadata.description).toContain("أوتوماتيك");
  });

  it("بيانات منظَّمة للمركبة، بلا سعر معروض", async () => {
    // An auction lot is not an item at a fixed price. Marking the reserve as an
    // `offers` price is a claim that is wrong the moment bidding starts.
    const html = await render(VehiclePage({ params }));

    expect(html).toContain('type="application/ld+json"');
    expect(html).toContain('\\"@type\\":\\"Vehicle\\"'.replace(/\\/g, ""));
    expect(html).not.toContain('"offers"');
  });

  it("لا يعرض صفر لمركبة بلا سعر وقوف", async () => {
    // A car whose owner set no floor is a different thing from a car whose
    // floor is zero, and printing a number for the first is a number nobody
    // chose.
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => answer({ ...VEHICLE, reserve_price: null })),
    );

    const html = await render(VehiclePage({ params }));

    expect(html).toContain("لم يُحدَّد");
    expect(html).not.toContain("0.00");
  });
});

// ---------------------------------------------------------------------------
// T1010 and the money rule — the guards, run and proven able to fail
// ---------------------------------------------------------------------------

describe("الحرّاس", () => {
  it("لا رسم لكرت مركبة خارج المكوَّن", async () => {
    const { violations } = await import("../../../ops/checks/web_one_vehicle_card.mjs");

    expect(await violations()).toEqual([]);
  });

  it("يمسك كرتاً ثانياً لو كُتب", async () => {
    const { mkdtemp, writeFile, rm } = await import("node:fs/promises");
    const { tmpdir } = await import("node:os");
    const { join } = await import("node:path");

    const scratch = await mkdtemp(join(tmpdir(), "haraj-card-"));
    try {
      await writeFile(
        join(scratch, "SecondCard.tsx"),
        "export const C = (v) => `${v.thumbnail_url} ${v.reserve_price} ${v.lot_number}`;\n",
        "utf8",
      );

      const { violations } = await import(
        "../../../ops/checks/web_one_vehicle_card.mjs"
      );
      expect(await violations(scratch)).toHaveLength(1);
    } finally {
      await rm(scratch, { recursive: true, force: true });
    }
  });

  it("لا حساب على مبلغ في الويب", async () => {
    const { violations } = await import(
      "../../../ops/checks/web_money_is_never_computed.mjs"
    );

    expect(await violations()).toEqual([]);
  });
});
