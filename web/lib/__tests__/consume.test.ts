/**
 * T1013 · T1018 · T1021 — استهلاك ما أضافه العقد، وما يجب ألّا يُستهلك.
 *
 * Three screens, and each is tested against the one thing it could get wrong:
 *
 * * **المفضّلة** — the heart must show what is *stored*, not what was clicked. An
 *   optimistic toggle shows a filled heart for a request that failed, and the
 *   customer finds the car missing later with no idea when it went.
 * * **الشحن** — the client must not learn which gateway is configured, and must
 *   not invent a destination when the server offers none.
 * * **التحديث الحي** — no rival's number, in any shape. The stream cannot send
 *   one (`apps/bidding/live.py` is tested for that directly), and this file
 *   checks the *other* half: the page renders the caller's own standing bid on
 *   the server, so a visitor whose script never runs still sees a true number
 *   rather than an empty box.
 */

import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const cookieJar = new Map<string, { value: string; options: Record<string, unknown> }>();
const redirects: string[] = [];

vi.mock("next/headers", () => ({
  cookies: async () => ({
    get: (name: string) => {
      const written = cookieJar.get(name);
      return written ? { name, value: written.value } : undefined;
    },
    set: (name: string, value: string, options: Record<string, unknown>) => {
      cookieJar.set(name, { value, options });
    },
    delete: (name: string) => {
      cookieJar.delete(name);
    },
  }),
}));

vi.mock("next/navigation", () => ({
  redirect: (to: string) => {
    redirects.push(to);
    throw new Error(`NEXT_REDIRECT:${to}`);
  },
  notFound: () => {
    throw new Error("NEXT_NOT_FOUND");
  },
}));

//: `revalidatePath` needs Next's request store, which no unit test has. What
//: matters here is *which endpoint the action called*, and the revalidation is
//: Next's own job.
const revalidated: string[] = [];
vi.mock("next/cache", () => ({
  revalidatePath: (path: string) => {
    revalidated.push(path);
  },
}));

import VehiclePage from "@/app/vehicles/[id]/page";
import FavouritesPage from "@/app/favourites/page";

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

const MY_BID = {
  id: 5,
  vehicle_id: 91,
  auction_id: 7,
  lot_number: 14,
  vehicle_title: VEHICLE.title,
  amount: "50000.25",
  placed_at: "2026-09-03T10:00:00Z",
  is_withdrawn: false,
  is_superseded: false,
};

function answer(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

/** A backend that answers each of the three surfaces the pages read. */
function backend(options: { favourites?: unknown[]; bids?: unknown[] } = {}) {
  const calls: Array<{ url: string; method: string }> = [];

  const handler = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const requested = input as Request;
    const url = typeof input === "string" ? input : requested.url;
    calls.push({ url, method: requested.method ?? init?.method ?? "GET" });

    if (url.includes("/favourites/")) {
      return answer({ total: (options.favourites ?? []).length, results: options.favourites ?? [] });
    }
    if (url.includes("/bids/mine/")) {
      return answer({ total: (options.bids ?? []).length, results: options.bids ?? [] });
    }
    return answer(VEHICLE);
  });

  return { handler, calls };
}

async function render(element: Promise<React.ReactElement>) {
  return renderToStaticMarkup(await element);
}

function form(values: Record<string, string>): FormData {
  const data = new FormData();
  for (const [key, value] of Object.entries(values)) data.set(key, value);
  return data;
}

beforeEach(() => {
  cookieJar.clear();
  redirects.length = 0;
  revalidated.length = 0;
  cookieJar.set("haraj_access", { value: "token", options: {} });
});

afterEach(() => {
  vi.unstubAllGlobals();
});

// ---------------------------------------------------------------------------
// T1013 — the heart shows what is stored
// ---------------------------------------------------------------------------

describe("المفضّلة", () => {
  it("القلب ممتلئ لأن الخادم قال إنها محفوظة", async () => {
    const api = backend({ favourites: [VEHICLE] });
    vi.stubGlobal("fetch", api.handler);

    const html = await render(VehiclePage({ params: Promise.resolve({ id: "91" }) }));

    expect(html).toContain("في المفضّلة");
    expect(html).not.toContain("أضف للمفضّلة");
  });

  it("وفارغ لأنه قال إنها ليست", async () => {
    const api = backend({ favourites: [] });
    vi.stubGlobal("fetch", api.handler);

    const html = await render(VehiclePage({ params: Promise.resolve({ id: "91" }) }));

    expect(html).toContain("أضف للمفضّلة");
  });

  it("الإضافة PUT والإزالة DELETE على نقطة العقد", async () => {
    const api = backend();
    vi.stubGlobal("fetch", api.handler);

    const { addFavourite, removeFavourite } = await import(
      "@/features/favourites/actions"
    );

    await addFavourite(form({ vehicle_id: "91", back: "/vehicles/91" }));
    await removeFavourite(form({ vehicle_id: "91", back: "/vehicles/91" }));

    const writes = api.calls.filter((call) => call.url.includes("/favourites/91/"));
    expect(writes.map((call) => call.method)).toEqual(["PUT", "DELETE"]);
  });

  it("وتُحدَّث صفحة المفضّلة أيضاً، لا الصفحة الحالية وحدها", async () => {
    // Marking from a vehicle page must not leave a stale «مفضّلتي» behind it.
    vi.stubGlobal("fetch", backend().handler);

    const { addFavourite } = await import("@/features/favourites/actions");
    await addFavourite(form({ vehicle_id: "91", back: "/vehicles/91" }));

    expect(revalidated).toContain("/vehicles/91");
    expect(revalidated).toContain("/favourites");
  });

  it("قائمة فارغة تقول ماذا يفعل، لا «لا نتائج»", async () => {
    vi.stubGlobal("fetch", backend({ favourites: [] }).handler);

    const html = await render(FavouritesPage({ searchParams: Promise.resolve({}) }));

    expect(html).toContain("لم تحفظ مركبة بعد");
  });

  it("زائرٌ بلا جلسة لا يُعرض له قلب أصلاً", async () => {
    cookieJar.clear();
    vi.stubGlobal("fetch", backend().handler);

    const html = await render(VehiclePage({ params: Promise.resolve({ id: "91" }) }));

    expect(html).not.toContain("أضف للمفضّلة");
    expect(html).toContain("سجّل دخولك");
  });

  it("فشل قراءة المفضّلة لا يُسقط صفحة المركبة", async () => {
    // The car, its price and its specification are what this page is for. A
    // hollow heart is a smaller loss than a 500 on a page arriving from a
    // search result.
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        const url = typeof input === "string" ? input : (input as Request).url;
        if (url.includes("/favourites/")) return answer({}, 500);
        if (url.includes("/bids/mine/")) return answer({ total: 0, results: [] });
        return answer(VEHICLE);
      }),
    );

    const html = await render(VehiclePage({ params: Promise.resolve({ id: "91" }) }));

    expect(html).toContain("تويوتا كامري 2022");
    expect(html).toContain("48500.75");
  });
});

