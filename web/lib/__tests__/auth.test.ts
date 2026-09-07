/**
 * T1011 و T1012 — المسار كاملاً، والتفرقة التي كلّفت v1 عملاء.
 *
 * The acceptance criterion has two halves and the second is the one worth the
 * file: *فشل الإرسال يُميَّز عن خطأ الكود (نظير T603)*.
 *
 * In v1 an SMS provider outage reached the customer as «الرمز غير صحيح». They
 * retyped a code that was never sent until the attempt limit locked them out,
 * and afterwards support could not tell the two cases apart either — the log
 * recorded one failure for both. The backend now answers with different codes
 * and different sentences, and the only thing this layer can do wrong is
 * flatten them. So the tests below assert that two different refusals produce
 * two different sentences, and that neither is a sentence written in the web.
 *
 * The other thing under test is where the token ends up. `verifyCode` must
 * write cookies and hand the browser a redirect and nothing else: a token in
 * the response body, in the url, or in any client-readable place is the whole
 * of T1004 undone at the one moment it matters.
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
    // Next implements a redirect by throwing, and the code under test depends
    // on that: nothing after a `redirect()` runs. A mock that returned normally
    // would let the action continue past a failure and pass a test the real
    // thing would fail.
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

function refusal(code: string, message: string, status = 409) {
  return answer({ error: { code, message, detail: {} } }, status);
}

/** Run an action and swallow the redirect it throws, returning where it went. */
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

function flash(): { code: string; message: string } | null {
  const raw = cookieJar.get("haraj_flash")?.value;
  return raw ? (JSON.parse(raw) as { code: string; message: string }) : null;
}

beforeEach(() => {
  cookieJar.clear();
  redirects.length = 0;
});

afterEach(() => {
  vi.unstubAllGlobals();
});

// ---------------------------------------------------------------------------
// T1011 — the whole path
// ---------------------------------------------------------------------------

describe("الدخول بالجوال", () => {
  it("المسار كاملاً: رقم ← رمز ← جلسة", async () => {
    const calls: string[] = [];
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        const url = typeof input === "string" ? input : (input as Request).url;
        calls.push(url);
        if (url.includes("/auth/code/")) {
          return answer({ sent: true, expires_at: "2026-09-03T10:05:00Z", resend_after: 60 });
        }
        return answer({
          access: "access-token",
          refresh: "refresh-token",
          expires_in: 3600,
          expires_at: "2026-09-03T11:00:00Z",
        });
      }),
    );

    const { sendCode, verifyCode } = await import("@/features/auth/actions");

    const afterSend = await run(() => sendCode(form({ phone: "966500000001" })));
    expect(calls[0]).toContain("/api/v1/auth/code/");
    expect(afterSend).toContain("sent=1");

    const afterVerify = await run(() =>
      verifyCode(form({ phone: "966500000001", code: "123456" })),
    );
    expect(afterVerify).toBe("/account");
    expect(cookieJar.get("haraj_access")?.value).toBe("access-token");
    expect(cookieJar.get("haraj_refresh")?.value).toBe("refresh-token");
  });

  it("الرمز لا يظهر في أي رابط", async () => {
    // A code in the url is a code in the browser history, in a shared screen,
    // and in whatever the next site sees as a referrer.
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => refusal("otp_incorrect", "الرمز غير صحيح.", 400)),
    );

    const { verifyCode } = await import("@/features/auth/actions");
    const to = await run(() => verifyCode(form({ phone: "966500000001", code: "999999" })));

    expect(to).not.toContain("999999");
    expect(to).not.toContain("code=");
  });

  it("الرمز الصحيح يكتب كوكيز HttpOnly، ولا يعيد الرمز إلى المتصفح", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        answer({
          access: "access-token",
          refresh: "refresh-token",
          expires_in: 3600,
          expires_at: "2026-09-03T11:00:00Z",
        }),
      ),
    );

    const { verifyCode } = await import("@/features/auth/actions");
    const to = await run(() => verifyCode(form({ phone: "966500000001", code: "123456" })));

    expect(cookieJar.get("haraj_access")?.options.httpOnly).toBe(true);
    expect(cookieJar.get("haraj_refresh")?.options.httpOnly).toBe(true);
    expect(to).not.toContain("access-token");
  });
});

// ---------------------------------------------------------------------------
// The distinction — T603's lesson in the web
// ---------------------------------------------------------------------------

