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

  // المزادُ الجاري لكرت المزاد — فشله أو غيابه لا يُسقط شاشة الدخول
  const live = sent
    ? null
    : await request(() =>
        api.GET("/api/v1/auctions/", { params: { query: { state: "live", limit: 1 } } }),
      )
        .then((page) => page.results[0] ?? null)
        .catch(() => null);

  const now = await respondedAt();

  return (
    <main className="min-h-screen bg-surface px-3 py-4 md:px-6 md:py-8 lg:flex lg:items-center lg:justify-center">
      <div className="mx-auto w-full max-w-5xl overflow-hidden rounded-3xl border border-outline-variant/60 bg-surface-lowest shadow-2xl">
        <div className="grid grid-cols-1 lg:grid-cols-12">
          
          {/* ── الجانب الأيمن: واجهة المزاد الحية وأجواء المنصة (Hero Side) ── */}
          <div className="relative flex flex-col justify-between border-b border-outline-variant/40 bg-gradient-to-br from-primary via-primary to-[#13233f] p-6 text-on-primary md:p-8 lg:col-span-5 lg:border-b-0 lg:border-e lg:p-10">
            {/* توهج خلفي جمالي */}
            <div aria-hidden="true" className="pointer-events-none absolute -top-24 -end-24 h-64 w-64 rounded-full bg-secondary/20 blur-3xl" />
            <div aria-hidden="true" className="pointer-events-none absolute -bottom-24 -start-24 h-64 w-64 rounded-full bg-ok/10 blur-3xl" />

            {/* الهوية والشعار */}
            <div className="relative z-10">
              <div className="flex items-center gap-3">
                <span className="relative flex h-14 w-14 items-center justify-center rounded-2xl bg-surface-lowest/10 backdrop-blur-md ring-1 ring-white/20">
                  <Image
                    src="/brand/logo-light.png"
                    alt=""
                    width={507}
                    height={455}
                    className="h-8 w-8 object-contain"
                    priority
                  />
                  <span className="tnum absolute -bottom-1 -end-1 rounded-full bg-secondary px-1.5 py-0.2 text-[10px] font-bold text-on-secondary ring-1 ring-primary">
                    V2
                  </span>
                </span>
                <div>
                  <h1 className="text-headline-md font-bold tracking-tight text-white">مزاد حراج واحد</h1>
                  <p className="text-body-sm on-navy-muted">منصة المزايدة المغلقة على سيارات المزاد</p>
                </div>
              </div>

              {/* بطاقة المزاد الجاري الحي */}
              {live ? (
                <div className="mt-6 rounded-2xl border border-white/15 bg-white/5 p-4 backdrop-blur-md shadow-lg">
                  <div className="mb-2 flex items-center justify-between gap-2">
                    <span className="inline-flex items-center gap-2 text-label-md font-bold on-navy-ok">
                      <span aria-hidden="true" className="relative flex h-2.5 w-2.5">
                        <span className="absolute inline-flex h-full w-full animate-ping rounded-full on-navy-ok-dot opacity-75" />
                        <span className="relative inline-flex h-2.5 w-2.5 rounded-full on-navy-ok-dot" />
                      </span>
                      المزاد الجاري · مزاد <span className="tnum">{live.number}</span>
                    </span>
                    {live.vehicle_count !== null ? (
                      <span className="rounded-lg bg-white/10 px-2.5 py-0.5 text-label-sm font-semibold text-inverse-on-surface">
                        <span className="money font-bold">{count(live.vehicle_count)}</span> سيارة
                      </span>
                    ) : null}
                  </div>

                  <div className="mt-2 rounded-xl bg-black/25 p-2.5">
                    <Countdown
                      endsAt={live.ends_at}
                      initial={remaining(live.ends_at, now)}
                      now={now}
                      label="ينتهي بعد"
                    />
                  </div>
                </div>
              ) : (
                <div className="mt-6 rounded-2xl border border-white/10 bg-white/5 p-4 text-body-sm on-navy-muted">
                  ⚡ مزادات دورية مستمرة — سجّل دخولك لتكون جاهزاً للمزايدة فور انطلاق المزاد القادم.
                </div>
              )}

              {/* ركائز الأمان والثقة الثلاث */}
              <div className="mt-8 space-y-3 hidden sm:block">
                <div className="flex items-start gap-3 text-body-sm text-inverse-on-surface">
                  <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-white/10 on-navy-ok">
                    <svg viewBox="0 0 24 24" aria-hidden="true" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
                      <path d="M7 11V7a5 5 0 0 1 10 0v4" />
                    </svg>
                  </span>
                  <div>
                    <strong className="block font-semibold text-white">مزايدة مغلقة ومحمية</strong>
                    <span className="text-caption on-navy-muted">لا أحد يرى مبلغ مزايدتك ولا يمكن لأحد منافستك بالاحتكار.</span>
                  </div>
                </div>

                <div className="flex items-start gap-3 text-body-sm text-inverse-on-surface">
                  <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-white/10 on-navy-info">
                    <svg viewBox="0 0 24 24" aria-hidden="true" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z" />
                    </svg>
                  </span>
                  <div>
                    <strong className="block font-semibold text-white">دخول سريع بلا كلمة مرور</strong>
                    <span className="text-caption on-navy-muted">رمز تحقق فوري لمرة واحدة يُرسل إلى هاتفك المحمول.</span>
                  </div>
                </div>

                <div className="flex items-start gap-3 text-body-sm text-inverse-on-surface">
                  <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-white/10 on-navy-warn">
                    <svg viewBox="0 0 24 24" aria-hidden="true" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
                    </svg>
                  </span>
                  <div>
                    <strong className="block font-semibold text-white">التأمين وديعة مستردة</strong>
                    <span className="text-caption on-navy-muted">مبلغ التأمين وديعة في محفظتك يُسترد بطلبك في أي وقت.</span>
                  </div>
                </div>
              </div>
            </div>

            {/* تذييل قسم الهوية */}
            <div className="relative z-10 mt-6 pt-4 border-t border-white/10 flex items-center justify-between text-caption on-navy-faint">
              <span>المملكة العربية السعودية</span>
              <span>منصة مرخصة ومعتمدة</span>
            </div>
          </div>

          {/* ── الجانب الأيسر: بطاقة المصادقة وإدخال البيانات (Auth Form) ── */}
          <div className="flex flex-col justify-between p-6 md:p-8 lg:col-span-7 lg:p-10">
            <div>
              {/* شريط الإغلاق والتنقل */}
              <div className="flex items-center justify-between pb-6">
                <span className="inline-flex items-center gap-2 rounded-full border border-outline-variant/60 bg-surface-low px-3 py-1 text-label-sm text-on-surface-variant">
                  <span aria-hidden="true" className="h-2 w-2 rounded-full bg-ok" />
                  حراج واحد <span className="tnum">v2</span>
                </span>
                <Link
                  href="/"
                  aria-label="المتابعة كزائر والعودة للمزادات"
                  className="inline-flex items-center gap-1.5 rounded-full border border-outline-variant/60 bg-surface-lowest px-3 py-1.5 text-label-sm text-on-surface-variant transition-colors hover:bg-surface-low hover:text-on-surface"
                >
                  <span>المتابعة كزائر</span>
                  <svg viewBox="0 0 24 24" aria-hidden="true" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                    <path d="M6 6l12 12M18 6L6 18" />
                  </svg>
                </Link>
              </div>

              {/* رأس النموذج */}
              <div className="mb-6">
                <div className="mb-3 inline-flex h-12 w-12 items-center justify-center rounded-2xl bg-secondary-fixed text-on-secondary-fixed shadow-sm">
                  {sent ? (
                    <svg viewBox="0 0 24 24" aria-hidden="true" className="h-6 w-6" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M21 2l-2 2m-7.61 7.61a5.5 5.5 0 1 1-7.778 7.778 5.5 5.5 0 0 1 7.777-7.777zm0 0L15.5 7.5m0 0l3 3L22 7l-3-3m-3.5 3.5L19 4" />
                    </svg>
                  ) : (
                    <svg viewBox="0 0 24 24" aria-hidden="true" className="h-6 w-6" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <rect x="5" y="11" width="14" height="10" rx="2" />
                      <path d="M8 11V8a4 4 0 0 1 8 0v3" />
                    </svg>
                  )}
                </div>
                <h2 className="text-headline-md font-bold text-on-surface">
                  {sent ? "أدخل رمز التحقق" : "الدخول أو إنشاء حساب"}
                </h2>
                <p className="mt-1 text-body-sm text-on-surface-variant">
                  {sent ? (
                    <>
                      أرسلنا رمز تحقق سريع إلى الرقم{" "}
                      <span className="money font-bold text-on-surface">{phone}</span>
                    </>
                  ) : (
                    "أدخل رقم جوالك لتصلك رسالة نصية برمز التحقق لمرة واحدة."
                  )}
                </p>
              </div>

              {/* تنبيهات الخادم */}
              <Notice message={flash?.message ?? ""} />

              {/* النموذج بحسب الخطوة */}
              {sent ? (
                /* ── الخطوة ٢: التحقق من رمز OTP ── */
                <form action={verifyCode} className="space-y-5">
                  <input type="hidden" name="phone" value={phone} />

                  <label className="flex flex-col gap-2">
                    <span className="text-label-md font-semibold text-on-surface">الرمز المرسل</span>
                    <input
                      type="text"
                      name="code"
                      inputMode="numeric"
                      autoComplete="one-time-code"
                      required
                      placeholder="••••••"
                      maxLength={6}
                      className="money h-16 w-full rounded-2xl border-2 border-outline-variant bg-surface-lowest px-4 text-center text-hero tracking-[0.4em] text-on-surface shadow-xs transition-colors focus:border-secondary focus:outline-none focus:ring-4 focus:ring-secondary/15"
                    />
                  </label>

                  <button
                    type="submit"
                    className="flex h-14 w-full items-center justify-center rounded-2xl bg-secondary text-headline-sm font-bold text-on-secondary shadow-lg shadow-secondary/25 transition-all hover:opacity-95 active:scale-[0.99]"
                  >
                    تأكيد ودخول
                  </button>

                  <div className="flex items-center justify-center pt-1">
                    <Link
                      href="/sign-in"
                      className="text-label-md font-semibold text-secondary hover:underline"
                    >
                      تغيير رقم الجوال
                    </Link>
                  </div>
                </form>
              ) : (
                /* ── الخطوة ١: إدخال رقم الجوال ── */
                <form action={sendCode} className="space-y-4">
                  <label className="flex flex-col gap-2">
                    <span className="text-label-md font-semibold text-on-surface">رقم الجوال</span>
                    <div className="flex h-14 items-stretch overflow-hidden rounded-2xl border-2 border-outline-variant bg-surface-lowest transition-colors focus-within:border-secondary focus-within:ring-4 focus-within:ring-secondary/15">
                      <span className="flex items-center gap-2 border-e border-outline-variant/60 bg-surface-low px-3.5 text-headline-sm">
                        {/* علم السعودية برسم SVG دقيق */}
                        <svg viewBox="0 0 30 20" aria-hidden="true" className="h-5 w-7 shrink-0 rounded-[3px] shadow-xs">
                          <rect width="30" height="20" fill="#006c35" />
                          <path d="M8 8.5h14M9.5 7c1-.6 2 .6 3 0s2 .6 3 0 2 .6 3 0 2 .6 3 0" stroke="#fff" strokeWidth="1" fill="none" strokeLinecap="round" />
                          <path d="M8 13h13l1.5-1" stroke="#fff" strokeWidth="1.2" fill="none" strokeLinecap="round" />
                        </svg>
                        <span className="money text-label-md font-bold text-on-surface">+966</span>
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
                    </div>
                  </label>

                  <button
                    type="submit"
                    className="flex h-14 w-full items-center justify-center gap-2.5 rounded-2xl bg-secondary text-headline-sm font-bold text-on-secondary shadow-lg shadow-secondary/25 transition-all hover:opacity-95 hover:shadow-xl active:scale-[0.99]"
                  >
                    <svg viewBox="0 0 24 24" aria-hidden="true" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M21 12a8 8 0 0 1-11.6 7.1L4 20l1-4.6A8 8 0 1 1 21 12z" />
                      <path d="M8.5 12h.01M12 12h.01M15.5 12h.01" />
                    </svg>
                    إرسال رمز التحقق
                  </button>

                  <p className="text-center text-caption text-on-surface-variant">
                    الحسابُ الجديد يُنشأ تلقائياً عند التحقق من الرمز، ثم تُكمل بياناتك.
                  </p>
                </form>
              )}
            </div>

            {/* الجزء السفلي: إعادة الإرسال في الخطوة ٢ أو روابط المساعدة في الخطوة ١ */}
            {sent ? (
              <form action={sendCode} className="mt-6 rounded-2xl border border-outline-variant/60 bg-surface-low p-4">
                <input type="hidden" name="phone" value={phone} />
                <button
                  type="submit"
                  className="h-11 w-full rounded-xl border border-outline-variant bg-surface-lowest text-label-md font-semibold text-on-surface transition-colors hover:bg-surface-low"
                >
                  أعِد إرسال الرمز
                </button>
                <p className="mt-2 text-center text-caption text-on-surface-variant">
                  لم تصلك الرسالة؟ يمكن طلبُ رمزٍ جديد بعد دقيقة من إرسال السابق.
                </p>
              </form>
            ) : (
              <div className="mt-8 border-t border-outline-variant/40 pt-4 text-center">
                <Link
                  href="/"
                  className="text-body-sm font-medium text-on-surface-variant transition-colors hover:text-on-surface hover:underline"
                >
                  إغلاق والمتابعة كزائر في تصفح السيارات ←
                </Link>
              </div>
            )}
          </div>

        </div>
      </div>
    </main>
  );
}
