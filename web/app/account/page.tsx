/**
 * حسابي — الصفحةُ الرئيسيّة: بطاقةُ ملخّصٍ، ثم أقسامُ الحساب. T1012.
 *
 * **بناءُ v1 نفسُه** (`menu/accounts.php`)، بطلب المالك في ٢٤ سبتمبر ٢٠٢٦:
 * «يكون فيها صفحات داخلية زي النظام القديم». هناك بطاقةٌ فيها الاسمُ ورقمُ
 * العميل والجوّالُ ونوعُ الحساب، ثم قائمةُ أزرارٍ كلٌّ منها يفتح قسماً:
 * التأمين، والاسترداد، والمحفظة، والمشتريات، والمشاركات، والمفضّلة، وتعديلُ
 * البيانات. وهنا الترتيبُ نفسُه في ثلاث مجموعات، وكلُّ قسمٍ صفحةٌ لها رابطُها.
 *
 * وكانت قبل ذلك صفحةً واحدةً فيها أربعةُ نماذج متتالية — يفتحها من يريد
 * محفظتَه فيجد نموذجَ تغيير الجوّال.
 *
 * **ما لم يُنقل من v1، ولماذا:**
 *
 * * «طلبات» (نقلٌ وتنازلٌ واستلامٌ وتوصيل) و«الدليل والمساعدة» والشروط —
 *   لا نقطةَ لها في العقد ولا صفحة. ورابطٌ يقود إلى 404 يُقرأ عطلاً في المنتج
 *   (القاعدةُ نفسُها في ذيل `PageShell`). تُضاف مع صفحاتها.
 * * «التأمين مفعّل/غير مفعّل» — في v1 حالةُ اشتراك. وهنا لا حكمَ يُشتقّ في
 *   الشاشة: أهليّةُ المزايدة قرارُ `apps/bidding/eligibility.py` وحده، وفيه
 *   عشرةُ أسباب رفضٍ لا يرى هذا الملفُّ أكثرَها. فيُعرض **رصيدُ المحفظة المتاح**
 *   كما قاله الخادم، والحكمُ يُقال عند المزايدة.
 */

import type { Metadata } from "next";
import Link from "next/link";

import { loadProfile } from "@/features/account/ui";
import { signOut } from "@/features/auth/actions";
import { Notice } from "@/features/shell/Notice";
import { PageShell } from "@/features/shell/PageShell";
import { api, request } from "@/lib/api";
import { readFlash } from "@/lib/flash";
import { amount } from "@/lib/format";

export const metadata: Metadata = {
  title: "حسابي",
  robots: { index: false, follow: false },
};

export const dynamic = "force-dynamic";

type Entry = { href: string; title: string; detail: string; icon: string; tone?: "accent" | "danger" };

