/**
 * قائمة المزادات — مرندَرة في الخادم، بترقيم حقيقي. T1007.
 *
 * A server component: the HTML that leaves this route already contains the
 * auction titles, so `curl` sees them, a crawler indexes them, and a visitor on
 * a slow connection reads them before any script has run. That is the acceptance
 * criterion literally — *طلب بلا جافاسكربت يُرجع أسماء المزادات في HTML* — and
 * it is the reason the phase chose Next over Flutter Web at all.
 *
 * The list is not filtered here. `apps/auctions/listing.py` already decides
 * which auctions a caller may see, and a `state` filter written in this file
 * would be a second opinion about visibility (rule 3).
 */

import type { Metadata } from "next";

import { AuctionCard, type Auction } from "@/features/catalog/AuctionCard";
import { Pagination } from "@/features/catalog/Pagination";
import { PageShell } from "@/features/shell/PageShell";
import { api, request } from "@/lib/api";
import { readPaging, toParams } from "@/lib/paging";

export const metadata: Metadata = {
  title: "المزادات",
  description: "المزادات القائمة والقادمة، ومركبات كل مزاد.",
};

//: Rendered per request, never cached at build time: an auction's state and its
//: open-vehicle count change during the day, and a page cached at build time
//: would tell a visitor an auction is still running an hour after it closed.
export const dynamic = "force-dynamic";

export default async function AuctionsPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const query = toParams(await searchParams);
  const { limit, offset } = readPaging(query);

  const page = await request(() =>
    api.GET("/api/v1/auctions/", { params: { query: { limit, offset } } }),
  );

  const auctions = (page.results ?? []) as Auction[];

  return (
    <PageShell title="المزادات">
      {auctions.length === 0 ? (
        <p className="py-12 text-center text-neutral-500">لا مزادات معروضة الآن.</p>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2">
          {auctions.map((auction) => (
            <AuctionCard key={auction.id} auction={auction} />
          ))}
        </div>
      )}

      <Pagination
        query={query}
        total={page.total}
        limit={limit}
        offset={offset}
        path="/auctions"
      />
    </PageShell>
  );
}
