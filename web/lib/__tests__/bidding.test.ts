/**
 * T1014–T1017 — المزايدة، والقاعدة الحاكمة للفيز مُقاسةً.
 *
 * J7 is the criterion: *عميل غير مؤهَّل يُرفض بنفس السبب المُعدَّد الذي يظهر في
 * التطبيق، **حرفياً***. Two channels giving one customer the same answer is not
 * achieved by being careful twice — it is achieved by there being one place that
 * answers. So the tests here assert two things about every refusal:
 *
 * * the code that reaches the screen is the code the backend sent, unaltered —
 *   `BidRefused.code` is the enumerated reason itself, not a generic "refused",
 *   and that is what makes the two channels comparable at all;
 * * the sentence is the backend's sentence, not one this layer wrote.
 *
 * And the third assertion, which is structural and stronger than either: the
 * guard `ops/checks/web_no_eligibility_logic.mjs` runs here and is proven able
 * to fail. The behavioural tests pass on the day somebody adds a "he has no
 * deposit, hide the box" branch — as long as their branch happens to agree with
 * the server on the cases these tests use. The guard does not.
 */

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

function answer(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

function refusal(code: string, message: string, detail: unknown = {}, status = 409) {
  return answer({ error: { code, message, detail } }, status);
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

function form(values: Record<string, string>): FormData {
  const data = new FormData();
  for (const [key, value] of Object.entries(values)) data.set(key, value);
  return data;
}

function flash(): { code: string; message: string; detail?: Record<string, unknown> } | null {
  const raw = cookieJar.get("haraj_flash")?.value;
  return raw ? JSON.parse(raw) : null;
}

beforeEach(() => {
  cookieJar.clear();
  redirects.length = 0;
  cookieJar.set("haraj_access", { value: "token", options: {} });
});

afterEach(() => {
  vi.unstubAllGlobals();
});

// ---------------------------------------------------------------------------
// T1014 / J7 — the refusal arrives as the server wrote it
// ---------------------------------------------------------------------------

describe("وضع المزايدة", () => {
  it("يرسل المبلغ نصّاً كما كُتب، بلا تحويل إلى عدد", async () => {
    // A decimal that survives a `Number` round trip for most values and not for
    // this one. The ledger is decimal all the way down; the web must not be the
    // one place that is not.
    let body: unknown;
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        body = JSON.parse(await (input as Request).text());
        return answer({ id: 1, amount: "50000.10" }, 201);
      }),
    );

    const { placeBid } = await import("@/features/bidding/actions");
    await run(() => placeBid(form({ vehicle_id: "91", amount: "50000.10" })));

    expect((body as { amount: unknown }).amount).toBe("50000.10");
    expect(typeof (body as { amount: unknown }).amount).toBe("string");
  });

  it("يستدعي نقطة العقد نفسها التي يستدعيها التطبيق", async () => {
    let url = "";
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        url = (input as Request).url;
        return answer({ id: 1 }, 201);
      }),
    );

    const { placeBid } = await import("@/features/bidding/actions");
    await run(() => placeBid(form({ vehicle_id: "91", amount: "50000.00" })));

    expect(url).toContain("/api/v1/vehicles/91/bids/");
  });

  it("يحمل الجلسة من الكوكي، فلا يلمس المتصفح رمزاً", async () => {
    let headers: Headers | undefined;
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        headers = (input as Request).headers;
        return answer({ id: 1 }, 201);
      }),
    );

    const { placeBid } = await import("@/features/bidding/actions");
    await run(() => placeBid(form({ vehicle_id: "91", amount: "1000.00" })));

    expect(headers?.get("authorization")).toBe("Bearer token");
  });
});

describe("J7 — الرفض يصل برمزه وجملته كما هما", () => {
  // The enumerated reasons, with the sentences the backend actually sends. The
  // test does not care what they say; it cares that whatever they say arrives.
  const REFUSALS = [
    ["no_deposit", "تحتاج تأميناً متاحاً قدره 10000.00 ريال."],
    ["unpaid_dues", "عليك مستحقات غير مسدَّدة، سدّدها قبل المزايدة."],
    ["auction_ended", "المزاد انتهى."],
    ["below_floor", "أقل مزايدة مقبولة 20000.00 ريال."],
    ["own_vehicle", "المركبة تخصّك."],
    ["phone_not_verified", "لازم توثّق رقم جوالك قبل المزايدة."],
  ] as const;

  it.each(REFUSALS)("%s", async (code, message) => {
    vi.stubGlobal("fetch", vi.fn(async () => refusal(code, message)));

    const { placeBid } = await import("@/features/bidding/actions");
    await run(() => placeBid(form({ vehicle_id: "91", amount: "1000.00" })));

    const shown = flash();
    expect(shown?.code).toBe(code);
    expect(shown?.message).toBe(message);
  });

  it("لا يبدّل جملة الخادم بجملة محلية", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => refusal("no_deposit", "جملة الخادم بالذات.")),
    );

    const { placeBid } = await import("@/features/bidding/actions");
    await run(() => placeBid(form({ vehicle_id: "91", amount: "1000.00" })));

    expect(flash()?.message).toBe("جملة الخادم بالذات.");
  });
});

// ---------------------------------------------------------------------------
// T1015 — lowering, and the accident it must not become
// ---------------------------------------------------------------------------

