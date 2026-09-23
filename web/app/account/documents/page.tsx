/**
 * المستندات — صفحةٌ داخليّةٌ من «حسابي»: السجلُّ التجاريّ والشهادةُ الضريبيّة
 * والهويّةُ والآيبان.
 *
 * وُلدت من اختبار المسار الكامل على `haraj.spas.sa` (٢٤ سبتمبر ٢٠٢٦): العميلُ
 * سدّد فاتورتَه فعاد تأمينُه متاحاً، فطلب استردادَه فرُدّ بـ«صورة الآيبان مطلوبة
 * قبل طلب الاسترداد. ارفعها من ملفّك» — ولم يكن في الموقع ملفٌّ يُرفع فيه.
 *
 * والقائمةُ من الخادم (`GET /api/v1/profile/documents/`): **الأربعةُ دائماً**،
 * والغائبُ منها `file: null`. فالشاشةُ تجيب «ماذا ينقصني؟» لا «ماذا رفعت؟».
 * ولا رابطَ لفتح الملفّ المرفوع: الوثيقةُ صورةُ هويّةٍ أو آيبان، ورابطٌ يفتحها
 * في المتصفّح يُحفَظ في سجلّه ويُنسخ — يكفي العميلَ أن يعرف أنها وصلت ومتى.
 */

import type { Metadata } from "next";

import { uploadDocument } from "@/features/account/actions";
import { CARD, FIELD, LABEL, LABEL_TEXT, PRIMARY, Pill, SubpageHead, loadProfile } from "@/features/account/ui";
import { Notice } from "@/features/shell/Notice";
import { PageShell } from "@/features/shell/PageShell";
import { api, request } from "@/lib/api";
import { readFlash } from "@/lib/flash";
import { dateTime } from "@/lib/format";

export const metadata: Metadata = {
  title: "المستندات",
  robots: { index: false, follow: false },
};

export const dynamic = "force-dynamic";

//: لماذا يُطلب كلٌّ منها — سطرٌ تحت اسمه. والآيبانُ أوّلُها سبباً: بدونه لا استرداد.
const WHY: Record<string, string> = {
  iban: "مطلوبةٌ قبل طلب استرداد التأمين — يُحوَّل الاسترداد إلى هذا الحساب.",
  id: "صورة الهوية أو الإقامة.",
  cr: "للحسابات التجاريّة — تُطبع بيانات المنشأة على الفاتورة.",
  tax: "للحسابات المسجّلة في ضريبة القيمة المضافة.",
};

export default async function DocumentsPage() {
  const { store, headers } = await loadProfile();
  const flash = readFlash(store);

  const documents = await request(() => api.GET("/api/v1/profile/documents/", { headers }));

  return (
    <PageShell>
      <div className="mx-auto max-w-3xl">
        <SubpageHead title="المستندات" hint="صورة واضحة (JPG أو PNG)، حتى ١٠ ميجابايت." />
        <Notice message={flash?.message ?? ""} tone={flash?.code === "saved" ? "info" : "error"} />

        <ul className="space-y-4">
          {documents.map((doc) => (
            <li key={doc.kind} className={CARD}>
              <div className="mb-4 flex items-start justify-between gap-3">
                <div>
                  <h2 className="text-headline-sm">{doc.label}</h2>
                  {WHY[doc.kind] ? (
                    <p className="text-body-sm text-on-surface-variant">{WHY[doc.kind]}</p>
                  ) : null}
                </div>
                {doc.file ? <Pill tone="ok">مرفوعة</Pill> : <Pill tone="warn">غير مرفوعة</Pill>}
              </div>

              {doc.file ? (
                <p className="mb-4 rounded-xl bg-surface-low px-4 py-3 text-body-sm text-on-surface-variant">
                  رُفعت {dateTime(doc.uploaded_at)}
                  {doc.uploaded_by_staff ? " — رفعها موظّفٌ عنك" : ""}
                  {doc.note ? ` · ${doc.note}` : ""}
                </p>
              ) : null}

              <form action={uploadDocument} className="flex flex-col gap-3 sm:flex-row sm:items-end">
                <input type="hidden" name="kind" value={doc.kind} />
                <label className={`${LABEL} flex-1`}>
                  <span className={LABEL_TEXT}>{doc.file ? "استبدال الصورة" : "الصورة"}</span>
                  <input
                    type="file"
                    name="file"
                    accept="image/jpeg,image/png,image/webp"
                    required
                    className={`${FIELD} py-2 file:me-3 file:rounded-md file:border-0 file:bg-surface-container file:px-3 file:py-1 file:text-label-md`}
                  />
                </label>
                <button type="submit" className={PRIMARY}>
                  ارفع
                </button>
              </form>
            </li>
          ))}
        </ul>
      </div>
    </PageShell>
  );
}
