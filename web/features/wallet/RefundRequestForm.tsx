/**
 * طلب استرداد، والطلبُ القائمُ فوقه — T1022.
 *
 * **والوديعةُ وحدةٌ لا رصيد**: عشرةُ آلافٍ بالضبط، ويُسترَدّ مضاعفُها كاملاً.
 * والخادمُ يحرسها (`whole_deposits_in`)؛ والخانةُ هنا تقول القاعدةَ سلفاً
 * وتبدأ بوحدةٍ واحدة، فلا يكتب العميلُ ٥٬٠٠٠ ثم يُردّ. ولا `max` مشتقٌّ من
 * الرصيد ولا مقارنةٌ في المتصفّح: «طلبٌ واحدٌ مفتوح» قيدٌ في القاعدة لا فحصٌ
 * تجريه شاشة — والسببُ حادثةُ v1: عشرةُ طلباتٍ مرّت على الفحص نفسِه أمام
 * الرصيد نفسِه، فصدرت تعليماتٌ بصرف عشرة أضعاف المال.
 *
 * **والطلبُ القائم يُعرَض ومعه زرُّ إلغائه.** كان لا يُعرَض أصلاً: يضغط العميلُ
 * «أرسل» فيُقال له «لديك طلبٌ قائم» وهو لا يراه في الصفحة، ولا يملك إنهاءه.
 * وv1 يعرض آخرَ عشرة طلباتٍ وزرَّ إلغاء.
 */

import { cancelRefund, requestRefund } from "@/features/wallet/actions";
import { amount } from "@/lib/format";

type OpenRefund = {
  reference: string;
  amount: string;
  state_label?: string;
  iban?: string;
};

export function RefundRequestForm({
  available,
  unit,
  open,
  iban,
}: {
  available: string;
  unit: string;
  open?: OpenRefund | null;
  iban?: string;
}) {
  return (
    <section id="refund" className="mt-12 scroll-mt-24 rounded-lg border border-neutral-200 bg-white p-4">
      <h2 className="mb-1 font-semibold">طلب استرداد</h2>

      {open ? (
        <div className="mb-4 rounded border border-amber-300 bg-amber-50 p-3">
          <p className="text-sm">
            لديك طلبٌ قائم بمبلغ{" "}
            <span className="money font-semibold">{amount(open.amount)}</span>
            {open.state_label ? ` · ${open.state_label}` : null}.
          </p>
          {open.iban ? (
            <p className="mt-1 text-xs text-neutral-700">
              إلى الآيبان <code dir="ltr">{open.iban}</code>
            </p>
          ) : null}
          <p className="mt-1 text-xs text-neutral-700">
            وتأمينك محجوزٌ له فلا تُقبل منك مزايدةٌ حتى يُنفَّذ أو يُلغى.
          </p>
          <form action={cancelRefund} className="mt-3">
            <input type="hidden" name="reference" value={open.reference} />
            <button
              type="submit"
              className="rounded border border-neutral-500 px-3 py-1.5 text-sm"
            >
              ألغِ الطلب
            </button>
          </form>
        </div>
      ) : (
        <>
          <p className="mb-1 text-sm text-neutral-600">
            المتاح الآن <span className="money">{amount(available)}</span>. الطلب لا
            يحرّك رصيدك؛ المحاسبة تنفّذه ويظهر في حركاتك عند التنفيذ.
          </p>
          <p className="mb-4 text-sm text-neutral-600">
            وديعة التأمين وحدةٌ لا تُجزَّأ:{" "}
            <span className="money">{amount(unit)}</span> للوديعة الواحدة —
            يُسترَدّ مضاعفُها كاملاً لا مبلغٌ جزئيّ.
          </p>

          <form action={requestRefund} className="flex flex-wrap items-end gap-3">
            <label className="flex flex-col gap-1 text-sm">
              <span className="text-neutral-600">المبلغ</span>
              <input
                type="text"
                name="amount"
                inputMode="decimal"
                defaultValue={unit}
                required
                className="money rounded border border-neutral-500 px-3 py-2"
              />
            </label>

            {/*
              **رقم الآيبان — وكان غائباً.** v1 يطلبه في استمارته مع الصورة
              (`refunds_requests.iban_account`)، وكانت عندنا الصورةُ وحدَها:
              فصرفُ عشرة آلافٍ يبدأ بقراءة رقمٍ من صورةٍ ثمّ كتابتِه بيد، وهو
              الموضعُ الذي يُخطئ فيه رقمٌ واحد. وعمودُ «الآيبان» في شاشة
              المالية كان يعرض الملاحظةَ في مكانه.

              ويُملأ سلفاً بآيبان الطلب السابق إن وُجد، ويُطبَّع في الخادم:
              البنوكُ تعرضه مجزّأً بمسافاتٍ كلَّ أربعة وهو ما يُنسَخ فعلاً.
            */}
            <label className="flex flex-col gap-1 text-sm">
              <span className="text-neutral-600">رقم الآيبان</span>
              <input
                type="text"
                name="iban"
                defaultValue={iban ?? ""}
                placeholder="SA00 0000 0000 0000 0000 0000"
                required
                dir="ltr"
                className="money w-72 rounded border border-neutral-500 px-3 py-2 text-left"
              />
            </label>

            <button type="submit" className="rounded bg-neutral-900 px-4 py-2 text-white">
              أرسل الطلب
            </button>
          </form>
        </>
      )}
    </section>
  );
}
