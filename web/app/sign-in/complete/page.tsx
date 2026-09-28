/**
 * أكمل تسجيلك — ما بعد الرمز لكلّ حسابٍ ينقصه شيء، جديداً كان أو منقولاً ناقصاً.
 *
 * طلبُ المالك (٢٨ سبتمبر ٢٠٢٦): «أوّل حاجة أدخل الرقم، بعد كده الـverification،
 * بعد كده يعمل detection: لو موجود يدخّله على طول، لو بياناته ناقصة يدخّله صفحة
 * يكمّل البيانات، لو جديد ينشئ حسابه ويديله كل الـdata المطلوبة… ما تعمليش تسجيل
 * ناقص داتا». وهذه الصفحةُ هي الفرعان الأخيران معاً، لأن الجوابَ فيهما واحد:
 * «هذا ما ينقصك» — والخادمُ هو من يقوله (`registration_missing`).
 *
 * **والبناءُ بناءُ v1** (`log2/index.php`): جوال ← رمز ← **نوعُ الحساب** ←
 * **البيانات** ← المستندات. والحقولُ حقولُه (`ClientProfileGuard`):
 *
 * * الفرد: الاسمُ الكامل، ورقمُ الهويّة، والمدينة.
 * * الشركة: اسمُ المفوّض، واسمُ المنشأة، والسجلّ، والرقمُ الضريبيّ، والعنوانُ
 *   الوطنيُّ كلُّه — وزِيد رقمُ الهويّة لأن بوّابةَ المزايدة في v2 تطلبه.
 *
 * والمستنداتُ بعدها في «المستندات» — اختياريّةٌ في v1 كما هنا، إلّا أن صورةَ
 * الآيبان شرطُ الاسترداد، فالرسالةُ تقول ذلك.
 *
 * بلا جافاسكربت: الخطوتان رابطٌ واستمارة، والنوعُ في الرابط (`?type=`).
 */

import type { Metadata } from "next";
import Link from "next/link";
import { redirect } from "next/navigation";

import { completeRegistration } from "@/features/account/actions";
import { CARD, FIELD, LABEL, LABEL_TEXT, PRIMARY, loadProfile } from "@/features/account/ui";
import { Notice } from "@/features/shell/Notice";
import { PageShell } from "@/features/shell/PageShell";
import { api, request } from "@/lib/api";
import { readFlash } from "@/lib/flash";

export const metadata: Metadata = {
  title: "أكمل تسجيلك",
  robots: { index: false, follow: false },
};

export const dynamic = "force-dynamic";

type Field = {
  name: string;
  label: string;
  inputMode?: "numeric" | "text";
  maxLength?: number;
  dir?: "ltr";
  hint?: string;
};

//: حقولُ المنشأة والعنوان الوطنيّ بترتيب v1، ومفاتيحُها مفاتيحُ الخادم نفسُها —
//: فالخطأُ العائدُ من الخادم (`detail.vat_number`) يقع تحت خانته بلا ترجمة.
const COMPANY_FIELDS: Field[] = [
  { name: "name", label: "اسم المنشأة" },
  { name: "commercial_register", label: "السجل التجاري", inputMode: "numeric", maxLength: 10, dir: "ltr", hint: "١٠ أرقام" },
  { name: "vat_number", label: "الرقم الضريبي", inputMode: "numeric", maxLength: 15, dir: "ltr", hint: "١٥ رقماً يبدأ وينتهي بـ3" },
  { name: "city", label: "المدينة" },
  { name: "district", label: "الحي" },
  { name: "street", label: "الشارع" },
  { name: "building_number", label: "رقم المبنى", inputMode: "numeric", maxLength: 4, dir: "ltr", hint: "٤ أرقام" },
  { name: "additional_number", label: "الرقم الإضافي", inputMode: "numeric", maxLength: 4, dir: "ltr", hint: "٤ أرقام" },
  { name: "postal_code", label: "الرمز البريدي", inputMode: "numeric", maxLength: 5, dir: "ltr", hint: "٥ أرقام" },
];

