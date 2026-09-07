/**
 * T1004 — الجلسة تصمد عبر إعادة التحميل، وليس في الذاكرة ولا في `localStorage`.
 *
 * The acceptance has two halves and this file holds both:
 *
 * * **the text check** — `ops/checks/web_tokens_are_httponly.mjs`, run here
 *   rather than only wired into CI, because a guard nothing executes is a guard
 *   that starts failing quietly. The last test proves it can fail, by handing it
 *   a file that breaks the rule;
 * * **the behaviour** — the session survives a reload with no token anywhere in
 *   client memory, which is what the cookie flags below actually buy.
 *
 * The cookie store is a plain map here rather than Next's. What is under test is
 * *which flags this module sets*, and running a framework to find that out would
 * test the framework.
 */

import { describe, expect, it } from "vitest";
import { readFile } from "node:fs/promises";
import { join } from "node:path";

import {
  ACCESS_COOKIE,
  REFRESH_COOKIE,
  accessToken,
  authHeader,
  clearSession,
  hasSession,
  refreshToken,
  setSession,
} from "@/lib/session";

interface Written {
  value: string;
  options: Record<string, unknown>;
}

/** A stand-in for Next's cookie store, remembering the options it was given. */
function store() {
  const jar = new Map<string, Written>();
  return {
    jar,
    set(name: string, value: string, options: Record<string, unknown>) {
      jar.set(name, { value, options });
    },
    get(name: string) {
      const written = jar.get(name);
      return written ? { name, value: written.value } : undefined;
    },
    delete(name: string) {
      jar.delete(name);
    },
  };
}

type Store = Parameters<typeof setSession>[0];

describe("the session lives in cookies the browser cannot read", () => {
  it("marks both cookies HttpOnly", () => {
    const cookies = store();
    setSession(cookies as unknown as Store, { access: "a", refresh: "r" });

    for (const name of [ACCESS_COOKIE, REFRESH_COOKIE]) {
      expect(cookies.jar.get(name)?.options.httpOnly).toBe(true);
    }
  });

  it("sends them SameSite=Lax on every path", () => {
    // Lax, not Strict: a customer arriving from a Google result is a top-level
    // GET and must stay signed in — that arrival is the whole point of the
    // server-rendered auction pages. And Lax still keeps the cookie off a
    // cross-site POST, which is the shape of a CSRF attempt on the wallet.
    const cookies = store();
    setSession(cookies as unknown as Store, { access: "a", refresh: "r" });

    const written = cookies.jar.get(ACCESS_COOKIE);
    expect(written?.options.sameSite).toBe("lax");
    expect(written?.options.path).toBe("/");
  });

  it("keeps the refresh cookie longer than the access cookie", () => {
    // An expired access token can be refreshed; a missing cookie is
    // indistinguishable from signing out.
    const cookies = store();
    setSession(cookies as unknown as Store, { access: "a", refresh: "r" });

    const access = Number(cookies.jar.get(ACCESS_COOKIE)?.options.maxAge);
    const refresh = Number(cookies.jar.get(REFRESH_COOKIE)?.options.maxAge);
    expect(refresh).toBeGreaterThan(access);
  });

  it("survives a reload: the token is read back from the cookie, not from memory", () => {
    const cookies = store();
    setSession(cookies as unknown as Store, { access: "token-1", refresh: "refresh-1" });

    // A reload keeps nothing but the jar. Everything else — module state,
    // React state, the client instance — is gone by definition.
    const afterReload = { get: cookies.get.bind(cookies) } as unknown as Store;

    expect(hasSession(afterReload)).toBe(true);
    expect(accessToken(afterReload)).toBe("token-1");
    expect(refreshToken(afterReload)).toBe("refresh-1");
    expect(authHeader(afterReload)).toEqual({ Authorization: "Bearer token-1" });
  });

  it("offers no session and no header when there is no cookie", () => {
    const cookies = store();

    expect(hasSession(cookies as unknown as Store)).toBe(false);
    expect(authHeader(cookies as unknown as Store)).toEqual({});
  });

  it("clears both cookies on sign-out, not only the access one", () => {
    // A refresh token left behind is a session somebody resumes from a shared
    // machine. A sign-out that leaves a way back in is worse than no button.
    const cookies = store();
    setSession(cookies as unknown as Store, { access: "a", refresh: "r" });

    clearSession(cookies as unknown as Store);

    expect(cookies.jar.size).toBe(0);
  });
});