describe("فشل الإرسال ≠ خطأ الرمز", () => {
  const CASES = [
    {
      what: "تعذّر إرسال الرسالة",
      code: "sms_undeliverable",
      message: "ما قدرنا نرسل الرمز الآن. جرّب بعد قليل.",
    },
    {
      what: "الرمز غير صحيح",
      code: "otp_incorrect",
      message: "الرمز غير صحيح.",
    },
    {
      what: "الرمز انتهت مهلته",
      code: "otp_expired",
      message: "انتهت مهلة الرمز. اطلب رمزاً جديداً.",
    },
    {
      what: "محاولات كثيرة",
      code: "otp_too_many_attempts",
      message: "محاولات كثيرة. اطلب رمزاً جديداً.",
    },
  ];

  it.each(CASES)("$what يصل بجملته هو", async ({ code, message }) => {
    vi.stubGlobal("fetch", vi.fn(async () => refusal(code, message)));

    const { verifyCode } = await import("@/features/auth/actions");
    await run(() => verifyCode(form({ phone: "966500000001", code: "123456" })));

    const shown = flash();
    expect(shown?.code).toBe(code);
    expect(shown?.message).toBe(message);
  });

  it("جملتان مختلفتان لحالتين مختلفتين — لا رسالة موحّدة", async () => {
    // The assertion the criterion is really about: whatever the web does, the
    // two must not arrive at the customer as the same sentence.
    const { verifyCode, sendCode } = await import("@/features/auth/actions");

    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        refusal("sms_undeliverable", "ما قدرنا نرسل الرمز الآن. جرّب بعد قليل."),
      ),
    );
    await run(() => sendCode(form({ phone: "966500000001" })));
    const undeliverable = flash()?.message;

    vi.stubGlobal(
      "fetch",
      vi.fn(async () => refusal("otp_incorrect", "الرمز غير صحيح.", 400)),
    );
    await run(() => verifyCode(form({ phone: "966500000001", code: "111111" })));
    const incorrect = flash()?.message;

    expect(undeliverable).toBeTruthy();
    expect(incorrect).toBeTruthy();
    expect(undeliverable).not.toBe(incorrect);
  });

  it("الرسالة تعيش في كوكي لا في الرابط", async () => {
    // A message in a url is a message anybody can write: a crafted link renders
    // whatever it says, on our domain and in our layout. React escapes it, so it
    // is not an XSS — it is a phishing page, which is worse in that nothing in
    // the code looks broken.
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => refusal("otp_incorrect", "الرمز غير صحيح.", 400)),
    );

    const { verifyCode } = await import("@/features/auth/actions");
    const to = await run(() => verifyCode(form({ phone: "966500000001", code: "1" })));

    expect(to).not.toContain("الرمز");
    expect(to).not.toContain("message=");
    expect(cookieJar.get("haraj_flash")?.options.httpOnly).toBe(true);
  });
});

// ---------------------------------------------------------------------------
// T1012 — the account, and the rules it does not own
// ---------------------------------------------------------------------------

describe("الملف الشخصي", () => {
  it("يخرج بالكوكي الذي كتبه الخادم، لا برمز من المتصفح", async () => {
    let sent: Headers | undefined;
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        sent = (input as Request).headers;
        return answer({ id: 1, full_name: "عميل" });
      }),
    );

    cookieJar.set("haraj_access", { value: "server-side-token", options: {} });

    const { saveProfile } = await import("@/features/account/actions");
    await run(() => saveProfile(form({ full_name: "عميل جديد", email: "" })));

    expect(sent?.get("authorization")).toBe("Bearer server-side-token");
  });

  it("رفض الخادم لرقم هوية يصل بجملته، ولا يُفحَص في الويب", async () => {
    // `apps/accounts/identity.py` owns what "valid" means. A checksum here would
    // refuse a number the backend accepts — or accept one it refuses — and
    // either way tell a customer something untrue about their own identity.
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => refusal("national_id_invalid", "رقم الهوية غير صحيح.", 400)),
    );

    const { saveNationalId } = await import("@/features/account/actions");
    await run(() => saveNationalId(form({ national_id: "1234567890" })));

    expect(flash()?.message).toBe("رقم الهوية غير صحيح.");
    expect(flash()?.code).toBe("national_id_invalid");
  });

  it("رقم هوية مثبَّت لا يُغيَّر — والرفض من الخادم لا من الصفحة", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        refusal("national_id_already_verified", "رقم الهوية مسجَّل ولا يمكن تغييره."),
      ),
    );

    const { saveNationalId } = await import("@/features/account/actions");
    await run(() => saveNationalId(form({ national_id: "1000000001" })));

    expect(flash()?.message).toContain("لا يمكن تغييره");
  });

  it("بيانات الشركة تُرسَل كاملة لا كفروق", async () => {
    // The endpoint takes the profile as a unit and the backend decides whether
    // the result is complete. Sending only edited fields would make "complete"
    // depend on which box somebody happened to touch.
    let body: unknown;
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        body = JSON.parse(await (input as Request).text());
        return answer({ name: "شركة", is_complete: true });
      }),
    );

    const { saveCompany } = await import("@/features/account/actions");
    await run(() => saveCompany(form({ name: "شركة المعارض" })));

    const keys = Object.keys(body as Record<string, unknown>);
    expect(keys).toContain("name");
    expect(keys).toContain("postal_code");
    expect(keys).toContain("commercial_register");
    expect(keys).toHaveLength(9);
  });

  it("الخروج يمسح الكوكيَّين معاً", async () => {
    cookieJar.set("haraj_access", { value: "a", options: {} });
    cookieJar.set("haraj_refresh", { value: "r", options: {} });

    const { signOut } = await import("@/features/auth/actions");
    const to = await run(() => signOut());

    expect(cookieJar.has("haraj_access")).toBe(false);
    expect(cookieJar.has("haraj_refresh")).toBe(false);
    expect(to).toBe("/");
  });
});