export default async function CompleteRegistrationPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const { store, headers, profile } = await loadProfile();

  // مكتملٌ؟ فلا شيء هنا له — يدخل على طول (الفرعُ الأوّل من طلب المالك).
  if (profile.registration_missing.length === 0) redirect("/account");

  const flash = readFlash(store);
  const errors = (flash?.detail ?? {}) as Record<string, unknown>;
  const errorOf = (field: string): string => {
    const value = errors[field];
    if (Array.isArray(value)) return String(value[0] ?? "");
    return typeof value === "string" ? value : "";
  };

  const params = await searchParams;
  const asked = params.type === "company" || params.type === "individual" ? params.type : null;
  const type = asked ?? (profile.account_type === "company" ? "company" : "individual");

  /*
    خطوةُ «نوع الحساب» للحساب الجديد وحده: بلا اسمٍ وبلا منشأة، ولم يختر بعد.
    ومن جاء ناقصاً من v1 يعرف نوعَه، فيدخل البياناتِ مباشرةً — سؤالُه «فردٌ أم
    شركة؟» وهو شركةٌ منذ سنتين سؤالٌ لا جوابَ له إلا الضجر.
  */
  const fresh = !profile.full_name.trim() && !profile.has_company_profile;
  if (fresh && !asked) {
    return (
      <PageShell>
        <div className="mx-auto max-w-lg">
          <Steps current={3} />
          <h1 className="mb-1 text-headline-lg">نوع الحساب</h1>
          <p className="mb-6 text-body-sm text-on-surface-variant">
            تحقّقنا من رقمك. اختر نوع الحساب لنطلب البيانات المناسبة.
          </p>
          <div className="grid grid-cols-2 gap-4">
            <TypeCard href="/sign-in/complete?type=individual" title="فرد" detail="بالاسم ورقم الهوية" icon="M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM4 21a8 8 0 0 1 16 0" />
            <TypeCard href="/sign-in/complete?type=company" title="شركة / مؤسسة" detail="بالسجل التجاري والرقم الضريبي" icon="M4 21V5l8-3 8 3v16M9 21v-5h6v5M8 9h2M14 9h2M8 13h2M14 13h2" />
          </div>
        </div>
      </PageShell>
    );
  }

  const company =
    type === "company" && profile.has_company_profile
      ? await request(() => api.GET("/api/v1/profile/company/", { headers })).catch(() => null)
      : null;
  const companyValue = (field: string) =>
    String(((company as Record<string, unknown> | null)?.[field] as string | undefined) ?? "");

  const missing = new Set(profile.registration_missing.map((gap) => gap.field));

  return (
    <PageShell>
      <div className="mx-auto max-w-2xl">
        <Steps current={4} />
        <h1 className="mb-1 text-headline-lg">أكمل تسجيلك</h1>
        <p className="mb-6 text-body-sm text-on-surface-variant">
          ينقص حسابك: {profile.registration_missing.map((gap) => gap.label).join("، ")}.
        </p>

        <Notice message={flash?.message ?? ""} tone={flash?.code === "saved" ? "info" : "error"} />

        <form action={completeRegistration} className={`${CARD} space-y-5`}>
          <input type="hidden" name="type" value={type} />
          <input type="hidden" name="current_full_name" value={profile.full_name} />

          <div className="flex items-center justify-between gap-3 rounded-xl bg-surface-low px-4 py-3">
            <span className="text-body-sm text-on-surface-variant">
              نوع الحساب: <strong className="text-on-surface">{type === "company" ? "شركة / مؤسسة" : "فرد"}</strong>
            </span>
            {fresh ? (
              <Link href="/sign-in/complete" className="text-label-md text-secondary hover:underline">
                تغيير
              </Link>
            ) : null}
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <Input
              field={{ name: "full_name", label: type === "company" ? "اسم المفوّض / المسؤول" : "الاسم الكامل", hint: "الاسم كما في الهوية — بلا أرقام" }}
              value={profile.full_name}
              error={errorOf("full_name")}
              required
            />

            {missing.has("national_id") ? (
              <Input
                field={{ name: "national_id", label: "رقم الهوية أو الإقامة", inputMode: "numeric", maxLength: 10, dir: "ltr", hint: "١٠ أرقام — يُسجَّل مرّةً واحدة" }}
                value={profile.national_id}
                error={errorOf("national_id")}
                required
              />
            ) : null}

            {type === "individual" ? (
              <Input field={{ name: "city", label: "المدينة" }} value={profile.city} error={errorOf("city")} required />
            ) : null}
          </div>

          {type === "company" ? (
            <fieldset className="space-y-4 border-t border-outline-variant/60 pt-5">
              <legend className="mb-2 text-headline-sm">بيانات المنشأة والعنوان الوطني</legend>
              <p className="-mt-1 text-body-sm text-on-surface-variant">تُطبع على فواتير المنشأة كما تُكتب هنا.</p>
              <div className="grid gap-4 sm:grid-cols-2">
                {COMPANY_FIELDS.map((field) => (
                  <Input
                    key={field.name}
                    field={field}
                    value={companyValue(field.name) || (field.name === "city" ? profile.city : "")}
                    error={errorOf(field.name)}
                    required
                  />
                ))}
              </div>
            </fieldset>
          ) : null}

          <button type="submit" className={`${PRIMARY} w-full`}>
            حفظ ومتابعة
          </button>
          <p className="text-center text-caption text-on-surface-variant">
            بالمتابعة فإنك توافق على الشروط والأحكام وسياسة الخصوصية.
          </p>
        </form>
      </div>
    </PageShell>
  );
}

