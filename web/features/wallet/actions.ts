"use server";

/**
 * أفعال المحفظة — الشحن وطلب الاسترداد. T1021 / T1022.
 *
 * Neither names an amount. That is the point of both.
 *
 * * **الشحن:** the customer says *which auction* they are depositing for, and
 *   `money.services.deposit_amount_for` decides how much. A request that named
 *   its own amount is refused at the edge — the figure is the platform's, and a
 *   web that sent one would be proposing a deposit the rules did not set.
 * * **الاسترداد:** the amount is the customer's to name, and everything about
 *   whether it may be paid out is the server's: one open request per customer
 *   is a database constraint, not a check a screen performs. In v1 ten requests
 *   each passed the same check against the same untouched balance and instructed
 *   accounting to pay out ten times the money.
 */

import { redirect } from "next/navigation";
import { cookies } from "next/headers";

import { ApiError, api, messageOf, request } from "@/lib/api";
import { setFlash } from "@/lib/flash";
import { authHeader } from "@/lib/session";

async function refuse(error: unknown, back: string): Promise<never> {
  const store = await cookies();
  setFlash(store, {
    code: error instanceof ApiError ? error.code : "",
    message: messageOf(error),
    ...(error instanceof ApiError ? { detail: error.detail } : {}),
  });
  redirect(back);
}

/**
 * Start a card top-up and go to where its state can be read.
 *
 * The intent row exists before the customer reaches any gateway, and its
 * `reference` is the only thing that says whose money a returning payment is.
 * The gateway does not carry our user id, and v1 tried to recover it from
 * whatever came back in the query string — which is both losable and forgeable.
 */
export async function startTopup(form: FormData): Promise<void> {
  const auctionRaw = String(form.get("auction") ?? "").trim();
  const auction = Number.parseInt(auctionRaw, 10);

  const headers = await authHeader(await cookies());

  let intent;
  try {
    intent = await request(() =>
      api.POST("/api/v1/wallet/topups/", {
        headers,
        // No amount. `deposit_amount_for` decides it, and an endpoint that let a
        // client name one would let a client name a deposit.
        body: Number.isFinite(auction) ? { auction } : {},
      }),
    );
  } catch (error) {
    return refuse(error, "/wallet");
  }

  redirect(`/wallet/topup/${encodeURIComponent(intent.reference)}`);
}

/** Ask for free insurance back. Asking moves no money; the payout is Odoo's. */
export async function requestRefund(form: FormData): Promise<void> {
  // Straight from the form to the body as text. Reading it as a number here
  // would put a refund through a binary float on its way to a decimal ledger.
  const refundAmount = String(form.get("amount") ?? "").trim();

  const headers = await authHeader(await cookies());

  try {
    await request(() =>
      api.POST("/api/v1/wallet/refund-requests/", {
        headers,
        body: { amount: refundAmount },
      }),
    );
  } catch (error) {
    return refuse(error, "/wallet");
  }

  const store = await cookies();
  setFlash(store, {
    code: "refund_requested",
    message: "سُجّل طلب الاسترداد. تُنفّذه المحاسبة ويظهر في حركاتك عند تنفيذه.",
  });
  redirect("/wallet");
}

/**
 * Pay an invoice.
 *
 * The method comes from the invoice's own `payment_methods` — the server says
 * which are open for this invoice, and the screen offers those. A list written
 * in the web would offer a card, and a purchase is never settled by a card
 * charge that can be reversed months later against a vehicle that has already
 * left the yard (`PaymentMethod` has no card member, deliberately).
 */
export async function payInvoice(form: FormData): Promise<void> {
  const invoiceId = Number(form.get("invoice_id"));
  const method = String(form.get("method") ?? "");
  const back = `/invoices/${invoiceId}`;

  const headers = await authHeader(await cookies());

  try {
    await request(() =>
      api.POST("/api/v1/invoices/{id}/pay/", {
        params: { path: { id: invoiceId } },
        headers,
        body: { method: method as "balance" | "bank_transfer" },
      }),
    );
  } catch (error) {
    return refuse(error, back);
  }

  const store = await cookies();
  setFlash(store, { code: "invoice_paid", message: "سُجّل السداد." });
  redirect(back);
}
