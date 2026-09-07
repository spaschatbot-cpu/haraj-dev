/**
 * T1028 — مسار كامل: دخول ← مزايدة ← محفظة.
 *
 * Every other test file in this project takes one screen or one action and holds
 * it to one rule. This one does the opposite: it plays a customer's actual
 * session end to end, in order, through the same server actions and the same
 * server components a browser would reach — and the value is entirely in the
 * *seams*.
 *
 * A unit test proves a step works. It cannot prove that the cookie sign-in wrote
 * is the cookie the bid reads, that the amount typed on one screen is the amount
 * the wallet shows on the next, or that a refusal in the middle leaves the
 * session intact instead of quietly signing somebody out. Every one of those is
 * a seam, and seams are where a system that passes all its tests still fails in
 * front of a person.
 *
 * The backend is stubbed at `fetch` and keeps state between calls, so the
 * sequence is a sequence rather than five independent stubs: a bid placed in
 * step three is why the held balance is what it is in step five.
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

import SignInPage from "@/app/sign-in/page";
import VehiclePage from "@/app/vehicles/[id]/page";
import BidsPage from "@/app/bids/page";
import WalletPage from "@/app/wallet/page";

const VEHICLE = {
  id: 91,
  auction_number: 811,
  auction_state: "live",
  lot_number: 14,
  reference: "#91",
  title: "تويوتا كامري",
  make: "تويوتا",
  model: "كامري",
  year: 2022,
  odometer_km: 84000,
  colour: "silver",
  colour_label: "فضي",
  condition: "good",
  condition_label: "جيدة",
  location: "الرياض / طريق الحائر",
  state: "listed",
  thumbnail_url: null,
};

/**
 * A backend with a memory.
 *
 * It holds the one fact the journey turns on — whether a bid has been placed —
 * and answers every later screen consistently with it. Independent stubs would
 * let the test pass with a wallet that shows a hold for a bid that was never
 * made, which is precisely the kind of agreement this file exists to check.
 */
function backend() {
  const state = { bid: null as null | { id: number; amount: string } };
  const calls: string[] = [];

  const answer = (body: unknown, status = 200) =>
    new Response(JSON.stringify(body), {
      status,
      headers: { "content-type": "application/json" },
    });

  const handler = vi.fn(async (input: RequestInfo | URL) => {
    const requested = input as Request;
    const url = typeof input === "string" ? input : requested.url;
    calls.push(url);

    if (url.includes("/auth/code/")) {
      return answer({ sent: true, expires_at: "2026-09-03T10:05:00Z", resend_after: 60 });
    }
    if (url.includes("/auth/verify/")) {
      return answer({
        access: "session-token",
        refresh: "session-refresh",
        expires_in: 3600,
        expires_at: "2026-09-03T11:00:00Z",
      });
    }
    if (url.includes("/bids/") && url.includes("/vehicles/")) {
      const body = JSON.parse(await requested.text()) as { amount: string };
      state.bid = { id: 5, amount: body.amount };
      return answer({ id: 5, amount: body.amount }, 201);
    }
    if (url.includes("/bids/mine/")) {
      return answer({
        total: state.bid ? 1 : 0,
        results: state.bid
          ? [
              {
                id: state.bid.id,
                vehicle_id: 91,
                auction_id: 7,
                lot_number: 14,
                vehicle_title: VEHICLE.title,
                amount: state.bid.amount,
                placed_at: "2026-09-03T10:10:00Z",
                is_withdrawn: false,
                is_superseded: false,
              },
            ]
          : [],
      });
    }
    if (url.includes("/wallet/")) {
      // The deposit is held the moment a bid is placed (T505): one hold per
      // customer and auction, moved by the bid and by nothing on this side.
      const held = state.bid ? "10000.00" : "0.00";
      const available = state.bid ? "15000.00" : "25000.00";
      return answer({
        currency: "SAR",
        total: "25000.00",
        available,
        held_for_auctions: held,
        locked_for_dues: "0.00",
        buckets: [
          {
            kind: "insurance_free",
            label: "تأمين متاح",
            amount: available,
            entry_count: 1,
            statement: "x",
          },
          {
            kind: "insurance_held",
            label: "تأمين محجوز لمزاد",
            amount: held,
            entry_count: state.bid ? 1 : 0,
            statement: "x",
          },
        ],
        holds: state.bid
          ? [
              {
                id: 3,
                amount: held,
                reason: "bidding",
                reason_label: "ضمان المزايدة",
                auction: { id: 7, number: 811 },
                invoice: null,
                created_at: "2026-09-03T10:10:00Z",
              },
            ]
          : [],
        as_of: "2026-09-03T10:11:00Z",
      });
    }
    if (url.includes("/vehicles/")) return answer(VEHICLE);

    return answer({ error: { code: "not_found", message: "غير موجود.", detail: {} } }, 404);
  });

  return { handler, state, calls };
}

