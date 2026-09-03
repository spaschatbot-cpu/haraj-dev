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

import { withdrawBid } from "@/features/bidding/actions";
import { Pagination } from "@/features/catalog/Pagination";
import { Notice } from "@/features/shell/Notice";
import { PageShell } from "@/features/shell/PageShell";
import { ApiError, api, request } from "@/lib/api";
import { takeFlash } from "@/lib/flash";
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

  const flash = takeFlash(store);
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
    <PageShell title="مزايداتي">
      <Notice
        message={flash?.message ?? ""}
        tone={flash?.code === "bid_withdrawn" ? "info" : "error"}
      />

      {bids.length === 0 ? (
        <p className="py-12 text-center text-neutral-500">لم تزايد على شيء بعد.</p>
      ) : (
        <ul className="divide-y divide-neutral-200 rounded-lg border border-neutral-200 bg-white">
          {bids.map((bid) => (
            <li key={bid.id} className="flex flex-wrap items-center gap-4 p-4">
              <div className="min-w-0 grow">
                <Link href={`/vehicles/${bid.vehicle_id}`} className="font-medium hover:underline">
                  {bid.vehicle_title}
                </Link>
                <p className="mt-1 text-sm text-neutral-600">
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
                <p className="text-sm text-neutral-500">
                  {bid.is_withdrawn
                    ? "مسحوبة"
                    : bid.is_superseded
                      ? "استُبدلت بمزايدة أحدث"
                      : "قائمة"}
                </p>
              </div>

              {!bid.is_withdrawn && !bid.is_superseded ? (
                <form action={withdrawBid}>
                  <input type="hidden" name="bid_id" value={bid.id} />
                  <button type="submit" className="text-sm text-red-700 underline">
                    سحب
                  </button>
                </form>
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
