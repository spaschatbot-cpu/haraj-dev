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
 *
 * **تصميمُ المالك** (٢٨ سبتمبر ٢٠٢٦): شعارٌ في دائرة، وكرتُ المزاد الجاري
 * بعدّاده، وبطاقةُ الدخول بخانة جوّالٍ مسبوقةٍ بـ+966، وثلاثُ ميزاتٍ تحتها، وخروجٌ
 * «كزائر». **والبياناتُ بياناتُنا**: المزادُ الجاري من `GET /api/v1/auctions/`
 * لا رقمٌ مكتوب، والميزاتُ وقائعُ النظام. وسقط من التصميم ما ليس فينا: «موثّقٌ
 * عبر النفاذ الوطني»، و«الدعم الفني» (لا صفحةَ له بعد)، و«استرجاعُ التأمين
 * بلحظات» — الاستردادُ تنفّذه المحاسبة، ووعدٌ في شاشة الدخول أوّلُ ما يُكذَّب.
 *
 * **ومختصرةٌ لتُرى بلا تمرير** (طلبُ المالك في اليوم نفسه): شعارٌ أصغر، وكرتُ
 * المزاد سطران، والميزاتُ عناوينُ بلا شرح، وسقط «مثال: 5…» لأن الخانةَ تقوله.
 *
 * **ولا `PageShell` هنا:** شاشةُ دخولٍ مركّزة بلا شريط أقسامٍ لا يفتح منها شيءٌ
 * لغير الداخل، والخروجُ منها زرٌّ واضح (✕ و«المتابعة كزائر») إلى المزادات.
 */

import type { Metadata } from "next";
import Image from "next/image";
import Link from "next/link";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { sendCode, verifyCode } from "@/features/auth/actions";
import { Countdown } from "@/features/catalog/Countdown";
import { Notice } from "@/features/shell/Notice";
import { api, request } from "@/lib/api";
import { readFlash } from "@/lib/flash";
import { count, remaining, respondedAt } from "@/lib/format";
import { hasSession } from "@/lib/session";

export const metadata: Metadata = {
  title: "الدخول",
  // Not indexed: a sign-in form in a search result is a phishing template, and
  // it is of no use to anybody arriving from a search anyway.
  robots: { index: false, follow: false },
};

export const dynamic = "force-dynamic";

