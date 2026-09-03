/**
 * فاتورة واحدة، وسدادها — T1023.
 *
 * The methods offered are `invoice.payment_methods`, which the server computes
 * for **this** invoice. A list written here would be a second opinion about how
 * a purchase may be settled — and it would offer a card, which
 * `PaymentMethod` deliberately does not have: a purchase is settled from money
 * already deposited or by a bank transfer the bank confirms, never by a card
 * charge that can be reversed months later against a vehicle that has already
 * left the yard.
 *
 * `outstanding` is a server field, not `amount - amount_paid` worked out here.
 * The subtraction looks safe and is not: a cancelled invoice's outstanding is
 * zero regardless of what its columns say, and that rule lives on the model.
 */

import type { Metadata } from "next";
import { cookies } from "next/headers";
import { notFound, redirect } from "next/navigation";

import { payInvoice } from "@/features/wallet/actions";
import { Notice } from "@/features/shell/Notice";
import { PageShell } from "@/features/shell/PageShell";
import { ApiError, api, request } from "@/lib/api";
import { takeFlash } from "@/lib/flash";
import { amount, dateTime } from "@/lib/format";
import { readNumber } from "@/lib/paging";
import { authHeader, hasSession } from "@/lib/session";

export const metadata: Metadata = {
  title: "الفاتورة",
  robots: { index: false, follow: false },
};

export const dynamic = "force-dynamic";

//: One entry of `invoice.payment_methods`. The server sends the value *and* its
//: Arabic name, so there is no label table here at all — which is the same rule
//: the vehicle card follows: a translation kept in the web is a second
//: definition of what a value is called, and it goes stale silently.
type PaymentMethod = { method: string; label: string };

export default async function InvoicePage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const store = await cookies();
  if (!hasSession(store)) redirect("/sign-in");

  const { id } = await params;
  const invoiceId = readNumber(id, 0);
  const flash = takeFlash(store);
  const headers = authHeader(store);

  let invoice;
  try {
    invoice = await request(() =>
      api.GET("/api/v1/invoices/{id}/", { headers, params: { path: { id: invoiceId } } }),
    );
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) notFound();
    if (error instanceof ApiError && (error.status === 401 || error.status === 403)) {
      redirect("/sign-in");
    }
    throw error;
  }

  return (
    <PageShell title={`فاتورة ${invoice.number}`}>
      <Notice
        message={flash?.message ?? ""}
        tone={flash?.code === "invoice_paid" ? "info" : "error"}
      />

      <div className="max-w-md rounded-lg border border-neutral-200 bg-white p-4">
        <dl className="space-y-3 text-sm">
          <div className="flex justify-between gap-4">
            <dt className="text-neutral-500">الحالة</dt>
            <dd className="font-semibold">{invoice.state_label}</dd>
          </div>
          <div className="flex justify-between gap-4">
            <dt className="text-neutral-500">المبلغ</dt>
            <dd className="money">{amount(invoice.amount)}</dd>
          </div>
          <div className="flex justify-between gap-4">
            <dt className="text-neutral-500">المسدَّد</dt>
            <dd className="money">{amount(invoice.amount_paid)}</dd>
          </div>
          <div className="flex justify-between gap-4">
            <dt className="text-neutral-500">المتبقّي</dt>
            {/* The server's field. Not `amount - amount_paid`. */}
            <dd className="money font-semibold">{amount(invoice.outstanding)}</dd>
          </div>
          <div className="flex justify-between gap-4">
            <dt className="text-neutral-500">صدرت</dt>
            <dd>{dateTime(invoice.issued_at)}</dd>
          </div>
          {invoice.due_at ? (
            <div className="flex justify-between gap-4">
              <dt className="text-neutral-500">تستحق</dt>
              <dd>{dateTime(invoice.due_at)}</dd>
            </div>
          ) : null}
        </dl>
      </div>

      {invoice.payment_methods.length > 0 ? (
        <form
          action={payInvoice}
          className="mt-6 max-w-md rounded-lg border border-neutral-200 bg-white p-4"
        >
          <input type="hidden" name="invoice_id" value={invoice.id} />
          <h2 className="mb-3 font-semibold">السداد</h2>

          <div className="space-y-2">
            {(invoice.payment_methods as PaymentMethod[]).map((option) => (
              <label key={option.method} className="flex items-center gap-2 text-sm">
                <input type="radio" name="method" value={option.method} required />
                <span>{option.label}</span>
              </label>
            ))}
          </div>

          <button
            type="submit"
            className="mt-4 w-full rounded bg-neutral-900 px-4 py-2 text-white"
          >
            سدّد
          </button>
        </form>
      ) : (
        /*
          No methods offered means the server has none open for this invoice —
          it is already paid, or cancelled, or awaiting something. The page says
          so rather than showing a button that will be refused.
        */
        <p className="mt-6 text-sm text-neutral-600">لا توجد طريقة سداد متاحة الآن.</p>
      )}
    </PageShell>
  );
}
