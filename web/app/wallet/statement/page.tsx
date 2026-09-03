/**
 * كشف الحركات — القيود نفسها، لا ملخّصاً بجانبها. T1020.
 *
 * Read straight off the ledger entries: the amounts on this page *are* the
 * postings. `direction` and `bucket_label` and `description` are the server's
 * words, so a movement is described here exactly as it is described in the app
 * and in the console.
 *
 * The bucket filter is the other half of Article 1-6: the wallet's every number
 * links here with `?bucket=…`, and this page forwards that to the endpoint —
 * which validates it against the same tuple the ledger uses. An unknown bucket
 * is the backend's refusal, in its own sentence, rather than a filter this page
 * silently drops.
 */

import type { Metadata } from "next";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { Pagination } from "@/features/catalog/Pagination";
import { PageShell } from "@/features/shell/PageShell";
import { ApiError, api, request } from "@/lib/api";
import { amount, dateTime } from "@/lib/format";
import { readPaging, toParams } from "@/lib/paging";
import { authHeader, hasSession } from "@/lib/session";

export const metadata: Metadata = {
  title: "كشف الحركات",
  robots: { index: false, follow: false },
};

export const dynamic = "force-dynamic";

export default async function StatementPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const store = await cookies();
  if (!hasSession(store)) redirect("/sign-in");

  const headers = authHeader(store);
  const query = toParams(await searchParams);
  const { limit, offset } = readPaging(query);
  const bucket = query.get("bucket") ?? "";

  let page;
  try {
    page = await request(() =>
      api.GET("/api/v1/wallet/transactions/", {
        headers,
        params: { query: { limit, offset, ...(bucket ? { bucket } : {}) } },
      }),
    );
  } catch (error) {
    if (error instanceof ApiError && (error.status === 401 || error.status === 403)) {
      redirect("/sign-in");
    }
    throw error;
  }

  const entries = page.results ?? [];

  return (
    <PageShell title="كشف الحركات">
      <p className="-mt-4 mb-6 text-sm text-neutral-600">
        {bucket ? (
          <>
            مرشَّح على دلوٍ واحد ·{" "}
            <a href="/wallet/statement" className="underline">
              كل الحركات
            </a>
          </>
        ) : (
          "كل الحركات على حسابك، الأحدث أولاً."
        )}
      </p>

      {entries.length === 0 ? (
        <p className="py-12 text-center text-neutral-500">لا حركات.</p>
      ) : (
        <div className="overflow-x-auto rounded-lg border border-neutral-200 bg-white">
          <table className="w-full text-sm">
            <thead className="bg-neutral-50 text-neutral-600">
              <tr>
                <th className="p-3 text-start">التاريخ</th>
                <th className="p-3 text-start">الحركة</th>
                <th className="p-3 text-start">الدلو</th>
                <th className="p-3 text-start">المبلغ</th>
                <th className="p-3 text-start">البيان</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-neutral-200">
              {entries.map((entry) => (
                <tr key={entry.id}>
                  <td className="p-3 whitespace-nowrap">{dateTime(entry.occurred_at)}</td>
                  <td className="p-3">{entry.description}</td>
                  <td className="p-3">{entry.bucket_label}</td>
                  {/*
                    The sign is the server's `direction`, and the digits are the
                    server's string. Deriving "in or out" from the amount here
                    would be this page's own reading of a ledger convention that
                    is written down once, in `apps/money/models`.
                  */}
                  <td className="money p-3">
                    {entry.direction === "out" ? "−" : "+"} {amount(entry.amount)}
                  </td>
                  <td className="p-3 text-neutral-600">{entry.memo}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <Pagination
        query={query}
        total={page.count}
        limit={limit}
        offset={offset}
        path="/wallet/statement"
      />
    </PageShell>
  );
}
