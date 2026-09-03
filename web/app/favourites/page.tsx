/**
 * مفضّلتي — T1013.
 *
 * The list the server holds, rendered through the one card builder like every
 * other list of vehicles. A car marked and since withdrawn is simply absent:
 * a favourite is a bookmark and never a claim, and it grants no sight of a row
 * its owner may no longer show.
 */

import type { Metadata } from "next";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { VehicleGrid, type Vehicle } from "@/features/catalog/VehicleCard";
import { Pagination } from "@/features/catalog/Pagination";
import { Notice } from "@/features/shell/Notice";
import { PageShell } from "@/features/shell/PageShell";
import { ApiError, api, request } from "@/lib/api";
import { takeFlash } from "@/lib/flash";
import { readPaging, toParams } from "@/lib/paging";
import { authHeader, hasSession } from "@/lib/session";

export const metadata: Metadata = {
  title: "مفضّلتي",
  robots: { index: false, follow: false },
};

export const dynamic = "force-dynamic";

export default async function FavouritesPage({
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
      api.GET("/api/v1/favourites/", { headers, params: { query: { limit, offset } } }),
    );
  } catch (error) {
    if (error instanceof ApiError && (error.status === 401 || error.status === 403)) {
      redirect("/sign-in");
    }
    throw error;
  }

  return (
    <PageShell title="مفضّلتي">
      <Notice message={flash?.message ?? ""} />

      {page.total === 0 ? (
        <p className="py-12 text-center text-neutral-500">
          لم تحفظ مركبة بعد. علامة المفضّلة على أي مركبة تعيدك إليها من هنا.
        </p>
      ) : (
        <VehicleGrid vehicles={(page.results ?? []) as Vehicle[]} />
      )}

      <Pagination
        query={query}
        total={page.total}
        limit={limit}
        offset={offset}
        path="/favourites"
      />
    </PageShell>
  );
}