describe("the guard that keeps tokens out of readable storage", () => {
  it("passes on the tree as it stands", async () => {
    const { violations } = await import(
      "../../../ops/checks/web_tokens_are_httponly.mjs"
    );

    expect(await violations()).toEqual([]);
  });

  it("catches a token put in localStorage", async () => {
    // Proven by breaking it. Without this the check above is a promise: it
    // passes today and nobody knows whether it would notice the thing it exists
    // to notice.
    const { mkdtemp, writeFile, rm } = await import("node:fs/promises");
    const { tmpdir } = await import("node:os");
    const { join } = await import("node:path");

    const scratch = await mkdtemp(join(tmpdir(), "haraj-guard-"));
    try {
      await writeFile(
        join(scratch, "leak.ts"),
        'export const t = localStorage.getItem("haraj_access");\n',
        "utf8",
      );

      const { violations } = await import(
        "../../../ops/checks/web_tokens_are_httponly.mjs"
      );
      const found = await violations(scratch);

      expect(found).toHaveLength(1);
      expect(found[0]).toContain("localStorage");
    } finally {
      await rm(scratch, { recursive: true, force: true });
    }
  });
});

// ---------------------------------------------------------------------------
// الجلسة تجدّد نفسها — والعطلان اللذان منعا ذلك
// ---------------------------------------------------------------------------

describe("تجديد الجلسة", () => {
  it("الوسيط يعمل على عقدة لا على الحافّة", async () => {
    /*
      قِيس (2026-09-07): على الحافّة يرسل عميلُ العقد `POST` **بلا جسم**،
      فتردّ الخلفية «هذا الحقل مطلوب» ويُقرأ ذلك رفضاً للرمز — فتُمسح الجلسة
      بدل أن تُجدَّد. أي أن السطر الواحد أدناه هو الفرق بين تجديدٍ وخروجٍ
      كامل، ولا شيء في الأنواع يمسك حذفه.
    */
    const source = await readFile(join("middleware.ts"), "utf8");

    expect(source).toMatch(/export const runtime = "nodejs"/);
  });

  it("عمرُ كوكي الوصول عمرُ الرمز، لا يوماً كاملاً", async () => {
    //: كان يوماً بينما الرمز ربع ساعة، فتقول `hasSession` «داخل» على رمزٍ
    //: ميت: الشاشة تعرض صندوق المزايدة وكل فعلٍ يردّ 401. وغيابُ الكوكي هو
    //: ما يقرؤه الوسيط ليجدّد، فإطالتُه تُعطّل التجديد أيضاً.
    const source = await readFile(join("lib", "session.ts"), "utf8");

    expect(source).toMatch(/expiresIn/);
    expect(source).not.toMatch(/ACCESS_MAX_AGE = 60 \* 60 \* 24/);
  });

  it("قراءة الرسالة لا تحذفها — الحذف في الوسيط", async () => {
    /*
      `takeFlash` كانت تحذف الكوكي وهي تُنادى من **سبع** مكوّنات خادم، وNext
      يرفض تعديل كوكي في رندرة: كل فعلٍ يضع رسالةً ثم يحوّل كان ينتهي بخطأ
      خادم. ولم يكشفه اختبار لأن `next/headers` مستبدَلٌ بمخزنٍ متساهل — ولذلك
      يُقاس المصدر هنا، ويحرسه `ops/checks/web_renders_never_write_cookies.mjs`.
    */
    const source = await readFile(join("lib", "flash.ts"), "utf8");

    expect(source).toMatch(/export function readFlash/);
    expect(source).not.toMatch(/export function takeFlash/);

    const body = source.slice(source.indexOf("export function readFlash"));
    expect(body).not.toMatch(/store\.delete\(/);
  });

  it("ولا رندرة تكتب كوكي — الحارس يمرّ على الشجرة كما هي", async () => {
    const { violations } = await import(
      "../../../ops/checks/web_renders_never_write_cookies.mjs"
    );

    expect(await violations()).toEqual([]);
  });
});
