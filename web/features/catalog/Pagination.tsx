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
    /*
      شريطٌ في بطاقةٍ كبقيّة الشاشة (T1032). والطرفان يبقيان مرسومَين حين لا
      يعملان — رماديّين لا غائبين: أزرارٌ تختفي وتظهر تجعل موضع «التالي» يقفز
      بين صفحةٍ وأخرى، فيُضغط ما لم يُقصد.
    */
    <nav
      className="mt-6 flex items-center justify-between gap-4 rounded-xl bg-surface-lowest p-3 text-label-md shadow-sm"
      aria-label="صفحات"
    >
      {offset > 0 ? (
        <Link
          href={href(offset - limit)}
          className="rounded-lg bg-surface-container px-5 py-2 transition-colors hover:bg-surface-high"
          rel="prev"
        >
          السابق
        </Link>
      ) : (
        <span className="px-5 py-2 text-outline">السابق</span>
      )}

      <span className="select-none text-center">
        صفحة <span className="tnum">{page}</span> من{" "}
        <span className="tnum">{pages}</span> ·{" "}
        <span className="tnum">{total}</span> نتيجة
      </span>

      {offset + limit < total ? (
        <Link
          href={href(offset + limit)}
          className="rounded-lg bg-surface-container px-5 py-2 transition-colors hover:bg-surface-high"
          rel="next"
        >
          التالي
        </Link>
      ) : (
        <span className="px-5 py-2 text-outline">التالي</span>
      )}
    </nav>
  );
}
