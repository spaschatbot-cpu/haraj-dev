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
    /*
      **تصميمُ المالك** (٢٨ سبتمبر ٢٠٢٦) — بطاقتان باختيارٍ ظاهر وزرٌّ واحدٌ
      أسفلَ الشاشة، بدل بطاقتين كلٌّ منهما رابط. والخطواتُ فوقها خطواتُنا
      الخمس لا الثلاث التي في التصميم، والنصوصُ وقائعُ النظام: التصميمُ كان
      يعد بـ«النفاذ الوطني» و«إضافة ممثّلين» و«ترقية الحساب لاحقاً»، وليس في
      النظام منها شيء — ووعدٌ في شاشة التسجيل أوّلُ ما يُكذَّب.

      **استمارةُ `GET` لا جافاسكربت:** الاختيارُ `radio` حقيقيّ، والإرسالُ يفتح
      `?type=` نفسَه الذي كانت الروابطُ تفتحه. وهيئةُ البطاقة المختارة من
      `has-checked:` في CSS — تعمل بلا سطرٍ واحدٍ في المتصفّح.
    */
    return (
      <PageShell>
        <form method="get" action="/sign-in/complete" className="mx-auto max-w-lg pb-28">
          <Steps current={3} />

          <p className="mb-4 inline-flex items-center gap-2 rounded-full border border-ok-line bg-ok-surface px-3 py-1.5 text-label-md text-ok">
            <svg viewBox="0 0 24 24" aria-hidden="true" className="h-4 w-4" fill="currentColor">
              <path d="M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20zm-1.2 14.2-4-4 1.4-1.4 2.6 2.6 5.6-5.6 1.4 1.4-7 7z" />
            </svg>
            تم التحقق من رقم الجوال بنجاح
          </p>

          <h1 className="text-headline-lg">حدد نوع حسابك</h1>
          <p className="mt-1 mb-6 text-body-md text-on-surface-variant">
            اختر نوع الحساب لنطلب منك البيانات المناسبة له فقط.
          </p>

          <div className="space-y-4">
            <TypeOption
              value="individual"
              checked
              title="حساب فرد"
              subtitle="بالاسم ورقم الهوية أو الإقامة"
              detail="للمزايدين الأفراد. نطلب الاسم الكامل ورقم الهوية والمدينة."
              icon="M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM4 21a8 8 0 0 1 16 0"
              perks={[
                { text: "مزايدة بعد إيداع التأمين", tone: "ok" },
                { text: "بدون رسوم فتح حساب", tone: "plain" },
              ]}
            />
            <TypeOption
              value="company"
              title="شركة / مؤسسة"
              subtitle="بالسجل التجاري والرقم الضريبي"
              detail="للشركات ومعارض السيارات والمؤسسات. تصدر الفواتير باسم المنشأة وعنوانها الوطني."
              icon="M4 21V5l8-3 8 3v16M9 21v-5h6v5M8 9h2M14 9h2M8 13h2M14 13h2"
              perks={[
                { text: "فواتير ضريبية باسم المنشأة", tone: "accent" },
                { text: "باسم المفوّض ورقم هويته", tone: "plain" },
              ]}
            />
          </div>

          <p className="mt-5 flex items-start gap-2.5 rounded-2xl border border-secondary/20 bg-surface-low px-4 py-3.5 text-body-sm text-on-surface-variant">
            <svg viewBox="0 0 24 24" aria-hidden="true" className="mt-0.5 h-5 w-5 shrink-0 text-secondary" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
              <circle cx="12" cy="12" r="9" />
              <path d="M12 11v5M12 8h.01" />
            </svg>
            <span>
              <strong className="text-on-surface">بعدها:</strong> البيانات المطلوبة لنوع
              حسابك، ثم المستندات — اختياريّة، إلّا صورة الآيبان فهي شرط استرداد التأمين.
            </span>
          </p>

          {/*
            الزرُّ ثابتٌ أسفلَ الشاشة كما في التصميم: البطاقتان تطولان على الجوّال،
            والزرُّ الذي يختفي تحت الطيّ يُقرأ كصفحةٍ بلا مخرج.
          */}
          <div className="fixed inset-x-0 bottom-0 z-30 border-t border-outline-variant/60 bg-surface/95 px-4 py-3 backdrop-blur">
            <button
              type="submit"
              className="mx-auto flex h-14 w-full max-w-lg items-center justify-center gap-2 rounded-2xl bg-primary text-headline-sm text-on-primary shadow-lg shadow-primary/20 transition-opacity hover:opacity-90"
            >
              متابعة استكمال البيانات
              <svg viewBox="0 0 24 24" aria-hidden="true" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M19 12H5M11 6l-6 6 6 6" />
              </svg>
            </button>
          </div>
        </form>
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

type Perk = { text: string; tone: "ok" | "accent" | "plain" };

//: بطاقةُ نوعٍ بالهيئة التي اعتمدها المالك: أيقونةٌ في مربّع، وعنوانٌ وسطرٌ أزرق
//: ووصف، وتحتها ميزتان — والاختيارُ دائرةٌ في الطرف. والمختارةُ تُعرف من
//: `has-checked:` (الإطار والأيقونة يمتلئان بالأزرق) بلا جافاسكربت.
function TypeOption({
  value,
  checked,
  title,
  subtitle,
  detail,
  icon,
  perks,
}: {
  value: string;
  checked?: boolean;
  title: string;
  subtitle: string;
  detail: string;
  icon: string;
  perks: Perk[];
}) {
  return (
    <label className="group block cursor-pointer rounded-3xl border-2 border-outline-variant/60 bg-surface-lowest p-5 transition-all hover:border-secondary/40 has-checked:border-secondary has-checked:shadow-lg has-checked:shadow-secondary/10">
      <div className="flex items-start gap-4">
        <span className="flex h-16 w-16 shrink-0 items-center justify-center rounded-2xl bg-surface-container text-on-surface transition-colors group-has-checked:bg-secondary group-has-checked:text-on-secondary">
          <svg viewBox="0 0 24 24" aria-hidden="true" className="h-8 w-8" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
            <path d={icon} />
          </svg>
        </span>
        <span className="min-w-0 flex-1">
          <span className="block text-headline-md text-on-surface">{title}</span>
          <span className="mt-0.5 block text-label-md text-on-surface group-has-checked:text-secondary">{subtitle}</span>
          <span className="mt-1.5 block text-body-sm text-on-surface-variant">{detail}</span>
        </span>
        <input
          type="radio"
          name="type"
          value={value}
          defaultChecked={checked}
          required
          className="mt-1 h-6 w-6 shrink-0 cursor-pointer appearance-none rounded-full border-2 border-outline-variant bg-surface-lowest transition-all checked:border-[7px] checked:border-secondary focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-secondary"
        />
      </div>
      <span className="mt-4 flex flex-wrap items-center gap-x-3 gap-y-1 border-t border-outline-variant/50 pt-3 text-body-sm">
        {perks.map((perk, index) => (
          <span key={perk.text} className="inline-flex items-center gap-1.5">
            {index > 0 ? <span aria-hidden="true" className="me-1.5 h-1 w-1 rounded-full bg-outline-variant" /> : null}
            {perk.tone === "ok" ? (
              <svg viewBox="0 0 24 24" aria-hidden="true" className="h-4 w-4 text-ok" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M5 12.5l4.5 4.5L19 7.5" />
              </svg>
            ) : perk.tone === "accent" ? (
              <svg viewBox="0 0 24 24" aria-hidden="true" className="h-4 w-4 text-secondary" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M7 3h7l5 5v13H7zM14 3v5h5M10 13h6M10 17h6" />
              </svg>
            ) : null}
            <span className={perk.tone === "ok" ? "text-ok" : perk.tone === "accent" ? "text-secondary" : "text-on-surface-variant"}>
              {perk.text}
            </span>
          </span>
        ))}
      </span>
    </label>
  );
}
