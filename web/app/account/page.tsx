/**
 * الحساب — الملف الشخصي والشركة والعنوان الوطني. T1012.
 *
 * Server-rendered like everything else, and every form is a plain `POST` to a
 * server action. Nothing on this page holds a token, and nothing on it decides
 * anything: what may be edited, whether a company profile is complete, whether
 * the national id is still changeable — all of it is read off the profile the
 * backend returned.
 *
 * `national_id_verified` is the clearest case. The field is disabled when the
 * server says the id is verified, and the *reason* it is disabled is the
 * server's answer, not a rule this page knows. That is why the flag is read
 * rather than derived from whether `national_id` is non-empty: those two are
 * the same thing today and stop being the same thing the first time somebody
 * stores an unverified value.
 */

import type { Metadata } from "next";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import {
  confirmPhoneChange,
  saveCompany,
  saveNationalId,
  saveProfile,
  startPhoneChange,
} from "@/features/account/actions";
import { signOut } from "@/features/auth/actions";
import { Notice } from "@/features/shell/Notice";
import { PageShell } from "@/features/shell/PageShell";
import { ApiError, api, request } from "@/lib/api";
import { readFlash } from "@/lib/flash";
import { authHeader, hasSession } from "@/lib/session";

export const metadata: Metadata = {
  title: "حسابي",
  robots: { index: false, follow: false },
};

export const dynamic = "force-dynamic";

const COMPANY_FIELDS: Array<[string, string]> = [
  ["name", "اسم الشركة"],
  ["representative_name", "اسم الممثّل"],
  ["commercial_register", "السجل التجاري"],
  ["vat_number", "الرقم الضريبي"],
  ["building_number", "رقم المبنى"],
  ["street", "الشارع"],
  ["district", "الحي"],
  ["city", "المدينة"],
  ["postal_code", "الرمز البريدي"],
];

