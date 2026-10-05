/**
 * المشتريات والفواتير — T1023.
 *
 * What was awarded to this customer, and the invoice behind each. Both come from
 * the server whole: `awarded_price` is the accepted offer as recorded at
 * settlement, never the highest bid recomputed — that recomputation is the v1
 * bug the console's partner screen was rebuilt around (T807), and a car awarded
 * to the second bidder would show the first bidder's number here for exactly
 * the same reason.
 */

import type { Metadata } from "next";
import Link from "next/link";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { Pagination } from "@/features/catalog/Pagination";
import { InvoiceStateChip, type InvoiceView } from "@/features/money/invoice";
import { PageShell } from "@/features/shell/PageShell";
import { ApiError, api, request } from "@/lib/api";
import { amount, dateTime } from "@/lib/format";
import { readPaging, toParams } from "@/lib/paging";
import { authHeader, hasSession } from "@/lib/session";

export const metadata: Metadata = {
  title: "مشترياتي",
  robots: { index: false, follow: false },
};

export const dynamic = "force-dynamic";

export default async function PurchasesPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const store = await cookies();
  if (!hasSession(store)) redirect("/sign-in");

  const headers = authHeader(store);
  const query = toParams(await searchParams);
  const { limit, offset } = readPaging(query);

  let page;
  try {
    page = await request(() =>
      api.GET("/api/v1/purchases/", { headers, params: { query: { limit, offset } } }),
    );
  } catch (error) {
    if (error instanceof ApiError && (error.status === 401 || error.status === 403)) {
      redirect("/sign-in");
    }
    throw error;
  }

  const purchases = page.results ?? [];

  return (
    <PageShell title="مشترياتي">
      {purchases.length === 0 ? (
        <p className="py-12 text-center text-on-surface-variant">لا مشتريات بعد.</p>
      ) : (
        <ul className="divide-y divide-outline-variant rounded-lg border border-outline-variant bg-white">
          {purchases.map((purchase) => {
            const invoice = purchase.invoice as InvoiceView | null;
            return (
              <li key={purchase.id} className="flex flex-wrap items-center gap-4 p-4">
                <div className="min-w-0 grow">
                  <p className="font-medium">
                    {purchase.make} {purchase.model} <span className="tnum">{purchase.year}</span>
                  </p>
                  <p className="mt-1 text-sm text-on-surface-variant">
                    لوت <span className="tnum">{purchase.lot_number}</span> · رست في{" "}
                    {dateTime(purchase.awarded_at)}
                  </p>
                </div>

                <div className="text-end">
                  <p className="money font-semibold">{amount(purchase.awarded_price)} ريال</p>
                  {invoice?.id ? (
                    <>
                      {/* حالةُ الفاتورة والمسدَّد والمتبقّي على الكرت نفسه، كما في v1
                          (`menu/purchases.php`) — كان العميلُ يفتح كلَّ فاتورةٍ ليعرف
                          أيُّها ما زال عليه. */}
                      <p className="mt-1">
                        <InvoiceStateChip invoice={invoice} />
                      </p>
                      <p className="mt-1 text-sm text-on-surface-variant">
                        المسدَّد <span className="money">{amount(invoice.amount_paid)}</span> ·
                        المتبقّي{" "}
                        <span className="money font-semibold">{amount(invoice.outstanding)}</span>
                      </p>
                      <Link href={`/invoices/${invoice.id}`} className="text-sm underline">
                        الفاتورة {invoice.number}
                      </Link>
                    </>
                  ) : (
                    <span className="text-sm text-on-surface-variant">لا فاتورة بعد</span>
                  )}
                </div>
              </li>
            );
          })}
        </ul>
      )}

      <Pagination
        query={query}
        total={page.count}
        limit={limit}
        offset={offset}
        path="/purchases"
      />
    </PageShell>
  );
}
