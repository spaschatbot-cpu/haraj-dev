/**
 * T1019–T1024 — المحفظة والمال، وثلاثة أشياء لا يفعلها الويب.
 *
 * The criteria in this group are all negative — the value is in what is
 * *absent* — so the tests are written to catch the tempting addition rather than
 * to confirm the rendering:
 *
 * * **G5** — the total matches the ledger, which it does by being the server's
 *   field. A sum computed in the browser is a second derivation, and a second
 *   derivation can be right on the day the first is wrong;
 * * **T1021** — tampering with the return parameters changes no balance, which
 *   holds because the return page reads no parameter at all;
 * * **T1024 / J4** — no amount ever becomes a number, proven by seeding a
 *   violation and watching CI's own guard reject it.
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

import WalletPage from "@/app/wallet/page";
import StatementPage from "@/app/wallet/statement/page";
import TopupStatusPage from "@/app/wallet/topup/[reference]/page";
import InvoicePage from "@/app/invoices/[id]/page";

const WALLET = {
  currency: "SAR",
  total: "30000.75",
  available: "12000.25",
  held_for_auctions: "10000.50",
  locked_for_dues: "8000.00",
  buckets: [
    { kind: "insurance_free", label: "تأمين متاح", amount: "12000.25", entry_count: 4, statement: "x?bucket=insurance_free" },
    { kind: "insurance_held", label: "تأمين محجوز لمزاد", amount: "10000.50", entry_count: 2, statement: "x?bucket=insurance_held" },
    { kind: "insurance_locked", label: "تأمين مقفول لمستحقات", amount: "8000.00", entry_count: 1, statement: "x?bucket=insurance_locked" },
    { kind: "wallet", label: "المحفظة", amount: "0.00", entry_count: 0, statement: "x?bucket=wallet" },
  ],
  holds: [
    {
      id: 3,
      amount: "10000.50",
      reason: "bidding",
      reason_label: "ضمان المزايدة",
      auction: { id: 7, number: 811 },
      invoice: null,
      created_at: "2026-09-01T08:00:00Z",
    },
  ],
  as_of: "2026-09-03T09:00:00Z",
};

const INTENT = {
  reference: "TOP-42",
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

const INVOICE = {
  id: 12,
  number: "INV/2026/12",
  amount: "48500.75",
  amount_paid: "500.25",
  outstanding: "48000.50",
  state: "partial",
  state_label: "مسدَّدة جزئياً",
  issued_at: "2026-09-01T08:00:00Z",
  due_at: null,
  payment_methods: [
    { method: "balance", label: "من الرصيد" },
    { method: "bank_transfer", label: "تحويل بنكي" },
  ],
};

function answer(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

async function render(element: Promise<React.ReactElement>) {
  return renderToStaticMarkup(await element);
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
// T1019 / G5 — three numbers, and none of them added up here
// ---------------------------------------------------------------------------

describe("المحفظة", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn(async () => answer(WALLET)));
  });

  it("ثلاثة أرقام لا واحد", async () => {
    // v1 showed one. A customer read «رصيدك 10,000», assumed it was his to
    // withdraw, and discovered it was pinned to a bid.
    const html = await render(WalletPage());

    expect(html).toContain("12000.25");
    expect(html).toContain("10000.50");
    expect(html).toContain("8000.00");
  });

  it("المجموع حقلٌ من الخادم لا جمعٌ في المتصفح", async () => {
    // 12000.25 + 10000.50 + 8000.00 is 30000.75 — and in JavaScript it is
    // 30000.749999999996. The page shows the server's string, so the digits are
    // the ledger's.
    const html = await render(WalletPage());

    expect(html).toContain("30000.75");
    expect(html).not.toContain("30000.749");
  });

  it("كل رقم يُفتح على الحركات التي تفسّره", async () => {
    // Article 1-6, and the difference between «لماذا 8,000 مقفولة؟» being a
    // click and being a support call.
    const html = await render(WalletPage());

    expect(html).toContain("/wallet/statement?bucket=insurance_free");
    expect(html).toContain("/wallet/statement?bucket=insurance_locked");
  });

  it("كل حجز يقول على ماذا هو", async () => {
    const html = await render(WalletPage());

    expect(html).toContain("ضمان المزايدة");
    expect(html).toContain("811");
  });

  it("لا حدّ أقصى محسوب على طلب الاسترداد", async () => {
    // One open request per customer is a database constraint, not a check a
    // screen performs: in v1 ten requests each passed the same check against the
    // same untouched balance and instructed accounting to pay out ten times.
    const html = await render(WalletPage());

    expect(html).toContain('name="amount"');
    expect(html).not.toContain("max=");
  });
});

// ---------------------------------------------------------------------------
// T1020 — the statement is the entries
// ---------------------------------------------------------------------------

describe("كشف الحركات", () => {
  const ENTRIES = {
    count: 2,
    results: [
      {
        id: 1,
        transaction: "t1",
        kind: "insurance_topup",
        description: "إيداع تأمين",
        bucket: "insurance_free",
        bucket_label: "تأمين متاح",
        amount: "10000.00",
        direction: "in",
        occurred_at: "2026-09-01T08:00:00Z",
        memo: "تحويل بنكي",
      },
      {
        id: 2,
        transaction: "t2",
        kind: "insurance_hold",
        description: "حجز تأمين لمزاد",
        bucket: "insurance_held",
        bucket_label: "تأمين محجوز لمزاد",
        amount: "10000.00",
        direction: "out",
        occurred_at: "2026-09-02T08:00:00Z",
        memo: "",
      },
    ],
  };

  it("يمرّر الدلو إلى الخادم بدل الترشيح في الصفحة", async () => {
    let url = "";
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        url = (input as Request).url;
        return answer(ENTRIES);
      }),
    );

    await render(
      StatementPage({ searchParams: Promise.resolve({ bucket: "insurance_locked" }) }),
    );

    expect(url).toContain("bucket=insurance_locked");
  });

  it("الاتجاه من الخادم لا مستنتَجاً من المبلغ", async () => {
    // "In or out" is a ledger convention written down once, in
    // `apps/money/models`. Deriving it here from the sign of a string would be
    // this page's own reading of it.
    vi.stubGlobal("fetch", vi.fn(async () => answer(ENTRIES)));

    const html = await render(StatementPage({ searchParams: Promise.resolve({}) }));

    expect(html).toContain("إيداع تأمين");
    expect(html).toContain("−");
    expect(html).toContain("+");
  });
});

// ---------------------------------------------------------------------------
// T1021 — the return page reads no parameter
// ---------------------------------------------------------------------------

describe("العودة من بوابة الدفع", () => {
  it("الحالة من سجلّنا، والمرجع وحده يأتي من الرابط", async () => {
    let url = "";
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        url = (input as Request).url;
        return answer(INTENT);
      }),
    );

    const html = await render(
      TopupStatusPage({ params: Promise.resolve({ reference: "TOP-42" }) }),
    );

    expect(url).toContain("/api/v1/wallet/topups/TOP-42/");
    expect(html).toContain("بانتظار الدفع");
  });

  it("التلاعب بمعاملات العودة لا يغيّر شيئاً", async () => {
    // The criterion, and the way it is satisfied: the page consults no query
    // parameter at all. `?status=paid` renders the stored state, which is what
    // v1 got wrong — it believed the query string.
    vi.stubGlobal("fetch", vi.fn(async () => answer(INTENT)));

    const html = await render(
      TopupStatusPage({ params: Promise.resolve({ reference: "TOP-42" }) }),
    );

    expect(html).toContain("بانتظار الدفع");
    expect(html).not.toContain("تمت");
    expect(html).toContain("لا من رابط العودة");
  });

  it("الشحن لا يسمّي مبلغاً", async () => {
    // The figure is `deposit_amount_for`'s. A request that named its own amount
    // would be proposing a deposit the rules did not set, and is refused at the
    // edge anyway.
    let body: Record<string, unknown> = {};
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        body = JSON.parse(await (input as Request).text());
        return answer(INTENT, 201);
      }),
    );

    const { startTopup } = await import("@/features/wallet/actions");
    const data = new FormData();
    data.set("auction", "7");
    await startTopup(data).catch(() => {});

    expect(body).toEqual({ auction: 7 });
    expect(Object.keys(body)).not.toContain("amount");
  });
});

// ---------------------------------------------------------------------------
// T1023 — the invoice, and the subtraction that is not done here
// ---------------------------------------------------------------------------

describe("الفاتورة والسداد", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn(async () => answer(INVOICE)));
  });

  it("المتبقّي حقلٌ من الخادم لا طرحٌ في الصفحة", async () => {
    // 48500.75 − 500.25 is 48000.50, and in JavaScript it is 48000.499999999996.
    // A cancelled invoice's outstanding is also zero whatever its columns say —
    // which is the real reason the subtraction is not done here.
    const html = await render(InvoicePage({ params: Promise.resolve({ id: "12" }) }));

    expect(html).toContain("48000.50");
    expect(html).not.toContain("48000.499");
  });

  it("طرق السداد من الخادم بأسمائها، ولا بطاقة بينها", async () => {
    const html = await render(InvoicePage({ params: Promise.resolve({ id: "12" }) }));

    expect(html).toContain("من الرصيد");
    expect(html).toContain("تحويل بنكي");
    expect(html).not.toContain('value="card"');
  });

  it("بلا طريقة متاحة، لا زرّ سداد", async () => {
    // A button that will certainly be refused is worse than a sentence.
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => answer({ ...INVOICE, payment_methods: [] })),
    );

    const html = await render(InvoicePage({ params: Promise.resolve({ id: "12" }) }));

    expect(html).toContain("لا توجد طريقة سداد متاحة");
    expect(html).not.toContain("سدّد<");
  });
});

// ---------------------------------------------------------------------------
// T1024 / J4 — seeded violations fail the guard
// ---------------------------------------------------------------------------

describe("لا Number على أي مبلغ", () => {
  it("الشجرة نظيفة", async () => {
    const { violations } = await import(
      "../../../ops/checks/web_money_is_never_computed.mjs"
    );

    expect(await violations()).toEqual([]);
  });

  it.each([
    ['const x = Number(reserve_price);\n', "Number على مبلغ"],
    ['const x = parseFloat(amount);\n', "parseFloat على مبلغ"],
    ['const total = amount + outstanding;\n', "جمع مبلغين"],
    ['const shown = balance.toFixed(2);\n', "تقريب مبلغ"],
  ])("يُسقِط: %s", async (source) => {
    // J4 word for word: «زرع مخالفة يُسقط الـCI». Four shapes, because the one
    // somebody writes is whichever one their editor autocompleted.
    const { mkdtemp, writeFile, rm } = await import("node:fs/promises");
    const { tmpdir } = await import("node:os");
    const { join } = await import("node:path");

    const scratch = await mkdtemp(join(tmpdir(), "haraj-money-"));
    try {
      await writeFile(join(scratch, "seeded.ts"), source, "utf8");

      const { violations } = await import(
        "../../../ops/checks/web_money_is_never_computed.mjs"
      );

      expect(await violations(scratch)).toHaveLength(1);
    } finally {
      await rm(scratch, { recursive: true, force: true });
    }
  });
});
