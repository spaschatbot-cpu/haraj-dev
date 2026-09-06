"use client";

/**
 * «تفاصيل المزايدة» — نموذج، وجوابُ الخادم فوقه. T1014 / T1015، وتكافؤ v1.
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
 * الأربعة أسطر التي يعرضها v1
 * ============================
 * قِيست من الإنتاج الحيّ (`specs/011-customer-web/v1-card-parity.md`): رسوم
 * إدارية · الرسوم + الضريبة (15%) · السعر · السعر + الضريبة (15%).
 *
 * **ولا سطر منها يُحسب هنا.** الأولان يصلان مع الكرت محسوبَين
 * (`admin_fee`, `admin_fee_with_vat`)، والرابع يُطلَب من
 * `POST /api/v1/bids/quote/` مع كل تغيير. في v1 كان الحساب في المتصفّح؛ عندنا
 * `ops/checks/web_money_is_never_computed.mjs` يمنعه ومعه حقّ — نسختان من
 * معادلة الضريبة تختلفان يوم تتغيّر النسبة، وتختلفان **صامتتَين**، فيقرأ
 * العميل رقماً ويدفع غيره.
 *
 * وثمن ذلك رحلةٌ إلى الخادم لكل توقّف عن الكتابة. مقصود: النسبة يقولها
 * `money.tax_added_to` وحدها.
 *
 * وحين لا يجيب الخادم يُكتب «—» لا رقمٌ قديم: مبلغٌ لا يخصّ ما في الحقل الآن
 * أسوأ من لا مبلغ.
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

import { useEffect, useState } from "react";

import { placeBid } from "@/features/bidding/actions";
import type { Flash } from "@/lib/flash";

//: ما يُعرض قبل أن يُكتب شيء، وهو ما يعرضه v1 حرفياً («٠ ر.س»). نصٌّ ثابت لا
//: ناتجُ حساب: صفرُ ضريبةٍ على لا شيء ليس قراراً يحتاج خادماً.
const NOTHING_YET = "0.00";

//: ريثما يجيب الخادم. نقاطٌ لا رقمٌ سابق — ولا صفرٌ أيضاً: صفرٌ **جواب**،
//: و«لم يصل بعد» ليس جواباً.
const WAITING = "…";

//: لم يُجب، أو رفض المبلغ. «—» تقول «لا رقم هنا» ولا تدّعي غيره.
const UNKNOWN = "—";

//: يُنتظر توقّفُ الكتابة قبل السؤال. بلا هذا يذهب طلبٌ لكل حرف، ويصل جوابُ
//: «4» بعد جواب «45» فيُكتب الأقدم فوق الأحدث.
const SETTLE = 300;

export function BidBox({
  vehicleId,
  flash,
  /** «رسوم إدارية» كما أرسلها الخادم — نصّ عشري، لا يُلمَس. */
  adminFee,
  /** «الرسوم + الضريبة (15%)»، محسوبةً على الخادم. */
  adminFeeWithVat,
}: {
  vehicleId: number;
  flash: Flash | null;
  adminFee: string;
  adminFeeWithVat: string;
}) {
  const needsConfirmation = flash?.code === "lower_needs_confirm";
  const requested =
    typeof flash?.detail?.requested === "string" ? flash.detail.requested : "";
  const standing =
    typeof flash?.detail?.standing === "string" ? flash.detail.standing : "";

  const [typed, setTyped] = useState(requested);

  //: الجواب **ومعه نصّه**. حفظُ الرقم وحده يعني أن رقماً صحيحاً عن «450»
  //: يبقى معروضاً بينما في الحقل «4500» — رقمٌ حقيقيّ تحت مبلغٍ آخر، وهو
  //: أسوأ من لا رقم لأنه يُقرأ ويُصدَّق.
  const [quote, setQuote] = useState<{ for: string; total: string } | null>(null);

  const written = typed.trim();

  useEffect(() => {
    if (written === "") return;

    //: يُلغى الطلب السابق حين يتغيّر الحقل، فلا يصل جوابُ «4» بعد جواب «45».
    const stop = new AbortController();
    const timer = setTimeout(async () => {
      try {
        const answer = await fetch("/api/backend/api/v1/bids/quote/", {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({ amount: written }),
          signal: stop.signal,
        });
        const total = answer.ok
          ? ((await answer.json()) as { total: string }).total
          : UNKNOWN;
        setQuote({ for: written, total });
      } catch {
        //: انقطاعٌ أو إلغاء. الملغى لا يُكتب: مكانه سيأخذه طلبٌ أحدث.
        if (!stop.signal.aborted) setQuote({ for: written, total: UNKNOWN });
      }
    }, SETTLE);

    return () => {
      clearTimeout(timer);
      stop.abort();
    };
  }, [written]);

  //: مشتقٌّ في الرندرة لا محفوظٌ في حالة: ما دام الجواب ليس عن النصّ المكتوب
  //: الآن فهو ليس جواباً، ولا يُعرض.
  const withVat =
    written === "" ? NOTHING_YET : quote?.for === written ? quote.total : WAITING;

  return (
    <form
      action={placeBid}
      className="mt-8 rounded-lg border border-neutral-200 bg-white p-4"
    >
      <input type="hidden" name="vehicle_id" value={vehicleId} />

      <h2 className="mb-3 font-semibold">تفاصيل المزايدة</h2>

      <dl className="mb-4 divide-y divide-neutral-200 border-y border-neutral-200 text-sm">
        <div className="flex justify-between gap-4 py-2">
          <dt className="text-neutral-500">رسوم إدارية</dt>
          <dd className="money tabular-nums">{adminFee} ر.س</dd>
        </div>
        <div className="flex justify-between gap-4 py-2">
          <dt className="text-neutral-500">الرسوم + الضريبة (15%)</dt>
          <dd className="money tabular-nums">{adminFeeWithVat} ر.س</dd>
        </div>
      </dl>

      <label className="flex flex-col gap-1 text-sm">
        <span className="text-neutral-600">السعر</span>
        <input
          type="text"
          name="amount"
          inputMode="decimal"
          required
          value={typed}
          onChange={(event) => setTyped(event.target.value)}
          className="money rounded border border-neutral-500 px-3 py-2 text-lg"
        />
      </label>

      <p className="mt-3 flex justify-between gap-4 text-sm">
        <span className="text-neutral-500">السعر + الضريبة (15%)</span>
        {/*
          `aria-live` لأن الرقم يتغيّر بلا أن يضغط أحد شيئاً: من لا يرى الشاشة
          لا يعرف أن سطراً تحت الحقل تحرّك.
        */}
        <span className="money tabular-nums font-semibold" aria-live="polite">
          {withVat} ر.س
        </span>
      </p>

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
        {needsConfirmation ? "تأكيد الخفض" : "دخول المزاد"}
      </button>

      <p className="mt-3 text-xs text-neutral-500">
        المزايدة تحجز تأميناً على المزاد. الخادم يقرّر الأهلية والحد الأدنى.
      </p>
    </form>
  );
}
