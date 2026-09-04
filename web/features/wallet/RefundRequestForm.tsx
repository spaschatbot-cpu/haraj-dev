/**
 * طلب استرداد — T1022.
 *
 * The customer names the amount and the server decides everything else. There is
 * no `max` here derived from the available balance and no client-side comparison:
 * one open request per customer is a **database constraint**, not a check a
 * screen performs, and the reason is a v1 incident — ten requests each passed
 * the same check against the same untouched balance, and accounting was
 * instructed to pay out ten times the money.
 *
 * The available figure is shown beside the box because it is useful to know, not
 * because it is being enforced.
 */

import { requestRefund } from "@/features/wallet/actions";
import { amount } from "@/lib/format";

export function RefundRequestForm({ available }: { available: string }) {
  return (
    <section className="mt-12 rounded-lg border border-neutral-200 bg-white p-4">
      <h2 className="mb-1 font-semibold">طلب استرداد</h2>
      <p className="mb-4 text-sm text-neutral-600">
        المتاح الآن <span className="money">{amount(available)}</span>. الطلب لا
        يحرّك رصيدك؛ المحاسبة تنفّذه ويظهر في حركاتك عند التنفيذ.
      </p>

      <form action={requestRefund} className="flex flex-wrap items-end gap-3">
        <label className="flex flex-col gap-1 text-sm">
          <span className="text-neutral-600">المبلغ</span>
          <input
            type="text"
            name="amount"
            inputMode="decimal"
            required
            className="money rounded border border-neutral-500 px-3 py-2"
          />
        </label>

        <button type="submit" className="rounded bg-neutral-900 px-4 py-2 text-white">
          أرسل الطلب
        </button>
      </form>
    </section>
  );
}
