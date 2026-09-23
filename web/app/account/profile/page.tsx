/**
 * تعديل البيانات — الاسمُ والبريد، ورقمُ الهوية، وبياناتُ المنشأة. T1012.
 *
 * نظيرُ `edit_profile.php` في v1، وصفحةٌ داخليّةٌ من «حسابي» (انظر
 * `app/account/page.tsx`). وكلُّ ما فيها يُقرأ من الملفّ الذي ردّه الخادم ولا
 * يُقرَّر هنا: ما يُعدَّل، وهل اكتملت المنشأة، وهل ما زال رقمُ الهوية قابلاً
 * للتغيير.
 *
 * `national_id_verified` أوضحُها: الحقلُ يُقفل حين يقول الخادمُ إن الرقمَ
 * مثبَّت، **وسببُ القفل جوابُه لا قاعدةٌ تعرفها الصفحة**. ولذلك يُقرأ العلَمُ
 * ولا يُشتقّ من كون `national_id` غيرَ فارغ: الاثنان واحدٌ اليوم، ويفترقان أوّلَ
 * مرّةٍ يُخزَّن فيها رقمٌ لم يُتحقَّق منه.
 */

import type { Metadata } from "next";

import { saveCompany, saveNationalId, saveProfile } from "@/features/account/actions";
import {
  CARD,
  CardHead,
  FIELD,
  LABEL,
  LABEL_TEXT,
  PRIMARY,
  Pill,
  SubpageHead,
  loadProfile,
} from "@/features/account/ui";
import { Notice } from "@/features/shell/Notice";
import { PageShell } from "@/features/shell/PageShell";
import { api, request } from "@/lib/api";
import { readFlash } from "@/lib/flash";

export const metadata: Metadata = {
  title: "تعديل البيانات",
  robots: { index: false, follow: false },
};

export const dynamic = "force-dynamic";

const COMPANY_FIELDS: Array<[string, string]> = [
  ["name", "اسم المنشأة"],
  ["representative_name", "اسم المفوّض / المسؤول"],
  ["commercial_register", "السجل التجاري"],
  ["vat_number", "الرقم الضريبي"],
  ["building_number", "رقم المبنى"],
  ["street", "الشارع"],
  ["district", "الحي"],
  ["city", "المدينة"],
  ["postal_code", "الرمز البريدي"],
];

