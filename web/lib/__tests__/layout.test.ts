/**
 * T1027 — ما يمكن إثباته بلا متصفح عن الثلاثة مقاسات.
 *
 * The task asks for snapshots of every main screen at phone, tablet and desktop
 * widths. **Half of that needs a browser and this file does not pretend
 * otherwise** — a media query is applied by a layout engine, and no amount of
 * string rendering exercises one. Rendering the same markup three times and
 * saving three identical files would be a green test that proves nothing, which
 * is worse than an honest gap.
 *
 * What *is* provable from the server's own output, and is worth proving:
 *
 * 1. **the markup is stable** — a snapshot per screen, so a refactor that
 *    silently drops a section is a diff somebody reads rather than a page
 *    somebody notices later;
 * 2. **the direction is on the document** — RTL is set once, on `<html>`, and
 *    every layout below is written without a direction-aware rule of its own
 *    (T1003). A screen that grew its own `dir` would be the beginning of the
 *    retrofit that task exists to prevent;
 * 3. **no fixed pixel width** — the one authoring mistake that reliably breaks
 *    a phone. A `w-[420px]` renders identically in a string test and produces a
 *    horizontal scrollbar on every phone in Saudi Arabia;
 * 4. **the grids declare their breakpoints** — the responsive classes are in the
 *    markup, so what a browser would apply is at least present to be applied.
 *
 * The remaining half — that the result actually *looks* right at 375, 768 and
 * 1280 — is `T1027`'s open item, and needs Playwright and a running server.
 */

import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { readdir, readFile } from "node:fs/promises";
import { join } from "node:path";

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

function answer(body: unknown) {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { "content-type": "application/json" },
  });
}

beforeEach(() => {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL) => {
      const url = typeof input === "string" ? input : (input as Request).url;
      if (url.includes("/vehicles/") && url.includes("/auctions/")) {
        return answer({ total: 1, results: [VEHICLE] });
      }
      if (/\/auctions\/\d+\//.test(url)) return answer(AUCTION);
      if (url.includes("/auctions/")) return answer({ total: 1, results: [AUCTION] });
      return answer(VEHICLE);
    }),
  );
});

afterEach(() => {
  vi.unstubAllGlobals();
});

async function render(element: Promise<React.ReactElement>) {
  return renderToStaticMarkup(await element);
}

// ---------------------------------------------------------------------------
// 1. Stable markup
// ---------------------------------------------------------------------------

describe("لقطات البنية", () => {
  it("قائمة المزادات", async () => {
    expect(await render(AuctionsPage({ searchParams: Promise.resolve({}) }))).toMatchSnapshot();
  });

  it("مركبات المزاد", async () => {
    expect(
      await render(
        AuctionPage({
          params: Promise.resolve({ id: "7" }),
          searchParams: Promise.resolve({}),
        }),
      ),
    ).toMatchSnapshot();
  });

  it("صفحة المركبة", async () => {
    expect(
      await render(VehiclePage({ params: Promise.resolve({ id: "91" }) })),
    ).toMatchSnapshot();
  });
});

// ---------------------------------------------------------------------------
// 2. The direction is on the document, once
// ---------------------------------------------------------------------------

describe("العربية وRTL", () => {
  it("‏`lang` و`dir` على الوثيقة", async () => {
    // On `<html>`, not on a wrapper inside it: Tailwind's logical properties,
    // the browser's caret and selection behaviour and a screen reader's
    // pronunciation all read the direction from there.
    //
    // Read as source rather than rendered. `app/layout.tsx` imports
    // `next/font/google`, which is a build-time transform and not a function
    // outside Next's pipeline — so rendering it here would test a mock of the
    // font loader, and the attribute is what is under test.
    const source = await readFile(join("app", "layout.tsx"), "utf8");

    expect(source).toMatch(/<html[^>]*lang="ar"/);
    expect(source).toMatch(/<html[^>]*dir="rtl"/);
  });

  it("ولا صفحة تعلن اتجاهها بنفسها", async () => {
    // A screen that grew its own `dir` is the beginning of the retrofit T1003
    // exists to prevent — and the second one would disagree with the first.
    const offenders: string[] = [];

    async function* walk(directory: string): AsyncGenerator<string> {
      for (const entry of await readdir(directory, { withFileTypes: true })) {
        if (entry.name === "node_modules" || entry.name === ".next") continue;
        const path = join(directory, entry.name);
        if (entry.isDirectory()) yield* walk(path);
        else if (entry.name.endsWith(".tsx")) yield path;
      }
    }

    for await (const path of walk("app")) {
      if (path.endsWith(join("app", "layout.tsx"))) continue;
      const source = await readFile(path, "utf8");
      if (/\bdir\s*=\s*["'{]/.test(source)) offenders.push(path);
    }
    for await (const path of walk("features")) {
      const source = await readFile(path, "utf8");
      if (/\bdir\s*=\s*["'{]/.test(source)) offenders.push(path);
    }

    expect(offenders).toEqual([]);
  });
});

// ---------------------------------------------------------------------------
// 3 & 4. What makes three sizes possible
// ---------------------------------------------------------------------------

describe("الثلاثة مقاسات — ما يمكن إثباته بلا متصفح", () => {
  it("لا عرض ثابت بالبكسل في أي شاشة", async () => {
    // The one authoring mistake that reliably breaks a phone. It renders
    // identically in a string test and produces a horizontal scrollbar on every
    // phone — which is exactly why a text check earns its place here.
    const offenders: string[] = [];

    async function* walk(directory: string): AsyncGenerator<string> {
      for (const entry of await readdir(directory, { withFileTypes: true })) {
        if (entry.name === "node_modules" || entry.name === ".next") continue;
        const path = join(directory, entry.name);
        if (entry.isDirectory()) yield* walk(path);
        else if (entry.name.endsWith(".tsx") || entry.name.endsWith(".css")) yield path;
      }
    }

    for (const root of ["app", "features"]) {
      for await (const path of walk(root)) {
        const source = await readFile(path, "utf8");
        // `w-[420px]`, `width: 420px`, `min-width: 900px` — a fixed floor wider
        // than a phone. `max-width` is fine and is how the layouts are written.
        if (/\bw-\[\d{3,}px\]|(?<!max-)\bmin-width:\s*\d{3,}px|(?<!max-)\bwidth:\s*\d{3,}px/.test(source)) {
          offenders.push(path);
        }
      }
    }

    expect(offenders).toEqual([]);
  });

  it("الشبكات تعلن نقاط انكسارها", async () => {
    // What a browser would apply is at least present to be applied. One column
    // on a phone, more as the screen grows.
    const list = await render(AuctionsPage({ searchParams: Promise.resolve({}) }));
    const vehicles = await render(
      AuctionPage({
        params: Promise.resolve({ id: "7" }),
        searchParams: Promise.resolve({}),
      }),
    );

    expect(list).toMatch(/sm:grid-cols-\d/);
    expect(vehicles).toMatch(/sm:grid-cols-\d/);
    expect(vehicles).toMatch(/lg:grid-cols-\d/);
  });

  it("الجداول العريضة تمرّر أفقياً داخل نفسها", async () => {
    // A statement table on a phone either scrolls inside its own container or
    // makes the whole page scroll sideways. The second is how a page stops
    // being readable at all.
    const source = await readFile(join("app", "wallet", "statement", "page.tsx"), "utf8");

    expect(source).toContain("overflow-x-auto");
  });
});
