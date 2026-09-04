/**
 * الدخول والتسجيل بالجوال — خطوتان، ونماذج تعمل بلا جافاسكربت. T1011.
 *
 * Two renders of one route rather than two routes: the step is decided by
 * whether a code has been sent, which is in the url. That keeps the back button
 * meaningful — going back from the code screen returns to the number screen,
 * which is what people expect and what a single-route wizard with client state
 * gets wrong.
 *
 * Both forms submit to server actions (`features/auth/actions.ts`). No client
 * state, no fetch, no hydration needed: the page works with scripting off,
 * which is the same standard the browse pages are held to and matters more
 * here — this is the screen a customer reaches when something has already gone
 * wrong for them.
 */

import type { Metadata } from "next";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { sendCode, verifyCode } from "@/features/auth/actions";
import { Notice } from "@/features/shell/Notice";
import { PageShell } from "@/features/shell/PageShell";
import { takeFlash } from "@/lib/flash";
import { hasSession } from "@/lib/session";

export const metadata: Metadata = {
  title: "الدخول",
  // Not indexed: a sign-in form in a search result is a phishing template, and
  // it is of no use to anybody arriving from a search anyway.
  robots: { index: false, follow: false },
};

export const dynamic = "force-dynamic";

export default async function SignInPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const store = await cookies();
  if (hasSession(store)) redirect("/account");

  const params = await searchParams;
  const phone = typeof params.phone === "string" ? params.phone : "";
  const sent = params.sent === "1";
  const flash = takeFlash(store);

  return (
    <PageShell title={sent ? "أدخل الرمز" : "الدخول"}>
      <div className="mx-auto max-w-sm">
        <Notice message={flash?.message ?? ""} />

        {sent ? (
          <form action={verifyCode} className="space-y-4">
            <input type="hidden" name="phone" value={phone} />

            <p className="text-sm text-neutral-600">
              أرسلنا رمزاً إلى <span className="money">{phone}</span>.
            </p>

            <label className="flex flex-col gap-1 text-sm">
              <span className="text-neutral-600">الرمز</span>
              <input
                type="text"
                name="code"
                inputMode="numeric"
                autoComplete="one-time-code"
                required
                className="money rounded border border-neutral-500 px-3 py-2 text-lg"
              />
            </label>

            {/*
              Optional, and only used when the backend decides this is a new
              customer. The web does not look the number up first to find out —
              that is a rule, and rules live on the server.
            */}
            <label className="flex flex-col gap-1 text-sm">
              <span className="text-neutral-600">الاسم (للتسجيل الجديد فقط)</span>
              <input
                type="text"
                name="full_name"
                autoComplete="name"
                className="rounded border border-neutral-500 px-3 py-2"
              />
            </label>

            <button
              type="submit"
              className="w-full rounded bg-neutral-900 px-4 py-2 text-white"
            >
              تأكيد
            </button>

            <a href="/sign-in" className="block text-center text-sm underline">
              تغيير الرقم
            </a>
          </form>
        ) : (
          <form action={sendCode} className="space-y-4">
            <label className="flex flex-col gap-1 text-sm">
              <span className="text-neutral-600">رقم الجوال</span>
              <input
                type="tel"
                name="phone"
                defaultValue={phone}
                inputMode="tel"
                autoComplete="tel"
                required
                placeholder="9665XXXXXXXX"
                className="money rounded border border-neutral-500 px-3 py-2 text-lg"
              />
            </label>

            <button
              type="submit"
              className="w-full rounded bg-neutral-900 px-4 py-2 text-white"
            >
              أرسل الرمز
            </button>
          </form>
        )}
      </div>
    </PageShell>
  );
}