export default async function ProfilePage() {
  const { store, headers, profile } = await loadProfile();
  const flash = readFlash(store);

  const company = profile.has_company_profile
    ? await request(() => api.GET("/api/v1/profile/company/", { headers }))
    : null;

  //: الحقولُ التي أقفلها الخادم، وسببُ كلٍّ بالعربيّة كما كتبه هو.
  const locked = new Map(profile.locked_fields.map((item) => [item.field, item.reason]));
  const isCompany = profile.account_type === "company";

  return (
    <PageShell>
      <div className="mx-auto max-w-3xl">
        <SubpageHead title="تعديل البيانات" />
        <Notice message={flash?.message ?? ""} tone={flash?.code === "saved" ? "info" : "error"} />

        <div className="space-y-6">
          {/* ── البيانات الأساسيّة ─────────────────────────────────────────── */}
          <section className={CARD}>
            <CardHead title="البيانات الأساسية" hint="الاسمُ يظهر على فواتيرك." />

            <dl className="mb-5 grid grid-cols-2 gap-3 sm:grid-cols-3">
              <Readonly label="رقم العميل" value={`#${profile.id}`} />
              <Readonly label="نوع الحساب" value={isCompany ? "شركة" : "فرد"} />
              <Readonly label="رقم الجوال" value={`+${profile.phone}`} ltr />
            </dl>

            <form action={saveProfile} className="grid gap-4 sm:grid-cols-2">
              <label className={LABEL}>
                <span className={LABEL_TEXT}>{isCompany ? "اسم المفوّض / المسؤول" : "الاسم الكامل"}</span>
                <input
                  type="text"
                  name="full_name"
                  defaultValue={profile.full_name}
                  required
                  disabled={locked.has("full_name")}
                  className={FIELD}
                />
                {locked.has("full_name") ? (
                  <span className="text-caption text-on-surface-variant">{locked.get("full_name")}</span>
                ) : null}
              </label>

              <label className={LABEL}>
                <span className={LABEL_TEXT}>البريد الإلكتروني</span>
                <input
                  type="email"
                  name="email"
                  dir="ltr"
                  defaultValue={profile.email ?? ""}
                  placeholder="name@example.com"
                  disabled={locked.has("email")}
                  className={`${FIELD} text-start`}
                />
                {locked.has("email") ? (
                  <span className="text-caption text-on-surface-variant">{locked.get("email")}</span>
                ) : null}
              </label>

              <div className="sm:col-span-2">
                <button type="submit" className={PRIMARY}>
                  حفظ البيانات
                </button>
              </div>
            </form>
          </section>

          {/* ── رقم الهوية ───────────────────────────────────────────────── */}
          <section className={CARD}>
            <CardHead
              title="رقم الهوية"
              hint="يُسجَّل مرّةً واحدة، ورقمٌ صحيحٌ لا يُغيَّر بعدها."
              badge={profile.national_id_verified ? <Pill tone="ok">مثبَّت</Pill> : <Pill tone="warn">ناقص</Pill>}
            />

            {profile.national_id_verified ? (
              <p className="money rounded-xl bg-surface-low px-4 py-3 text-headline-sm tracking-wider" dir="ltr">
                {profile.national_id}
              </p>
            ) : (
              <form action={saveNationalId} className="flex flex-col gap-3 sm:flex-row sm:items-end">
                {/*
                  No pattern, no maxlength, no checksum. `apps/accounts/identity.py`
                  owns what "valid" means, and a second definition here would refuse
                  a number the backend accepts — or accept one it refuses — and tell
                  a customer something untrue about their own identity.
                */}
                <label className={`${LABEL} flex-1`}>
                  <span className={LABEL_TEXT}>رقم الهوية أو الإقامة</span>
                  <input
                    type="text"
                    name="national_id"
                    inputMode="numeric"
                    dir="ltr"
                    defaultValue={profile.national_id}
                    required
                    className={`${FIELD} money text-start tracking-wider`}
                  />
                </label>
                <button type="submit" className={PRIMARY}>
                  تسجيل الرقم
                </button>
              </form>
            )}
          </section>

          {/* ── المنشأة والعنوان الوطني ───────────────────────────────────── */}
          {isCompany ? (
            <section className={CARD}>
              <CardHead
                title="بيانات المنشأة والعنوان الوطني"
                hint="تُطبع على فواتير المنشأة كما تُكتب هنا."
                badge={
                  company ? (
                    company.is_complete ? <Pill tone="ok">مكتملة</Pill> : <Pill tone="warn">غير مكتملة</Pill>
                  ) : null
                }
              />

              <form action={saveCompany} className="grid gap-4 sm:grid-cols-2">
                {COMPANY_FIELDS.map(([field, label]) => (
                  <label key={field} className={LABEL}>
                    <span className={LABEL_TEXT}>{label}</span>
                    <input
                      type="text"
                      name={field}
                      defaultValue={
                        (company as Record<string, unknown> | null)?.[field] as string | undefined ?? ""
                      }
                      className={FIELD}
                    />
                  </label>
                ))}

                <div className="sm:col-span-2">
                  <button type="submit" className={PRIMARY}>
                    حفظ بيانات المنشأة
                  </button>
                </div>
              </form>
            </section>
          ) : null}
        </div>
      </div>
    </PageShell>
  );
}

function Readonly({ label, value, ltr }: { label: string; value: string; ltr?: boolean }) {
  return (
    <div className="rounded-xl bg-surface-low px-3 py-2.5">
      <dt className="text-caption text-on-surface-variant">{label}</dt>
      <dd className="money truncate text-label-md" dir={ltr ? "ltr" : undefined}>
        {value}
      </dd>
    </div>
  );
}
