/**
 * العميل المولَّد من المخطط — T1002، ولا نموذج مكتوب بيد واحدة.
 *
 * `schema.ts` is generated from `backend/openapi/schema.yaml` by
 * `npm run schema` and is never edited. `openapi-fetch` reads those types, so
 * every path, every query parameter and every response body is checked at
 * compile time against the contract phase 007 pinned. A field renamed in the
 * backend and not regenerated here does not reach the browser to be discovered
 * by a customer — `tsc` refuses the build (J2), and `scripts/schema-is-current.mjs`
 * refuses it in CI even if somebody forgot to run the generator locally.
 *
 * Where the token lives
 * ---------------------
 * Nowhere in this file, and nowhere the browser can read (T1004, rule 8). The
 * browser's requests go to this app's own origin at {@link PROXY_PREFIX}; the
 * route handler behind it reads the `HttpOnly` cookie and forwards. Server
 * components skip the hop and call the backend directly with the same cookie.
 *
 * So `baseUrl` differs by where the code is running, and that is the only
 * difference. Both sides speak the same generated types to the same paths,
 * because a second client shape is a second place for a request to be built
 * slightly differently.
 */

import createClient from "openapi-fetch";

import { toApiError } from "./errors";
import type { paths } from "./schema";

/**
 * Where the browser sends its calls: this app, which holds the cookie.
 *
 * A *transparent* prefix, not an API of its own. The route handler behind it
 * forwards the path unchanged, so it cannot grow a web-only endpoint — which is
 * rule 1 (**لا نقطة API خاصة بالويب**) made impossible rather than forbidden.
 */
export const PROXY_PREFIX = "/api/backend";

/** The backend, as the *server* reaches it. Never sent to the browser. */
export function backendUrl(): string {
  const configured = process.env.BACKEND_URL ?? "http://127.0.0.1:8000";
  return configured.replace(/\/+$/, "");
}

const onServer = typeof window === "undefined";

/**
 * The typed client. Import it from `@/lib/api`, never from this module.
 *
 * `credentials: "include"` on the browser side so the session cookie rides
 * along; on the server side the cookie is attached per-request by the caller,
 * because a server component handles one visitor's request at a time and a
 * client that remembered a cookie would eventually serve it to somebody else.
 */
export const api = createClient<paths>({
  baseUrl: onServer ? backendUrl() : PROXY_PREFIX,
  credentials: onServer ? "omit" : "include",
  headers: { "Accept-Language": "ar" },
  // Looked up on every call rather than captured once at module load. Without
  // the wrapper the client closes over whatever `fetch` was when this module
  // was first imported, which is a real behaviour difference and not only a
  // testing inconvenience: anything that installs instrumentation after the
  // first import — a tracing agent, a test's stub — is silently bypassed, and
  // "the request was never made" looks identical to "the server never
  // answered".
  fetch: (...args) => globalThis.fetch(...args),
});

/**
 * One request, with the refusal already turned into an {@link ApiError}.
 *
 * Every caller in `features` uses this rather than reading `.error` off the
 * openapi-fetch result, so no screen has to remember to handle the envelope —
 * and a screen that forgets is a screen that renders `undefined` where a
 * sentence belongs. `data` is returned or a typed error is thrown; there is no
 * third outcome to write a branch for.
 */
export async function request<T>(
  call: () => Promise<{
    data?: T;
    error?: unknown;
    response: Response;
  }>,
): Promise<T> {
  let result: Awaited<ReturnType<typeof call>>;

  try {
    result = await call();
  } catch {
    // The request never produced a response at all. Status 0 is what
    // `toApiError` reads as "unreachable" — a distinct thing from a refusal,
    // and the distinction is what tells a customer to check their connection
    // rather than their balance.
    throw toApiError(undefined, 0);
  }

  if (result.error !== undefined || !result.response.ok) {
    throw toApiError(result.error, result.response.status);
  }
  return result.data as T;
}