async function run(action: () => Promise<void>): Promise<string> {
  const before = redirects.length;
  await action().catch((error: unknown) => {
    if (!(error instanceof Error) || !error.message.startsWith("NEXT_REDIRECT")) {
      throw error;
    }
  });
  return redirects[before] ?? "";
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
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("مسار عميل كامل", () => {
  it("دخول ← مزايدة ← مزايداتي ← محفظة", async () => {
    const api = backend();
    vi.stubGlobal("fetch", api.handler);

    const { sendCode, verifyCode } = await import("@/features/auth/actions");
    const { placeBid } = await import("@/features/bidding/actions");

    // ---- 1. a visitor who is not signed in is told what to do, not refused --
    const anonymous = await render(
      VehiclePage({ params: Promise.resolve({ id: "91" }) }),
    );
    expect(anonymous).toContain("سجّل دخولك");
    expect(anonymous).toContain("تويوتا كامري");

    // ---- 2. sign in ------------------------------------------------------
    await run(() => sendCode(form({ phone: "966500000001" })));
    const afterVerify = await run(() =>
      verifyCode(form({ phone: "966500000001", code: "123456" })),
    );
    expect(afterVerify).toBe("/account");

    // The seam: the session the sign-in wrote is a cookie, not a value held in
    // memory by the module that wrote it.
    expect(cookieJar.get("haraj_access")?.value).toBe("session-token");
    expect(cookieJar.get("haraj_access")?.options.httpOnly).toBe(true);

    // ---- 3. the same vehicle page now offers the box ----------------------
    const signedIn = await render(VehiclePage({ params: Promise.resolve({ id: "91" }) }));
    expect(signedIn).toContain("زايد");
    expect(signedIn).not.toContain("سجّل دخولك");

    // ---- 4. bid ----------------------------------------------------------
    const afterBid = await run(() =>
      placeBid(form({ vehicle_id: "91", amount: "50000.25" })),
    );
    expect(afterBid).toBe("/vehicles/91");
    expect(api.state.bid?.amount).toBe("50000.25");

    // The bid carried the session, and it carried it from the cookie.
    const bidCall = api.handler.mock.calls.find(([input]) =>
      (input as Request).url?.includes("/bids/"),
    );
    expect((bidCall?.[0] as Request).headers.get("authorization")).toBe(
      "Bearer session-token",
    );

    // ---- 5. مزايداتي shows the amount that was typed, unchanged ----------
    const bids = await render(BidsPage({ searchParams: Promise.resolve({}) }));
    expect(bids).toContain("50000.25");
    expect(bids).toContain("قائمة");
    expect(bids).toContain("تويوتا كامري");

    // ---- 6. and the wallet shows the deposit the bid moved ---------------
    const wallet = await render(WalletPage());
    expect(wallet).toContain("10000.00");
    expect(wallet).toContain("ضمان المزايدة");
    expect(wallet).toContain("811");
  });

  it("رفضٌ في المنتصف لا يُخرج العميل من جلسته", async () => {
    // The seam that breaks quietly: an error handler that clears the session
    // "to be safe" turns a refused bid into a sign-out, and the customer's next
    // click is a login screen with no explanation of what happened.
    const api = backend();
    vi.stubGlobal("fetch", api.handler);

    const { verifyCode } = await import("@/features/auth/actions");
    await run(() => verifyCode(form({ phone: "966500000001", code: "123456" })));

    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        new Response(
          JSON.stringify({
            error: {
              code: "no_deposit",
              message: "تحتاج تأميناً متاحاً قدره 10000.00 ريال.",
              detail: {},
            },
          }),
          { status: 409, headers: { "content-type": "application/json" } },
        ),
      ),
    );

    const { placeBid } = await import("@/features/bidding/actions");
    const to = await run(() => placeBid(form({ vehicle_id: "91", amount: "1.00" })));

    expect(to).toBe("/vehicles/91");
    expect(cookieJar.get("haraj_access")?.value).toBe("session-token");

    const flash = JSON.parse(cookieJar.get("haraj_flash")?.value ?? "{}") as {
      message?: string;
    };
    expect(flash.message).toBe("تحتاج تأميناً متاحاً قدره 10000.00 ريال.");
  });

  it("الخروج يقطع المسار: الصفحات المحمية تعود إلى الدخول", async () => {
    const api = backend();
    vi.stubGlobal("fetch", api.handler);

    const { verifyCode, signOut } = await import("@/features/auth/actions");
    await run(() => verifyCode(form({ phone: "966500000001", code: "123456" })));
    await run(() => signOut());

    // Not "renders an empty wallet" — redirects. A protected page that renders
    // for a signed-out visitor is a page that will eventually render somebody
    // else's numbers.
    await expect(render(WalletPage())).rejects.toThrow("NEXT_REDIRECT:/sign-in");
    await expect(
      render(BidsPage({ searchParams: Promise.resolve({}) })),
    ).rejects.toThrow("NEXT_REDIRECT:/sign-in");
  });

  it("الدخول وأنت داخلٌ يمضي بك، لا يعيد سؤالك", async () => {
    const api = backend();
    vi.stubGlobal("fetch", api.handler);

    const { verifyCode } = await import("@/features/auth/actions");
    await run(() => verifyCode(form({ phone: "966500000001", code: "123456" })));

    await expect(
      render(SignInPage({ searchParams: Promise.resolve({}) })),
    ).rejects.toThrow("NEXT_REDIRECT:/account");
  });
});