export default async function AccountPage() {
  const { store, headers, profile } = await loadProfile();
  const flash = readFlash(store);

  // **الرصيدُ زينةٌ لا ركن**: فشلُه لا يُسقط صفحةَ الحساب، فيُعرض القسمُ بلا رقم.
  const wallet = await request(() => api.GET("/api/v1/wallet/", { headers })).catch(() => null);

  const isCompany = profile.account_type === "company";
  const name = profile.full_name || profile.display_name;
  const initial = (name || "؟").trim().charAt(0);

  const groups: Array<{ title: string; items: Entry[] }> = [
    {
      title: "المحفظة والتأمين",
      items: [
        {
          href: "/wallet",
          title: "دفع تأمين المزاد",
          detail: "اشحن محفظتك لتدخل المزادات",
          icon: "M12 3l8 4v5c0 4.5-3.4 8.3-8 9-4.6-.7-8-4.5-8-9V7z",
          tone: "accent",
        },
        {
          href: "/wallet",
          title: "المحفظة",
          detail: wallet ? `${amount(wallet.available)} ${wallet.currency} متاح` : "الرصيد والحجوزات والحركات",
          icon: "M3 7h18v12H3zM3 7l3-3h12l3 3M16 13h2",
        },
        {
          href: "/wallet#refund",
          title: "طلب استرداد مبلغ التأمين",
          detail: "يُنفَّذ من المحاسبة ويظهر في حركاتك",
          icon: "M4 12a8 8 0 1 0 2.3-5.7M4 4v4h4",
          tone: "danger",
        },
      ],
    },
    {
      title: "مزاداتي",
      items: [
        { href: "/purchases", title: "مشترياتي", detail: "ما رسا عليك وفواتيره", icon: "M6 7h12l-1 13H7zM9 7a3 3 0 0 1 6 0" },
        {
          href: "/account/participations",
          title: "مشاركاتي في المزادات",
          detail: "كلُّ مزادٍ دخلتَه وتأمينُه",
          icon: "M4 20h16M7 16l9-9 3 3-9 9H7zM14 5l3 3",
        },
        { href: "/bids", title: "مزايداتي", detail: "كلُّ عرضٍ قدّمتَه", icon: "M5 12h14M12 5v14" },
        { href: "/favourites", title: "المفضّلة", detail: "سياراتٌ تتابعها", icon: "M12 20s-7-4.4-7-10a4 4 0 0 1 7-2.6A4 4 0 0 1 19 10c0 5.6-7 10-7 10z" },
      ],
    },
    {
      title: "الحساب",
      items: [
        {
          href: "/account/profile",
          title: "تعديل البيانات",
          detail: isCompany ? "بياناتك والهوية والمنشأة" : "بياناتك ورقم الهوية",
          icon: "M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM4 21a8 8 0 0 1 16 0",
        },
        {
          href: "/account/phone",
          title: "تغيير رقم الجوال",
          detail: "برمزين: للرقم الحالي وللجديد",
          icon: "M8 3h8a1 1 0 0 1 1 1v16a1 1 0 0 1-1 1H8a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1zM11 18h2",
        },
      ],
    },
  ];

  return (
    <PageShell>
      <Notice message={flash?.message ?? ""} tone={flash?.code === "saved" ? "info" : "error"} />

      <div className="mx-auto max-w-3xl">
        {/* ── بطاقةُ الملخّص ─────────────────────────────────────────────── */}
        <section className="relative overflow-hidden rounded-3xl bg-primary p-6 text-on-primary md:p-8">
          <div
            aria-hidden="true"
            className="pointer-events-none absolute -start-20 -top-24 h-72 w-72 rounded-full bg-secondary/40 blur-3xl"
          />
          <div className="relative flex items-center gap-4">
            <span className="flex h-16 w-16 shrink-0 items-center justify-center rounded-2xl bg-on-primary/10 text-headline-lg ring-1 ring-on-primary/20">
              {initial}
            </span>
            <div className="min-w-0 flex-1">
              <p className="text-label-sm text-on-primary/70">حسابي</p>
              <h1 className="truncate text-headline-lg">{name}</h1>
              <p className="mt-0.5 flex flex-wrap items-center gap-x-3 text-body-sm text-on-primary/80">
                {/* رقمُ العميل كما في v1 (`#client_no`) — وهو هنا مفتاحُ الحساب. */}
                <span className="money">#{profile.id}</span>
                <span className="money" dir="ltr">+{profile.phone}</span>
              </p>
            </div>
          </div>

          <ul className="relative mt-5 flex flex-wrap gap-2">
            <Fact tone="plain">{isCompany ? "حساب شركة" : "حساب فرد"}</Fact>
            {profile.phone_verified_at ? <Fact tone="ok">الجوال موثّق</Fact> : <Fact tone="warn">الجوال غير موثّق</Fact>}
            {profile.national_id_verified ? <Fact tone="ok">الهوية مثبّتة</Fact> : <Fact tone="warn">رقم الهوية ناقص</Fact>}
            {isCompany ? (
              profile.company_profile_complete ? (
                <Fact tone="ok">بيانات المنشأة مكتملة</Fact>
              ) : (
                <Fact tone="warn">بيانات المنشأة ناقصة</Fact>
              )
            ) : null}
          </ul>

          {wallet ? (
            <div className="relative mt-5 flex items-end justify-between gap-4 border-t border-on-primary/15 pt-4">
              <div>
                <p className="text-label-sm text-on-primary/70">رصيد التأمين المتاح</p>
                <p className="money text-headline-md">
                  {amount(wallet.available)} <span className="text-body-sm text-on-primary/70">{wallet.currency}</span>
                </p>
              </div>
              <Link
                href="/wallet"
                className="inline-flex h-10 items-center rounded-lg bg-on-primary px-4 text-label-md text-primary transition-opacity hover:opacity-90"
              >
                المحفظة
              </Link>
            </div>
          ) : null}
        </section>

        {/* ── الأقسام ────────────────────────────────────────────────────── */}
        {groups.map((group) => (
          <section key={group.title} className="mt-6">
            <h2 className="mb-2 px-1 text-label-md text-on-surface-variant">{group.title}</h2>
            <ul className="divide-y divide-outline-variant/50 overflow-hidden rounded-2xl border border-outline-variant/60 bg-surface-lowest">
              {group.items.map((item) => (
                <li key={item.title}>
                  <Row {...item} />
                </li>
              ))}
            </ul>
          </section>
        ))}

        {/*
          A form, never a link: a `GET` that ends a session is a session ended by a
          prefetch, a crawler, or an image tag on somebody else's page.
        */}
        <form action={signOut} className="mt-6">
          <button
            type="submit"
            className="flex w-full items-center justify-center gap-2 rounded-2xl border border-critical-line bg-critical-surface py-3.5 text-label-md text-critical transition-colors hover:bg-critical-line/40"
          >
            <svg viewBox="0 0 24 24" aria-hidden="true" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 3v9M6.3 6.3a8 8 0 1 0 11.4 0" />
            </svg>
            تسجيل الخروج
          </button>
        </form>
      </div>
    </PageShell>
  );
}

