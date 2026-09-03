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
import { PageShell } from "@/features/shell/PageShell";
import { ApiError, api, request } from "@/lib/api";
import { amount, count, dateTime } from "@/lib/format";
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
        <p className="py-12 text-center text-neutral-500">لا مشتريات بعد.</p>
      ) : (
        <ul className="divide-y divide-neutral-200 rounded-lg border border-neutral-200 bg-white">
          {purchases.map((purchase) => {
            const invoice = purchase.invoice as
              | { id?: number; number?: string; outstanding?: string }
              | null;
            return (
              <li key={purchase.id} className="flex flex-wrap items-center gap-4 p-4">
                <div className="min-w-0 grow">
                  <p className="font-medium">
                    {purchase.make} {purchase.model} {count(purchase.year)}
                  </p>
                  <p className="mt-1 text-sm text-neutral-600">
                    لوت {count(purchase.lot_number)} · رست في{" "}
                    {dateTime(purchase.awarded_at)}
                  </p>
                </div>

                <div className="text-end">
                  <p className="money font-semibold">{amount(purchase.awarded_price)} ريال</p>
                  {invoice?.id ? (
                    <Link href={`/invoices/${invoice.id}`} className="text-sm underline">
                      الفاتورة {invoice.number}
                    </Link>
                  ) : (
                    <span className="text-sm text-neutral-500">لا فاتورة بعد</span>
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
