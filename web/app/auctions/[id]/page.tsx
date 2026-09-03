/**
 * مركبات المزاد، بالبحث والترشيح في الخادم. T1008.
 *
 * The filters are a `GET` form and the filtering happens at
 * `/api/v1/auctions/{id}/vehicles/`, which is the endpoint the Flutter app
 * calls with the same parameters. That is the acceptance criterion's second
 * half: for one set of criteria the two channels return the same cars, because
 * there is one implementation of "which cars match" and neither channel has a
 * copy of it.
 */

import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { type Auction } from "@/features/catalog/AuctionCard";
import { VehicleFilters, FILTER_FIELDS } from "@/features/catalog/VehicleFilters";
import { VehicleGrid, type Vehicle } from "@/features/catalog/VehicleCard";
import { Pagination } from "@/features/catalog/Pagination";
import { PageShell } from "@/features/shell/PageShell";
import { ApiError, api, request } from "@/lib/api";
import { dateTime, count } from "@/lib/format";
import { readNumber, readPaging, toParams } from "@/lib/paging";

export const dynamic = "force-dynamic";

type Params = { params: Promise<{ id: string }> };
type Search = { searchParams: Promise<Record<string, string | string[] | undefined>> };

async function auctionOr404(id: number): Promise<Auction> {
  try {
    return (await request(() =>
      api.GET("/api/v1/auctions/{id}/", { params: { path: { id } } }),
    )) as Auction;
  } catch (error) {
    // 404 is the only refusal that means "this page does not exist". Anything
    // else — the backend down, a 500 — must not be dressed up as a missing
    // auction: that turns an outage into a page that looks correct and tells a
    // visitor the auction was removed.
    if (error instanceof ApiError && error.status === 404) notFound();
    throw error;
  }
}

export async function generateMetadata({ params }: Params): Promise<Metadata> {
  const { id } = await params;
  const auction = await auctionOr404(Number(id));

  return {
    title: auction.title,
    description: `مزاد رقم ${auction.number} — ${auction.state_label}.`,
  };
}

export default async function AuctionPage({ params, searchParams }: Params & Search) {
  const { id } = await params;
  const auctionId = readNumber(id, 0);
  const query = toParams(await searchParams);
  const { limit, offset } = readPaging(query);

  const auction = await auctionOr404(auctionId);

  // Only the parameters the contract declares are forwarded. An unknown one
  // arriving in the url is dropped here rather than passed through to be
  // refused by the API with a message the visitor cannot act on.
  const filters: Record<string, string> = {};
  for (const field of FILTER_FIELDS) {
    const value = query.get(field);
    if (value) filters[field] = value;
  }

  const page = await request(() =>
    api.GET("/api/v1/auctions/{id}/vehicles/", {
      params: { path: { id: auctionId }, query: { limit, offset, ...filters } },
    }),
  );

  return (
    <PageShell title={auction.title}>
      <p className="-mt-4 mb-6 text-sm text-neutral-600">
        مزاد رقم {count(auction.number)} · {auction.state_label} · ينتهي{" "}
        {dateTime(auction.ends_at)}
      </p>

      <VehicleFilters action={`/auctions/${auctionId}`} values={query} />

      <VehicleGrid vehicles={(page.results ?? []) as Vehicle[]} />

      <Pagination
        query={query}
        total={page.total}
        limit={limit}
        offset={offset}
        path={`/auctions/${auctionId}`}
      />
    </PageShell>
  );
}
