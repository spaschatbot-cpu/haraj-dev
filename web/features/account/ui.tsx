/**
 * قطعُ «حسابي» المشتركة — شكلُ الحقل والبطاقة ورأسُ الصفحة الداخليّة.
 *
 * صار «حسابي» صفحةً رئيسيّةً وصفحاتٍ داخليّة كما في v1 (`menu/accounts.php`:
 * بطاقةُ ملخّصٍ ثم قائمةُ أقسام، وكلُّ قسمٍ شاشتُه). فشكلُ الحقل يُكتب مرّةً
 * هنا: سطرُ `className` منسوخٌ في أربع صفحاتٍ يُعدَّل في ثلاثٍ ويُنسى في الرابعة.
 */

import Link from "next/link";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { ApiError, api, request } from "@/lib/api";
import { authHeader, hasSession } from "@/lib/session";

export const FIELD =
  "h-11 w-full rounded-lg border border-outline-variant bg-surface-lowest px-3 text-body-md text-on-surface transition-colors placeholder:text-outline focus:border-secondary focus:outline-none focus:ring-2 focus:ring-secondary/20 disabled:bg-surface-low disabled:text-on-surface-variant";
export const LABEL = "flex flex-col gap-1.5";
export const LABEL_TEXT = "text-label-md text-on-surface-variant";
export const PRIMARY =
  "inline-flex h-11 items-center justify-center rounded-lg bg-primary px-5 text-label-md text-on-primary transition-opacity hover:opacity-90";
export const CARD = "rounded-2xl border border-outline-variant/60 bg-surface-lowest p-5 md:p-6";

/**
 * الجلسةُ والملفّ معاً — كلُّ صفحةٍ داخليّةٍ تبدأ بهما.
 *
 * رمزٌ منتهٍ أو مسحوبٌ هو جلسةٌ انتهت، والجوابُ الصادق صفحةُ الدخول — لا شاشةُ
 * خطأٍ تُعاد تحميلاً على صفحةٍ لن تُحمَّل أبداً.
 */
export async function loadProfile() {
  const store = await cookies();
  if (!hasSession(store)) redirect("/sign-in");
  const headers = authHeader(store);

  try {
    const profile = await request(() => api.GET("/api/v1/profile/", { headers }));
    return { store, headers, profile };
  } catch (error) {
    if (error instanceof ApiError && (error.status === 401 || error.status === 403)) {
      redirect("/sign-in");
    }
    throw error;
  }
}

/** رأسُ الصفحة الداخليّة: رجوعٌ إلى «حسابي» ثم العنوان — كزرّ «رجوع» في v1. */
export function SubpageHead({ title, hint }: { title: string; hint?: string }) {
  return (
    <div className="mb-6">
      <Link
        href="/account"
        className="mb-3 inline-flex items-center gap-1.5 text-label-md text-secondary hover:underline"
      >
        <svg viewBox="0 0 24 24" aria-hidden="true" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M9 6l6 6-6 6" />
        </svg>
        حسابي
      </Link>
      <h1 className="text-headline-lg">{title}</h1>
      {hint ? <p className="mt-1 text-body-sm text-on-surface-variant">{hint}</p> : null}
    </div>
  );
}

export function CardHead({ title, hint, badge }: { title: string; hint?: string; badge?: React.ReactNode }) {
  return (
    <div className="mb-5 flex items-start justify-between gap-3">
      <div>
        <h2 className="text-headline-sm">{title}</h2>
        {hint ? <p className="text-body-sm text-on-surface-variant">{hint}</p> : null}
      </div>
      {badge}
    </div>
  );
}

export function Pill({ tone, children }: { tone: "ok" | "warn"; children: React.ReactNode }) {
  return tone === "ok" ? (
    <span className="rounded-full bg-secondary-fixed px-3 py-1 text-label-sm text-on-secondary-fixed">{children}</span>
  ) : (
    <span className="rounded-full border border-warn-line bg-warn-surface px-3 py-1 text-label-sm text-warn">{children}</span>
  );
}