function Row({ href, title, detail, icon, tone }: Entry) {
  const badge =
    tone === "accent"
      ? "bg-secondary text-on-secondary"
      : tone === "danger"
        ? "bg-critical-surface text-critical"
        : "bg-surface-container text-secondary";
  return (
    <Link href={href} className="flex items-center gap-4 px-4 py-3.5 transition-colors hover:bg-surface-low">
      <span className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-xl ${badge}`}>
        <svg viewBox="0 0 24 24" aria-hidden="true" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
          <path d={icon} />
        </svg>
      </span>
      <span className="min-w-0 flex-1">
        <span className="block text-label-md text-on-surface">{title}</span>
        <span className="money block truncate text-body-sm text-on-surface-variant">{detail}</span>
      </span>
      {/* السهمُ يشير إلى اليسار: في واجهةٍ عربيّة «التالي» يساراً. */}
      <svg viewBox="0 0 24 24" aria-hidden="true" className="h-4 w-4 shrink-0 text-outline" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M15 6l-6 6 6 6" />
      </svg>
    </Link>
  );
}

//: واقعةٌ من الخادم لا حكم — انظر رأسَ الملفّ.
function Fact({ tone, children }: { tone: "ok" | "warn" | "plain"; children: React.ReactNode }) {
  const look =
    tone === "ok"
      ? "bg-on-primary/10 text-on-primary ring-on-primary/25"
      : tone === "warn"
        ? "bg-warn-surface text-warn ring-warn-line"
        : "bg-transparent text-on-primary/80 ring-on-primary/25";
  return (
    <li className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-label-sm ring-1 ${look}`}>
      {tone === "ok" ? (
        <svg viewBox="0 0 24 24" aria-hidden="true" className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
          <path d="M5 12.5l4.5 4.5L19 7.5" />
        </svg>
      ) : tone === "warn" ? (
        <span aria-hidden="true" className="h-1.5 w-1.5 rounded-full bg-warn" />
      ) : null}
      {children}
    </li>
  );
}
