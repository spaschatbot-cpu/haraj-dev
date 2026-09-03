/**
 * زرّ الشحن — T1021.
 *
 * No amount field. The figure is `deposit_amount_for`'s and the server refuses
 * a request that names its own — a box here would be a box whose value is
 * discarded, which is worse than no box because it looks like a choice.
 *
 * A form and not a link: starting a top-up writes a `PaymentIntent`, and a `GET`
 * that writes is a row created by a prefetch or a crawler.
 */

import { startTopup } from "@/features/wallet/actions";

export function TopupButton({ auctionId }: { auctionId?: number }) {
  return (
    <form action={startTopup} className="mt-6">
      {auctionId === undefined ? null : (
        <input type="hidden" name="auction" value={auctionId} />
      )}
      <button
        type="submit"
        className="rounded bg-neutral-900 px-4 py-2 text-sm text-white"
      >
        شحن التأمين بالبطاقة
      </button>
      <p className="mt-2 text-xs text-neutral-500">
        المبلغ يحدّده النظام. يُفتح لك موقع الدفع، ويتحرّك رصيدك حين تؤكّد البوابة
        الدفع للخادم — لا عند عودتك من الرابط.
      </p>
    </form>
  );
}
