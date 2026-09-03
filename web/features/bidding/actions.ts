"use server";

/**
 * المزايدة من الويب — نداءٌ واحد، وجوابٌ يُعرَض. T1014–T1016.
 *
 * This file is the shortest one in the feature and that is the point. It reads a
 * form, calls the endpoint the Flutter app calls, and renders what comes back.
 * There is:
 *
 * * **no eligibility check** — not "does he have a deposit", not "is the auction
 *   still running", not "is this his own car". `apps/bidding/eligibility.py` is
 *   the single gate (its own CI guard refuses a second reader of those facts),
 *   and J7 is the criterion that an unqualified customer is refused with *the
 *   same enumerated reason, word for word*, in both channels. The way to
 *   guarantee that is to have nothing here that could produce a different one;
 * * **no minimum computed** — the floor is the server's number;
 * * **no arithmetic on the amount** — it is a string from the form to the body,
 *   and `ops/checks/web_money_is_never_computed.mjs` keeps it that way.
 *
 * Lowering (T1015)
 * ----------------
 * A lower bid is a real feature of a sealed auction and also what a fat finger
 * produces, so the backend refuses the first attempt with `lower_needs_confirm`
 * and accepts a second carrying `confirm_lower`. This layer does not decide when
 * that applies — it forwards the flag when the customer ticked the box, and the
 * two-step exists because the *server* asked for it. A web that inferred "this
 * looks lower, add the flag" would walk straight through the guard F3 exists to
 * be.
 */

import { redirect } from "next/navigation";
import { cookies } from "next/headers";

import { ApiError, api, messageOf, request } from "@/lib/api";
import { setFlash } from "@/lib/flash";
import { authHeader } from "@/lib/session";

async function refuse(error: unknown, back: string): Promise<never> {
  const store = await cookies();

  setFlash(store, {
    // The enumerated reason itself — `no_deposit`, `unpaid_dues`,
    // `lower_needs_confirm` — because `BidRefused.code` is the reason and not a
    // generic "refused". A screen can say something specific about each one, and
    // that is exactly why the backend made the set closed.
    code: error instanceof ApiError ? error.code : "",
    message: messageOf(error),
    ...(error instanceof ApiError ? { detail: error.detail } : {}),
  });
  redirect(back);
}

/**
 * Place a bid on one vehicle.
 *
 * `amount` goes to the body as the string it was typed as. Reading it as a
 * number here and sending it back would put every amount through a binary
 * float on the way to a ledger that is decimal all the way down.
 */
export async function placeBid(form: FormData): Promise<void> {
  const vehicleId = Number(form.get("vehicle_id"));
  const amount = String(form.get("amount") ?? "").trim();
  const confirmLower = form.get("confirm_lower") === "1";
  const back = `/vehicles/${vehicleId}`;

  const headers = await authHeader(await cookies());

  try {
    await request(() =>
      api.POST("/api/v1/vehicles/{id}/bids/", {
        params: { path: { id: vehicleId } },
        headers,
        // Always sent, never conditionally omitted: the contract declares the
        // field as required-with-a-default, and a body that sometimes carries it
        // is a body whose meaning depends on which branch built it.
        body: { amount, confirm_lower: confirmLower },
      }),
    );
  } catch (error) {
    return refuse(error, back);
  }

  const store = await cookies();
  setFlash(store, { code: "bid_placed", message: "سُجّلت مزايدتك." });
  redirect(back);
}

/**
 * Withdraw a standing bid.
 *
 * Whether it may still be withdrawn is the server's answer — the auction may
 * have ended, the car may have been awarded — and `not_your_bid` is its answer
 * to somebody trying to withdraw a bid that is not theirs. Neither is checked
 * here: an ownership check in a screen is a check that is absent from every
 * other way of reaching the endpoint.
 */
export async function withdrawBid(form: FormData): Promise<void> {
  const bidId = Number(form.get("bid_id"));

  const headers = await authHeader(await cookies());

  try {
    await request(() =>
      api.POST("/api/v1/bids/{id}/withdraw/", {
        params: { path: { id: bidId } },
        headers,
      }),
    );
  } catch (error) {
    return refuse(error, "/bids");
  }

  const store = await cookies();
  setFlash(store, { code: "bid_withdrawn", message: "سُحبت مزايدتك." });
  redirect("/bids");
}