// ---------------------------------------------------------------------------
// T1021 — the hand-off, and what the client is not told
// ---------------------------------------------------------------------------

describe("الشحن بالبطاقة", () => {
  const INTENT = {
    reference: "TOP-42",
    checkout_url: "http://testserver/api/v1/wallet/topups/TOP-42/checkout/",
    amount: "10000.00",
    currency: "SAR",
    purpose: "insurance_deposit",
    purpose_label: "إيداع تأمين",
    state: "pending",
    state_label: "بانتظار الدفع",
    gateway: "moyasar",
    gateway_status_raw: "",
    created_at: "2026-09-03T09:00:00Z",
    updated_at: "2026-09-03T09:00:00Z",
  };

  async function run(action: () => Promise<void>): Promise<string> {
    const before = redirects.length;
    await action().catch((error: unknown) => {
      if (!(error instanceof Error) || !error.message.startsWith("NEXT_REDIRECT")) {
        throw error;
      }
    });
    return redirects[before] ?? "";
  }

  it("يتبع العنوان الذي أعطاه الخادم", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => answer(INTENT, 201)));

    const { startTopup } = await import("@/features/wallet/actions");
    const to = await run(() => startTopup(new FormData()));

    expect(to).toBe(INTENT.checkout_url);
  });

  it("ولا يعرف أي بوابة هي", async () => {
    // The whole point of a url on our own server: switching gateway changes
    // `apps/money/gateway.py` and rebuilds nothing here.
    vi.stubGlobal("fetch", vi.fn(async () => answer(INTENT, 201)));

    const { startTopup } = await import("@/features/wallet/actions");
    const to = await run(() => startTopup(new FormData()));

    expect(to).not.toContain("moyasar");
    expect(to).toContain("/wallet/topups/");
  });

  it("وبلا عنوان يذهب إلى حالة العملية، ولا يخترع وجهة", async () => {
    // An empty `checkout_url` means the environment has no gateway, or the
    // intent can no longer be paid. The status page says which, in the server's
    // own words.
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => answer({ ...INTENT, checkout_url: "" }, 201)),
    );

    const { startTopup } = await import("@/features/wallet/actions");
    const to = await run(() => startTopup(new FormData()));

    expect(to).toBe("/wallet/topup/TOP-42");
  });
});

// ---------------------------------------------------------------------------
// T1018 — the server renders a true number, and no rival's
// ---------------------------------------------------------------------------

describe("التحديث الحي", () => {
  it("مزايدة المتصل مرندَرة في الخادم، فمن لا يعمل سكربته يرى رقماً صحيحاً", async () => {
    vi.stubGlobal("fetch", backend({ bids: [MY_BID] }).handler);

    const html = await render(VehiclePage({ params: Promise.resolve({ id: "91" }) }));

    expect(html).toContain("50000.25");
    expect(html).toContain("مزايدتك القائمة");
  });

  it("وحالة الاتصال معروضة، فلا يبدو رقمٌ قديم حيّاً", async () => {
    // The task's own sentence: «رقم مزايدة قديم يبدو حياً أسوأ من لا رقم».
    vi.stubGlobal("fetch", backend({ bids: [MY_BID] }).handler);

    const html = await render(VehiclePage({ params: Promise.resolve({ id: "91" }) }));

    expect(html).toContain("جارٍ الاتصال");
  });

  it("ولا حقل عن مزايدات غيره في أي مكان", async () => {
    // The stream cannot send one — `apps/bidding/live.py` is tested for that
    // directly. This is the other half: the page does not ask for one either.
    vi.stubGlobal("fetch", backend({ bids: [MY_BID] }).handler);

    const html = await render(VehiclePage({ params: Promise.resolve({ id: "91" }) }));

    for (const leak of ["أعلى مزايدة", "الأعلى", "عدد المزايدين", "منافس"]) {
      expect(html).not.toContain(leak);
    }
  });

  it("بلا مزايدة، يقول ذلك بدل أن يترك فراغاً", async () => {
    vi.stubGlobal("fetch", backend({ bids: [] }).handler);

    const html = await render(VehiclePage({ params: Promise.resolve({ id: "91" }) }));

    expect(html).toContain("لا مزايدة قائمة لك");
  });
});
