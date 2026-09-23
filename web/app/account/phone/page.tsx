/**
 * تغيير رقم الجوال — صفحةٌ داخليّةٌ من «حسابي». T604.
 *
 * كانت نموذجين مفتوحين دائماً في صفحة الحساب يأخذان نصفَها لفعلٍ يُفعَل مرّةً
 * في عمر الحساب. وصارت صفحتَها، بخطوتين مرقَّمتين.
 *
 * خطوتان، ونموذجان اثنان — لأن الخطوة الثانية تحمل **رمزين معاً**: واحدٌ وصل
 * الرقم الحالي وواحدٌ وصل الجديد. وذلك شرطُ العقد لا شكلُ الشاشة: تأكيدٌ برمزٍ
 * واحد يعني رقماً أُثبت وآخرَ لم يُثبت، وهو ما يجعل سرقةَ حسابٍ بجوّالٍ ضائعٍ
 * ممكنة.
 *
 * ولا تحقّقَ من صيغة الرقم هنا ولا `pattern`: النمطُ عند الخادم، ونسخةٌ ثانيةٌ
 * منه تتفارق عنه يوم يتغيّر.
 */

import type { Metadata } from "next";

import { confirmPhoneChange, startPhoneChange } from "@/features/account/actions";
import { CARD, CardHead, FIELD, LABEL, LABEL_TEXT, PRIMARY, SubpageHead, loadProfile } from "@/features/account/ui";
import { Notice } from "@/features/shell/Notice";
import { PageShell } from "@/features/shell/PageShell";
import { readFlash } from "@/lib/flash";

export const metadata: Metadata = {
  title: "تغيير رقم الجوال",
  robots: { index: false, follow: false },
};

export const dynamic = "force-dynamic";

export default async function PhonePage() {
  const { store, profile } = await loadProfile();
  const flash = readFlash(store);

  return (
    <PageShell>
      <div className="mx-auto max-w-2xl">
        <SubpageHead title="تغيير رقم الجوال" hint="يصل رمزٌ إلى رقمك الحالي وآخرُ إلى الجديد، وتُدخلهما معاً." />
        <Notice message={flash?.message ?? ""} tone={flash?.code === "saved" ? "info" : "error"} />

        <p className="mb-6 rounded-xl bg-surface-low px-4 py-3 text-body-sm text-on-surface-variant">
          رقمك الحالي{" "}
          <span className="money text-label-md text-on-surface" dir="ltr">
            +{profile.phone}
          </span>
        </p>

        <div className="space-y-6">
          <section className={CARD}>
            <CardHead title="١ — اطلب الرمزين" />
            <form action={startPhoneChange} className="flex flex-col gap-3 sm:flex-row sm:items-end">
              <label className={`${LABEL} flex-1`}>
                <span className={LABEL_TEXT}>رقم الجوال الجديد</span>
                <input
                  type="tel"
                  name="new_phone"
                  inputMode="numeric"
                  dir="ltr"
                  placeholder="9665XXXXXXXX"
                  required
                  className={`${FIELD} money text-start`}
                />
              </label>
              <button type="submit" className={PRIMARY}>
                أرسل الرمزين
              </button>
            </form>
          </section>

          <section className={CARD}>
            <CardHead title="٢ — أدخل الرمزين معاً" hint="بعد التغيير تُغلق جلستك، وتدخل بالرقم الجديد." />
            <form action={confirmPhoneChange} className="space-y-4">
              <label className={LABEL}>
                <span className={LABEL_TEXT}>رقم الجوال الجديد</span>
                <input
                  type="tel"
                  name="new_phone"
                  inputMode="numeric"
                  dir="ltr"
                  placeholder="9665XXXXXXXX"
                  required
                  className={`${FIELD} money text-start`}
                />
              </label>
              <div className="grid grid-cols-2 gap-3">
                <label className={LABEL}>
                  <span className={LABEL_TEXT}>رمز الرقم الحالي</span>
                  <input
                    type="text"
                    name="current_code"
                    inputMode="numeric"
                    dir="ltr"
                    required
                    className={`${FIELD} money text-center tracking-widest`}
                  />
                </label>
                <label className={LABEL}>
                  <span className={LABEL_TEXT}>رمز الرقم الجديد</span>
                  <input
                    type="text"
                    name="new_code"
                    inputMode="numeric"
                    dir="ltr"
                    required
                    className={`${FIELD} money text-center tracking-widest`}
                  />
                </label>
              </div>
              <button type="submit" className={PRIMARY}>
                تأكيد التغيير
              </button>
            </form>
          </section>
        </div>
      </div>
    </PageShell>
  );
}