export default async function AccountPage() {
  const store = await cookies();
  if (!hasSession(store)) redirect("/sign-in");

  const flash = readFlash(store);
  const headers = authHeader(store);

  let profile;
  try {
    profile = await request(() => api.GET("/api/v1/profile/", { headers }));
  } catch (error) {
    // An expired or revoked token is the session being over, and the honest
    // response is the sign-in page — not an error screen that leaves somebody
    // pressing reload on a page that can never load again.
    if (error instanceof ApiError && (error.status === 401 || error.status === 403)) {
      redirect("/sign-in");
    }
    throw error;
  }

  const company = profile.has_company_profile
    ? await request(() => api.GET("/api/v1/profile/company/", { headers }))
    : null;

  return (
    <PageShell title="حسابي">
      <Notice
        message={flash?.message ?? ""}
        tone={flash?.code === "saved" ? "info" : "error"}
      />

      <section className="mb-10">
        <h2 className="mb-3 text-lg font-semibold">بياناتي</h2>

        <form action={saveProfile} className="max-w-md space-y-4">
          <label className="flex flex-col gap-1 text-sm">
            <span className="text-neutral-600">الاسم</span>
            <input
              type="text"
              name="full_name"
              defaultValue={profile.full_name}
              required
              className="rounded border border-neutral-500 px-3 py-2"
            />
          </label>

          <label className="flex flex-col gap-1 text-sm">
            <span className="text-neutral-600">البريد الإلكتروني</span>
            <input
              type="email"
              name="email"
              defaultValue={profile.email ?? ""}
              className="rounded border border-neutral-500 px-3 py-2"
            />
          </label>

          <p className="text-sm text-neutral-600">
            الجوال <span className="money">{profile.phone}</span>
          </p>

          <button type="submit" className="rounded bg-neutral-900 px-4 py-2 text-white">
            حفظ
          </button>
        </form>
      </section>

      <section className="mb-10">
        <h2 className="mb-3 text-lg font-semibold">رقم الهوية</h2>

        {profile.national_id_verified ? (
          <p className="text-sm text-neutral-700">
            مسجَّل ومُثبَّت: <span className="money">{profile.national_id}</span>
          </p>
        ) : (
          <form action={saveNationalId} className="max-w-md space-y-4">
            {/*
              No pattern, no maxlength, no checksum. `apps/accounts/identity.py`
              owns what "valid" means, and a second definition here would refuse
              a number the backend accepts — or accept one it refuses — and tell
              a customer something untrue about their own identity.
            */}
            <label className="flex flex-col gap-1 text-sm">
              <span className="text-neutral-600">رقم الهوية أو الإقامة</span>
              <input
                type="text"
                name="national_id"
                inputMode="numeric"
                defaultValue={profile.national_id}
                required
                className="money rounded border border-neutral-500 px-3 py-2"
              />
            </label>

            <p className="text-sm text-neutral-500">
              يُسجَّل مرة واحدة. رقم صحيح لا يمكن تغييره بعدها.
            </p>

            <button type="submit" className="rounded bg-neutral-900 px-4 py-2 text-white">
              حفظ
            </button>
          </form>
        )}
      </section>

      <section className="mb-10">
        <h2 className="mb-3 text-lg font-semibold">تغيير رقم الجوال</h2>

        {/*
          خطوتان، ونموذجان اثنان — لأن الخطوة الثانية تحمل **رمزين معاً**:
          واحدٌ وصل الرقم الحالي وواحدٌ وصل الجديد. وذلك شرطُ العقد لا شكلُ
          الشاشة: تأكيدٌ برمزٍ واحد يعني رقماً أُثبت وآخرَ لم يُثبت، وهو ما
          يجعل سرقةَ حسابٍ بجوّالٍ ضائعٍ ممكنة.

          ولا تحقّقَ من صيغة الرقم هنا ولا `pattern`: النمطُ عند الخادم، ونسخةٌ
          ثانيةٌ منه تتفارق عنه يوم يتغيّر.
        */}
        <form action={startPhoneChange} className="max-w-md space-y-4">
          <label className="flex flex-col gap-1 text-sm">
            <span className="text-neutral-600">رقم الجوال الجديد</span>
            <input
              type="tel"
              name="new_phone"
              inputMode="numeric"
              placeholder="9665XXXXXXXX"
              required
              className="money rounded border border-neutral-500 px-3 py-2"
            />
          </label>
          <button type="submit" className="rounded bg-neutral-900 px-4 py-2 text-white">
            أرسل الرمزين
          </button>
        </form>

        <form action={confirmPhoneChange} className="mt-6 max-w-md space-y-4">
          <p className="text-sm text-neutral-600">
            بعد وصول الرمزين — واحدٌ إلى رقمك الحالي وواحدٌ إلى الجديد —
            أدخلهما معاً هنا.
          </p>
          <label className="flex flex-col gap-1 text-sm">
            <span className="text-neutral-600">رقم الجوال الجديد</span>
            <input
              type="tel"
              name="new_phone"
              inputMode="numeric"
              placeholder="9665XXXXXXXX"
              required
              className="money rounded border border-neutral-500 px-3 py-2"
            />
          </label>
          <div className="grid gap-4 sm:grid-cols-2">
            <label className="flex flex-col gap-1 text-sm">
              <span className="text-neutral-600">رمز الرقم الحالي</span>
              <input
                type="text"
                name="current_code"
                inputMode="numeric"
                required
                className="money rounded border border-neutral-500 px-3 py-2"
              />
            </label>
            <label className="flex flex-col gap-1 text-sm">
              <span className="text-neutral-600">رمز الرقم الجديد</span>
              <input
                type="text"
                name="new_code"
                inputMode="numeric"
                required
                className="money rounded border border-neutral-500 px-3 py-2"
              />
            </label>
          </div>
          <p className="text-sm text-neutral-500">
            بعد التغيير تُغلق جلستك، وتدخل بالرقم الجديد.
          </p>
          <button type="submit" className="rounded bg-neutral-900 px-4 py-2 text-white">
            تأكيد التغيير
          </button>
        </form>
      </section>

      {profile.account_type === "company" ? (
        <section>
          <h2 className="mb-3 text-lg font-semibold">
            بيانات الشركة والعنوان الوطني
            {company && !company.is_complete ? (
              <span className="ms-2 text-sm font-normal text-amber-700">— غير مكتملة</span>
            ) : null}
          </h2>

          <form action={saveCompany} className="grid max-w-2xl gap-4 sm:grid-cols-2">
            {COMPANY_FIELDS.map(([field, label]) => (
              <label key={field} className="flex flex-col gap-1 text-sm">
                <span className="text-neutral-600">{label}</span>
                <input
                  type="text"
                  name={field}
                  defaultValue={
                    (company as Record<string, unknown> | null)?.[field] as string | undefined ?? ""
                  }
                  className="rounded border border-neutral-500 px-3 py-2"
                />
              </label>
            ))}

            <div className="sm:col-span-2">
              <button
                type="submit"
                className="rounded bg-neutral-900 px-4 py-2 text-white"
              >
                حفظ بيانات الشركة
              </button>
            </div>
          </form>
        </section>
      ) : null}

      {/*
        A form, never a link: a `GET` that ends a session is a session ended by a
        prefetch, a crawler, or an image tag on somebody else's page.
      */}
      <form action={signOut} className="mt-12 border-t border-neutral-200 pt-6">
        <button type="submit" className="text-sm text-neutral-600 underline">
          تسجيل الخروج
        </button>
      </form>
    </PageShell>
  );
}
