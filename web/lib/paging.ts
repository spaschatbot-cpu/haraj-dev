/**
 * قراءة الترقيم من سلسلة الاستعلام — قراءة، لا قرار.
 *
 * The bounds are the server's: `limit` is capped in `apps/auctions/listing.py`
 * and the API refuses anything larger, so what happens here is *reading a
 * number out of a string* and nothing more. The clamp below is not a second
 * rule, it is a defence against `?limit=abc` producing `NaN` and a request the
 * backend answers with a 400 that the visitor cannot act on.
 */

//: What a page holds when the url does not say. Twelve rather than the API's
//: twenty: three columns on a desktop grid divide into it, and a partial last
//: row on every page reads as a rendering bug.
export const PAGE_SIZE = 12;

export function readNumber(value: string | undefined, fallback: number): number {
  const parsed = Number.parseInt(value ?? "", 10);
  return Number.isFinite(parsed) && parsed >= 0 ? parsed : fallback;
}

export function readPaging(params: URLSearchParams): { limit: number; offset: number } {
  return {
    limit: Math.min(Math.max(readNumber(params.get("limit") ?? undefined, PAGE_SIZE), 1), 100),
    offset: readNumber(params.get("offset") ?? undefined, 0),
  };
}

/**
 * The search params a page was rendered with, as a `URLSearchParams`.
 *
 * Next hands a plain object with `string | string[]` values. Normalising it in
 * one place keeps every page's filter-reading identical, and keeps the
 * "repeated parameter" case — `?make=a&make=b` — from silently becoming the
 * string `"a,b"` in one screen and the array in another.
 */
export function toParams(
  input: Record<string, string | string[] | undefined>,
): URLSearchParams {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(input)) {
    if (value === undefined) continue;
    if (Array.isArray(value)) {
      const first = value[0];
      if (first !== undefined) params.set(key, first);
    } else {
      params.set(key, value);
    }
  }
  return params;
}
