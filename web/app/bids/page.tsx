/**
 * مزايداتي — والسحب من عندها. T1016 / T1017.
 *
 * Every bid the customer has placed, with its state as the server records it:
 * `is_superseded` when they have since bid again on the same car, and
 * `is_withdrawn` when they took it back. Both are read, never derived — "the
 * newest bid on this car is the standing one" is a rule, it lives in
 * `apps/bidding`, and a list that worked it out from timestamps would disagree
 * with the ledger the first time two bids shared a second.
 *
 * Withdrawal is offered on a bid the server has not marked withdrawn or
 * superseded, and the *result* is still the server's: the auction may have
 * ended between the render and the click, and the refusal that comes back is
 * the sentence shown. The button is an offer, not a promise.
 */

import type { Metadata } from "next";
import Link from "next/link";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { placeBid, withdrawBid } from "@/features/bidding/actions";
import { Pagination } from "@/features/catalog/Pagination";
import { Notice } from "@/features/shell/Notice";
import { PageShell } from "@/features/shell/PageShell";
import { ApiError, api, request } from "@/lib/api";
import { readFlash } from "@/lib/flash";
import { amount, count, dateTime } from "@/lib/format";
import { readPaging, toParams } from "@/lib/paging";
import { authHeader, hasSession } from "@/lib/session";

export const metadata: Metadata = {
  title: "مزايداتي",
  robots: { index: false, follow: false },
};

export const dynamic = "force-dynamic";

export default async function BidsPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const store = await cookies();
  if (!hasSession(store)) redirect("/sign-in");

  const flash = readFlash(store);
  const headers = authHeader(store);
  const query = toParams(await searchParams);
  const { limit, offset } = readPaging(query);

  let page;
  try {
    page = await request(() =>
      api.GET("/api/v1/bids/mine/", { headers, params: { query: { limit, offset } } }),
    );
  } catch (error) {
    if (error instanceof ApiError && (error.status === 401 || error.status === 403)) {
      redirect("/sign-in");
    }
    throw error;
  }

  const bids = page.results ?? [];

  return (
    <PageShell title="مزايداتي" art="bids">
      <Notice
        message={flash?.message ?? ""}
        tone={flash?.code === "bid_withdrawn" ? "info" : "error"}
      />

      {bids.length === 0 ? (
        <p className="py-12 text-center text-on-surface-variant">لم تزايد على شيء بعد.</p>
      ) : (
        <ul className="divide-y divide-outline-variant rounded-lg border border-outline-variant bg-white">
          {bids.map((bid) => (
            <li key={bid.id} className="flex flex-wrap items-center gap-4 p-4">
              <div className="min-w-0 grow">
                <Link href={`/vehicles/${bid.vehicle_id}`} className="font-medium hover:underline">
                  {bid.vehicle_title}
                </Link>
                <p className="mt-1 text-sm text-on-surface-variant">
                  لوت {count(bid.lot_number)} · {dateTime(bid.placed_at)}
                </p>
              </div>

              <div className="text-end">
                <p className="money text-lg font-semibold">{amount(bid.amount)} ريال</p>
                {/*
                  The state as the server records it. «قائمة» is the absence of
                  both flags rather than a third field — which is the backend's
                  own model, and inventing a third state here would be a fourth
                  opinion about what a live bid is.
                */}
                <p className="text-sm text-on-surface-variant">
                  {bid.is_withdrawn
                    ? "مسحوبة"
                    : bid.is_superseded
                      ? "استُبدلت بمزايدة أحدث"
                      : "قائمة"}
                </p>
              </div>

              {/*
                **تعديلٌ وسحبٌ — وكلاهما يختفي بانتهاء المزاد.**

                v1 يضع الاثنين في الصفّ و«تظهر فقط أثناء نشاط المزاد وتختفي
                فور انتهائه» (تعليقُ `my_bids.php` بحرفه). وكان عندنا «سحب»
                وحدَه، ويُعرض على مزادٍ منتهٍ: زرٌّ يقود إلى رفضٍ مؤكَّد بعد
                أن صار الخادمُ يرفض السحبَ بعد الإغلاق — وزرٌّ ميّتٌ أسوأُ من
                زرٍّ غائب.

                و«can_change» جوابُ الخادم لا حسابُ الشاشة: المرحلةُ من
                المحرّك نفسِه الذي يقرؤه `withdraw_bid`، فلا تقول الشاشةُ
                شيئاً ويقول الخادمُ غيرَه.

                والتعديلُ **مزايدةٌ جديدة** على المركبة نفسِها لا مسارٌ ثانٍ:
                الخفضُ يحتاج تأكيداً كما في صفحة المركبة، والدفترُ يرى ما
                يراه هناك.
              */}
              {bid.can_change ? (
                <div className="flex flex-wrap items-center gap-3">
                  <form action={placeBid} className="flex items-center gap-2">
                    <input type="hidden" name="vehicle_id" value={bid.vehicle_id} />
                    <input type="hidden" name="back" value="bids" />
                    <label className="sr-only" htmlFor={`amount-${bid.id}`}>
                      المبلغ الجديد
                    </label>
                    <input
                      id={`amount-${bid.id}`}
                      type="text"
                      name="amount"
                      inputMode="decimal"
                      defaultValue={bid.amount}
                      required
                      className="money w-32 rounded border border-outline px-2 py-1 text-sm"
                    />
                    <button type="submit" className="text-sm underline">
                      تعديل
                    </button>
                  </form>

                  <form action={withdrawBid}>
                    <input type="hidden" name="bid_id" value={bid.id} />
                    <button type="submit" className="text-sm text-error underline">
                      سحب
                    </button>
                  </form>
                </div>
              ) : null}
            </li>
          ))}
        </ul>
      )}

      <Pagination
        query={query}
        total={page.total}
        limit={limit}
        offset={offset}
        path="/bids"
      />
    </PageShell>
  );
}
