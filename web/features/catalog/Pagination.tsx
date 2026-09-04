/**
 * ترقيم صفحات حقيقي — T1007، ويعمل بلا جافاسكربت.
 *
 * Links, not buttons with click handlers. The whole point of server-rendering
 * these pages is that they work for a visitor arriving from a search result on
 * a slow connection before any script has run — and a "next page" that needs
 * JavaScript is a list with exactly one page for that visitor.
 *
 * It is also what makes page two shareable: the url carries the offset, so a
 * link somebody sends opens where they were.
 */

import Link from "next/link";

interface Props {
  /** The current query, so every filter on the screen survives the page change. */
  query: URLSearchParams;
  total: number;
  limit: number;
  offset: number;
  /** Where the links point — the same route the list is rendered on. */
  path: string;
}

export function Pagination({ query, total, limit, offset, path }: Props) {
  const page = Math.floor(offset / limit) + 1;
  const pages = Math.max(Math.ceil(total / limit), 1);

  function href(nextOffset: number): string {
    const next = new URLSearchParams(query);
    if (nextOffset <= 0) next.delete("offset");
    else next.set("offset", String(nextOffset));
    const search = next.toString();
    return search ? `${path}?${search}` : path;
  }

  return (
    <nav className="mt-8 flex items-center justify-between gap-4 text-sm" aria-label="صفحات">
      {offset > 0 ? (
        <Link href={href(offset - limit)} className="underline" rel="prev">
          الصفحة السابقة
        </Link>
      ) : (
        <span className="text-neutral-500">الصفحة السابقة</span>
      )}

      <span className="text-neutral-600">
        صفحة {page} من {pages} · {total} نتيجة
      </span>

      {offset + limit < total ? (
        <Link href={href(offset + limit)} className="underline" rel="next">
          الصفحة التالية
        </Link>
      ) : (
        <span className="text-neutral-500">الصفحة التالية</span>
      )}
    </nav>
  );
}