function Input({ field, value, error, required }: { field: Field; value: string; error: string; required?: boolean }) {
  return (
    <label className={LABEL}>
      <span className={LABEL_TEXT}>{field.label}</span>
      <input
        type="text"
        name={field.name}
        defaultValue={value}
        required={required}
        inputMode={field.inputMode}
        maxLength={field.maxLength}
        dir={field.dir}
        aria-invalid={error ? true : undefined}
        className={`${FIELD} ${field.dir ? "money text-start" : ""} ${error ? "border-critical focus:border-critical focus:ring-critical/20" : ""}`}
      />
      {error ? (
        <span className="text-caption text-critical">{error}</span>
      ) : field.hint ? (
        <span className="text-caption text-on-surface-variant">{field.hint}</span>
      ) : null}
    </label>
  );
}

//: خطواتُ v1 الخمس، والحاليّةُ مضاءة — ليعرف العميلُ أين هو وكم بقي.
function Steps({ current }: { current: number }) {
  const labels = ["الجوال", "الرمز", "نوع الحساب", "البيانات", "المستندات"];
  return (
    <ol className="mb-6 flex items-center gap-2" aria-label="خطوات التسجيل">
      {labels.map((label, index) => {
        const step = index + 1;
        const state = step < current ? "done" : step === current ? "now" : "next";
        return (
          <li key={label} className="flex flex-1 flex-col items-center gap-1">
            <span
              aria-current={state === "now" ? "step" : undefined}
              className={`flex h-8 w-8 items-center justify-center rounded-full text-label-sm ${
                state === "now"
                  ? "bg-primary text-on-primary"
                  : state === "done"
                    ? "bg-secondary-fixed text-on-secondary-fixed"
                    : "bg-surface-container text-on-surface-variant"
              }`}
            >
              {step}
            </span>
            <span className="text-caption text-on-surface-variant">{label}</span>
          </li>
        );
      })}
    </ol>
  );
}

function TypeCard({ href, title, detail, icon }: { href: string; title: string; detail: string; icon: string }) {
  return (
    <Link
      href={href}
      className="flex flex-col items-center gap-3 rounded-2xl border border-outline-variant/60 bg-surface-lowest p-6 text-center transition-colors hover:border-secondary hover:bg-surface-low"
    >
      <span className="flex h-14 w-14 items-center justify-center rounded-2xl bg-surface-container text-secondary">
        <svg viewBox="0 0 24 24" aria-hidden="true" className="h-7 w-7" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
          <path d={icon} />
        </svg>
      </span>
      <span className="text-headline-sm">{title}</span>
      <span className="text-body-sm text-on-surface-variant">{detail}</span>
    </Link>
  );
}