describe("الخفض بتأكيد صريح", () => {
  it("المحاولة الأولى لا تحمل التأكيد", async () => {
    // The web does not infer "this looks lower, add the flag". If it did, it
    // would walk straight through the guard F3 exists to be — the two-step is
    // the server's, and this layer only forwards what the customer ticked.
    let body: { confirm_lower?: boolean } = {};
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        body = JSON.parse(await (input as Request).text());
        return refusal(
          "lower_needs_confirm",
          "المبلغ أقل من مزايدتك الحالية. أكّد الخفض إن كنت متأكداً.",
          { standing: "51000.00", requested: "50000.00", bid: 4 },
        );
      }),
    );

    const { placeBid } = await import("@/features/bidding/actions");
    await run(() => placeBid(form({ vehicle_id: "91", amount: "50000.00" })));

    expect(body.confirm_lower).toBe(false);
    expect(flash()?.code).toBe("lower_needs_confirm");
  });

  it("يحمل الرقم القائم من تفصيل الرفض نفسه، لا من قراءة جديدة", async () => {
    // The figure the customer is asked to confirm below has to be the figure the
    // refusal was about. A fresh read a moment later can legitimately be a
    // different one — and then the confirmation is consent to something that was
    // never asked.
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        refusal("lower_needs_confirm", "أكّد الخفض.", {
          standing: "51000.00",
          requested: "50000.00",
        }),
      ),
    );

    const { placeBid } = await import("@/features/bidding/actions");
    await run(() => placeBid(form({ vehicle_id: "91", amount: "50000.00" })));

    expect(flash()?.detail?.standing).toBe("51000.00");
    expect(flash()?.detail?.requested).toBe("50000.00");
  });

  it("التأكيد يمرّ، والثاني وحده يحمل العلم", async () => {
    let body: { confirm_lower?: boolean } = {};
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        body = JSON.parse(await (input as Request).text());
        return answer({ id: 5, amount: "50000.00" }, 201);
      }),
    );

    const { placeBid } = await import("@/features/bidding/actions");
    await run(() =>
      placeBid(form({ vehicle_id: "91", amount: "50000.00", confirm_lower: "1" })),
    );

    expect(body.confirm_lower).toBe(true);
    expect(flash()?.code).toBe("bid_placed");
  });

  it("لا يمرّ صدفةً: قيمة غير «1» ليست تأكيداً", async () => {
    let body: { confirm_lower?: boolean } = {};
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        body = JSON.parse(await (input as Request).text());
        return answer({ id: 5 }, 201);
      }),
    );

    const { placeBid } = await import("@/features/bidding/actions");
    await run(() =>
      placeBid(form({ vehicle_id: "91", amount: "1.00", confirm_lower: "on" })),
    );

    expect(body.confirm_lower).toBe(false);
  });
});

// ---------------------------------------------------------------------------
// T1016 — withdrawal
// ---------------------------------------------------------------------------

describe("سحب المزايدة", () => {
  it("يستدعي نقطة السحب ويعود إلى مزايداتي", async () => {
    let url = "";
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        url = (input as Request).url;
        return answer({ id: 4, is_withdrawn: true });
      }),
    );

    const { withdrawBid } = await import("@/features/bidding/actions");
    const to = await run(() => withdrawBid(form({ bid_id: "4" })));

    expect(url).toContain("/api/v1/bids/4/withdraw/");
    expect(to).toBe("/bids");
  });

  it("رفض الخادم يصل كما هو — الملكية ليست فحصاً في الويب", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => refusal("not_your_bid", "هذه المزايدة ليست مزايدتك.")),
    );

    const { withdrawBid } = await import("@/features/bidding/actions");
    await run(() => withdrawBid(form({ bid_id: "4" })));

    expect(flash()?.code).toBe("not_your_bid");
    expect(flash()?.message).toBe("هذه المزايدة ليست مزايدتك.");
  });
});

// ---------------------------------------------------------------------------
// The structural guarantee — stronger than any of the above
// ---------------------------------------------------------------------------

describe("لا منطق أهلية في الويب", () => {
  it("الشجرة نظيفة", async () => {
    const { violations } = await import(
      "../../../ops/checks/web_no_eligibility_logic.mjs"
    );

    expect(await violations()).toEqual([]);
  });

  it("يمسك قراءة شرط أهلية لو كُتبت", async () => {
    const { mkdtemp, writeFile, rm } = await import("node:fs/promises");
    const { tmpdir } = await import("node:os");
    const { join } = await import("node:path");

    const scratch = await mkdtemp(join(tmpdir(), "haraj-elig-"));
    try {
      await writeFile(
        join(scratch, "leak.ts"),
        "export const may = (m) => m.insurance_free >= m.required_deposit;\n",
        "utf8",
      );

      const { violations } = await import(
        "../../../ops/checks/web_no_eligibility_logic.mjs"
      );
      const found = await violations(scratch);

      expect(found).toHaveLength(1);
      expect(found[0]).toContain("أهلية");
    } finally {
      await rm(scratch, { recursive: true, force: true });
    }
  });

  it("يمسك سبب رفضٍ مكتوباً في شيفرة تُشحن", async () => {
    const { mkdtemp, writeFile, rm } = await import("node:fs/promises");
    const { tmpdir } = await import("node:os");
    const { join } = await import("node:path");

    const scratch = await mkdtemp(join(tmpdir(), "haraj-reason-"));
    try {
      await writeFile(
        join(scratch, "message.ts"),
        'export const label = (c: string) => (c === "no_deposit" ? "زد رصيدك" : "");\n',
        "utf8",
      );

      const { violations } = await import(
        "../../../ops/checks/web_no_eligibility_logic.mjs"
      );

      expect(await violations(scratch)).toHaveLength(1);
    } finally {
      await rm(scratch, { recursive: true, force: true });
    }
  });
});