const CARD = "rounded-3xl border border-outline-variant/60 bg-surface-lowest p-5 shadow-sm";

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

  // المزادُ الجاري لكرت الرأس — **زينةٌ لا ركن**: فشلُه أو غيابُ مزادٍ جارٍ يُخفي
  // الكرتَ ولا يُسقط شاشةَ الدخول.
  const live = sent
    ? null
    : await request(() =>
        api.GET("/api/v1/auctions/", { params: { query: { state: "live", limit: 1 } } }),
      )
        .then((page) => page.results[0] ?? null)
        .catch(() => null);
  // لحظةُ الردّ من `respondedAt` كبقيّة الصفحات — `Date.now()` في الرسم يرفضه
  // `react-hooks/purity`، ويجعل الرسمين (الخادم والمتصفّح) يختلفان.
  const now = await respondedAt();

  return (
    <main className="bg-gradient-to-b from-surface-low to-surface px-4 pt-3 pb-3">
      <div className="mx-auto max-w-md">
        {/* ── الشريطُ العلويّ ─────────────────────────────────────────── */}
        <div className="flex items-center justify-between">
          <span className="inline-flex items-center gap-2 rounded-full border border-outline-variant/60 bg-surface-lowest px-3.5 py-1.5 text-label-md shadow-sm">
            <span aria-hidden="true" className="h-2 w-2 rounded-full bg-ok" />
            حراج واحد <span className="tnum">v2</span>
          </span>
          <Link
            href="/"
            aria-label="إغلاق والعودة إلى المزادات"
            className="flex h-10 w-10 items-center justify-center rounded-full border border-outline-variant/60 bg-surface-lowest text-on-surface shadow-sm transition-colors hover:bg-surface-low"
          >
            <svg viewBox="0 0 24 24" aria-hidden="true" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
              <path d="M6 6l12 12M18 6L6 18" />
            </svg>
          </Link>
        </div>

        {/* ── الشعار ───────────────────────────────────────────────────── */}
        <div className="-mt-4 flex flex-col items-center text-center">
          <span className="relative flex h-20 w-20 items-center justify-center rounded-full bg-primary shadow-xl shadow-primary/25 ring-4 ring-surface-lowest">
            <span aria-hidden="true" className="absolute inset-2 rounded-full border border-on-primary/15" />
            {/*
              الشعارُ لا الحرف، أبيضُ على الكحليّ كما في رأس الموقع. و`alt=""`
              لأن الاسم مكتوبٌ نصّاً تحته: بديلٌ يقوله ثانيةً يُقرأ مرّتين.
            */}
            <Image src="/brand/logo-light.png" alt="" width={507} height={455} className="h-10 w-10 object-contain" priority />
            <span className="tnum absolute -bottom-2 rounded-full bg-secondary px-2.5 py-0.5 text-label-sm text-on-secondary ring-2 ring-surface-lowest">
              V2
            </span>
          </span>
          <h1 className="mt-4 text-headline-md">مزاد حراج واحد</h1>
          <p className="text-body-sm text-on-surface-variant">مزايدة مغلقة على سيارات المزاد — من جوالك</p>
        </div>

        {/* ── المزادُ الجاري ───────────────────────────────────────────── */}
        {live ? (
          <section className="mt-3 rounded-2xl border border-outline-variant/60 bg-surface-lowest p-3.5 shadow-sm" aria-label="المزاد الجاري">
            <div className="mb-2.5 flex items-center justify-between gap-3">
              <span className="inline-flex items-center gap-2 whitespace-nowrap text-label-md">
                <span aria-hidden="true" className="h-2.5 w-2.5 rounded-full bg-ok" />
                المزاد الجاري · مزاد <span className="tnum">{live.number}</span>
              </span>
              {live.vehicle_count !== null ? (
                <span className="rounded-lg bg-surface-container px-2.5 py-1 text-label-sm text-secondary">
                  <span className="money">{count(live.vehicle_count)}</span> سيارة
                </span>
              ) : null}
            </div>
            <Countdown endsAt={live.ends_at} initial={remaining(live.ends_at, now)} now={now} label="ينتهي بعد" />
          </section>
        ) : null}

        {/* ── الدخول ───────────────────────────────────────────────────── */}
        <section className={`${CARD} mt-4`}>
          <div className="mb-3 flex items-center gap-3">
            <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-surface-container text-secondary">
              <svg viewBox="0 0 24 24" aria-hidden="true" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <rect x="5" y="11" width="14" height="10" rx="2" />
                <path d="M8 11V8a4 4 0 0 1 8 0v3" />
              </svg>
            </span>
            <h2 className="text-headline-sm">{sent ? "أدخل رمز التحقق" : "الدخول أو إنشاء حساب"}</h2>
          </div>

          <Notice message={flash?.message ?? ""} />

          {sent ? (
            <form action={verifyCode} className="space-y-4">
              <input type="hidden" name="phone" value={phone} />

              <p className="text-body-sm text-on-surface-variant">
                أرسلنا رمزاً إلى <span className="money text-on-surface" dir="ltr">{phone}</span>.
              </p>

              <label className="flex flex-col gap-1.5">
                <span className="text-label-md text-on-surface-variant">الرمز</span>
                <input
                  type="text"
                  name="code"
                  inputMode="numeric"
                  autoComplete="one-time-code"
                  required
                  dir="ltr"
                  placeholder="••••••"
                  className="money h-16 rounded-2xl border-2 border-outline-variant bg-surface-lowest px-4 text-center text-headline-md tracking-[0.5em] focus:border-secondary focus:outline-none focus:ring-4 focus:ring-secondary/15"
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
                className="flex h-14 w-full items-center justify-center rounded-2xl bg-secondary text-headline-sm text-on-secondary shadow-lg shadow-secondary/25 transition-opacity hover:opacity-90"
              >
                تأكيد ودخول
              </button>

              <Link href="/sign-in" className="block text-center text-label-md text-secondary hover:underline">
                تغيير الرقم
              </Link>
            </form>
          ) : (
            <form action={sendCode} className="space-y-3">
              <p className="text-body-sm text-on-surface-variant">
                أدخل رقم جوالك ونرسل لك رمز تحقق سريع بلا كلمة مرور.
              </p>

              {/*
                **+966 مسبوقةٌ في الشكل، والرقمُ كما يُكتب.** الخادمُ يطبّع 05…
                و5… و+966… و966… (`normalise_saudi_mobile`)، فالبادئةُ تذكيرٌ لا
                جزءٌ من القيمة — ومن كتب 05 كاملةً لا يُرفض.
              */}
              <label className="flex h-14 items-stretch overflow-hidden rounded-2xl border-2 border-outline-variant bg-surface-lowest focus-within:border-secondary focus-within:ring-4 focus-within:ring-secondary/15" dir="ltr">
                <span className="flex items-center gap-2 border-e border-outline-variant/60 bg-surface-low px-4 text-headline-sm">
                  {/* العلمُ رسمٌ لا إيموجي: ويندوز لا يرسم أعلامَ الإيموجي فيكتب «SA»
                      حرفين — قِيس في كروم على هذا الجهاز. */}
                  <svg viewBox="0 0 30 20" aria-hidden="true" className="h-5 w-7 rounded-[3px]">
                    <rect width="30" height="20" fill="#006c35" />
                    <path d="M8 8.5h14M9.5 7c1-.6 2 .6 3 0s2 .6 3 0 2 .6 3 0 2 .6 3 0" stroke="#fff" strokeWidth="1" fill="none" strokeLinecap="round" />
                    <path d="M8 13h13l1.5-1" stroke="#fff" strokeWidth="1.2" fill="none" strokeLinecap="round" />
                  </svg>
                  <span className="money">+966</span>
                </span>
                <span className="sr-only">رقم الجوال</span>
                <input
                  type="tel"
                  name="phone"
                  defaultValue={phone}
                  inputMode="tel"
                  autoComplete="tel"
                  required
                  placeholder="5X XXX XXXX"
                  className="money min-w-0 flex-1 bg-transparent px-4 text-headline-sm tracking-wider placeholder:text-outline focus:outline-none"
                />
              </label>
              <button
                type="submit"
                className="flex h-14 w-full items-center justify-center gap-2 rounded-2xl bg-secondary text-headline-sm text-on-secondary shadow-lg shadow-secondary/25 transition-opacity hover:opacity-90"
              >
                <svg viewBox="0 0 24 24" aria-hidden="true" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M21 12a8 8 0 0 1-11.6 7.1L4 20l1-4.6A8 8 0 1 1 21 12z" />
                  <path d="M8.5 12h.01M12 12h.01M15.5 12h.01" />
                </svg>
                إرسال رمز التحقق
              </button>
              <p className="text-center text-caption text-on-surface-variant">
                الحسابُ الجديد يُنشأ عند التحقق من الرمز، ثم تُكمل بياناتك.
              </p>
            </form>
          )}
        </section>

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
          <form action={sendCode} className={`${CARD} mt-4`}>
            <input type="hidden" name="phone" value={phone} />
            <button
              type="submit"
              className="h-12 w-full rounded-2xl border-2 border-outline-variant text-label-md transition-colors hover:bg-surface-low"
            >
              أعِد إرسال الرمز
            </button>
            <p className="mt-2 text-center text-caption text-on-surface-variant">
              لم تصلك الرسالة؟ يمكن طلبُ رمزٍ جديد بعد دقيقة من إرسال السابق.
            </p>
          </form>
        ) : (
          <ul className="mt-3 space-y-1.5 px-1">
            <Feature
              title="مزايدة مغلقة: لا يرى أحد مبلغك"
              icon="M3 3l18 18M10.6 5.1A10 10 0 0 1 12 5c5 0 9 4.5 10 7a13 13 0 0 1-2.6 3.9M6.6 6.6A13 13 0 0 0 2 12c1 2.5 5 7 10 7a9.8 9.8 0 0 0 5.4-1.6M9.9 9.9a3 3 0 0 0 4.2 4.2"
            />
            <Feature
              title="بلا كلمة مرور — رمز لمرة واحدة"
              icon="M15 7a4 4 0 1 1-3.9 4.9L3 20v-3l2-2h2v-2h2l1.1-1.1A4 4 0 0 1 15 7zM16 9h.01"
            />
            <Feature
              title="التأمين وديعة مستردة بطلبك"
              icon="M12 3l8 4v5c0 4.5-3.4 8.3-8 9-4.6-.7-8-4.5-8-9V7zM9 12l2 2 4-4"
            />
          </ul>
        )}

        <Link href="/" className="mt-3 block text-center text-label-md text-on-surface-variant hover:text-on-surface">
          إغلاق والمتابعة كزائر
        </Link>
      </div>
    </main>
  );
}

function Feature({ title, icon }: { title: string; icon: string }) {
  return (
    <li className="flex items-center gap-2.5 text-body-sm text-on-surface-variant">
      <svg viewBox="0 0 24 24" aria-hidden="true" className="h-5 w-5 shrink-0 text-secondary" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        <path d={icon} />
      </svg>
      {title}
    </li>
  );
}
