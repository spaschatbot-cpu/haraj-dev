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
import { readFlash } from "@/lib/flash";
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
  const flash = readFlash(store);

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
              **لا اسمَ هنا.** كان حقلٌ «الاسم (للتسجيل الجديد فقط)» يُرسَل مع
              الرمز، فيُتجاهَل لحسابٍ موجودٍ باسمٍ فارغ ولا يعرف العميلُ لماذا
              لم يُحفظ. البياناتُ كلُّها — للجديد والناقص معاً — في «أكمل
              تسجيلك» بعد الرمز (`verifyCode` → `/sign-in/complete`).
            */}
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
        ) : null}

        {sent ? (
          /*
            إعادةُ الإرسال — وكانت غائبة. v1 يعرض عدّاداً ينزل من ١٢٠ ثانيةً
            ثمّ يُفعّل «إعادة الإرسال» (`log2/verify.php`)، وهنا لم يكن للعميل
            بابٌ إلى رمزٍ ثانٍ إلا أن يعرف أن «تغيير الرقم» ثمّ إعادةَ كتابة
            الرقم نفسِه تُرسله — وهو ما لا يخطر لأحد. والرسالةُ التي لا تصل
            هي أوّلُ ما يحدث للعميل حين يُغلق الطريق.

            واستمارةٌ ثانيةٌ لا زرٌّ في الأولى: زرّان في استمارةٍ واحدةٍ
            يُرسلان إلى وجهةٍ واحدة، والفصلُ يُبقي الصفحةَ تعمل بلا جافاسكربت
            كما هي.

            ولا عدّادَ ينزل: العدّادُ جافاسكربت، والخادمُ يحرس المهلةَ على أيّ
            حال (`OtpResendTooSoon`) فيقول متى يُعاد. والمكتوبُ تحته يقول
            المدّةَ سلفاً فلا يُضغط في فراغ.
          */
          <form action={sendCode} className="mt-6 border-t border-neutral-200 pt-4">
            <input type="hidden" name="phone" value={phone} />
            <button
              type="submit"
              className="w-full rounded border border-neutral-500 px-4 py-2 text-sm"
            >
              أعِد إرسال الرمز
            </button>
            <p className="mt-2 text-center text-xs text-neutral-600">
              لم تصلك الرسالة؟ يمكن طلبُ رمزٍ جديد بعد دقيقة من إرسال السابق.
            </p>
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
                /* والصيغةُ أيُّها: الخادمُ يطبّع 05… و5… و+966… و966…
                   (`normalise_saudi_mobile`). والمثالُ ما يكتبه الناسُ فعلاً
                   لا ما يخزّنه العمود. */
                placeholder="05XXXXXXXX"
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
