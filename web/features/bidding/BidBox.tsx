/**
 * صندوق المزايدة — نموذج، وجوابُ الخادم فوقه. T1014 / T1015.
 *
 * A plain form posting to a server action, like every other write in this app:
 * it works with scripting off, and the amount never passes through a number.
 *
 * What this component deliberately does not do
 * --------------------------------------------
 * It does not decide whether the visitor may bid. There is no check on the
 * vehicle's state, no comparison against a deposit, no minimum worked out from
 * anything — so there is no branch here that could refuse somebody the server
 * would have allowed, or offer a box to somebody it will refuse. J7 is that the
 * refusal a customer sees is the *server's* enumerated reason, identical to the
 * app's, and the only way to guarantee it is to have nothing here that produces
 * one.
 *
 * The visible consequence is that an unqualified customer gets the box and then
 * a sentence. That is on purpose: a hidden box tells somebody nothing, and «لا
 * يوجد تأمين متاح» tells them exactly what to do next.
 *
 * The confirmation step (T1015)
 * -----------------------------
 * When the server answers `lower_needs_confirm`, this renders with the amount
 * kept, the standing bid quoted **from the refusal's own detail**, and an
 * explicit checkbox. Quoting the number the refusal carried rather than
 * re-reading it matters: the figure the customer is asked to confirm below has
 * to be the figure the refusal was about, and a fresh read a moment later can
 * legitimately be a different one — at which point the confirmation would be
 * consent to something that was never asked.
 */

import { placeBid } from "@/features/bidding/actions";
import type { Flash } from "@/lib/flash";

export function BidBox({
  vehicleId,
  flash,
}: {
  vehicleId: number;
  flash: Flash | null;
}) {
  const needsConfirmation = flash?.code === "lower_needs_confirm";
  const requested =
    typeof flash?.detail?.requested === "string" ? flash.detail.requested : "";
  const standing =
    typeof flash?.detail?.standing === "string" ? flash.detail.standing : "";

  return (
    <form
      action={placeBid}
      className="mt-8 rounded-lg border border-neutral-200 bg-white p-4"
    >
      <input type="hidden" name="vehicle_id" value={vehicleId} />

      <h2 className="mb-3 font-semibold">المزايدة</h2>

      <label className="flex flex-col gap-1 text-sm">
        <span className="text-neutral-600">مبلغ المزايدة</span>
        <input
          type="text"
          name="amount"
          inputMode="decimal"
          required
          defaultValue={requested}
          className="money rounded border border-neutral-300 px-3 py-2 text-lg"
        />
      </label>

      {needsConfirmation ? (
        <div className="mt-4 rounded border border-amber-300 bg-amber-50 p-3 text-sm">
          <p className="mb-2 text-amber-900">
            مزايدتك القائمة <span className="money">{standing}</span> ريال، والمبلغ
            الجديد أقل منها.
          </p>
          {/*
            Unchecked, and required to submit. A pre-ticked box is not a
            confirmation — it is the first attempt with an extra field, which is
            precisely the accident the two-step exists to stop (F3).
          */}
          <label className="flex items-center gap-2 text-amber-900">
            <input type="checkbox" name="confirm_lower" value="1" required />
            <span>نعم، أريد خفض مزايدتي.</span>
          </label>
        </div>
      ) : null}

      <button
        type="submit"
        className="mt-4 w-full rounded bg-neutral-900 px-4 py-2 text-white"
      >
        {needsConfirmation ? "تأكيد الخفض" : "زايد"}
      </button>

      <p className="mt-3 text-xs text-neutral-500">
        المزايدة تحجز تأميناً على المزاد. الخادم يقرّر الأهلية والحد الأدنى.
      </p>
    </form>
  );
}
