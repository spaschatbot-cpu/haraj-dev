/**
 * الجلسة في كوكيز HttpOnly — T1004، ولا رمز يلمسه جافاسكربت أبداً.
 *
 * The rule and the reason, from spec 011 §8: *ثغرة XSS واحدة على موقع فيه
 * محفظة تعني حساباً مسروقاً*. A token in `localStorage` is readable by any
 * script that reaches the page — an npm dependency three levels down, an
 * analytics snippet, a reflected parameter. A token in an `HttpOnly` cookie is
 * not, and the same XSS then costs a session's actions rather than the account.
 *
 * So the tokens live in cookies this module sets, and **no code path puts them
 * anywhere else**: not in `localStorage`, not in `sessionStorage`, not in a
 * React store, not in a prop. `ops/checks/web_tokens_are_httponly.mjs` fails the
 * build on any of those, because this is a rule that has to be enforced rather
 * than remembered — the tempting shortcut ("just for the refresh call") is
 * written by somebody who knows the rule and thinks their case is different.
 *
 * Why the names are here and not typed twice
 * ------------------------------------------
 * The route handlers read them, the proxy reads them, the sign-out clears them.
 * Three files spelling `"haraj_access"` is three files that keep agreeing until
 * one is renamed.
 */

import type { cookies } from "next/headers";

type CookieStore = Awaited<ReturnType<typeof cookies>>;

export const ACCESS_COOKIE = "haraj_access";
export const REFRESH_COOKIE = "haraj_refresh";

/**
 * The flags every session cookie carries, in one object.
 *
 * * `httpOnly` — the whole point; see above.
 * * `secure` — off only when the app itself is served over plain HTTP, which is
 *   local development. A cookie marked `Secure` is simply never stored by the
 *   browser on `http://localhost`, so hardcoding it to `true` would make the
 *   dev environment silently sign everybody out on every navigation, and
 *   whoever hit that would "fix" it by removing the flag in production too.
 * * `sameSite: "lax"` — the session survives a customer arriving from a Google
 *   result (a top-level GET), and does not ride along on a cross-site POST,
 *   which is the shape of a CSRF attempt against the wallet.
 * * `path: "/"` — every route, including the proxy under `/api/backend`.
 */
function options(maxAge: number) {
  return {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax" as const,
    path: "/",
    maxAge,
  };
}

//: How long each cookie is kept by the browser. These are storage lifetimes,
//: not authority: the backend decides whether a token is still valid, and it is
//: the only thing that can. Keeping the cookie a little beyond the token's life
//: is deliberate — an expired access token can be refreshed, while a missing
//: cookie looks exactly like signing out.
const ACCESS_MAX_AGE = 60 * 60 * 24;
const REFRESH_MAX_AGE = 60 * 60 * 24 * 30;

export interface Tokens {
  access: string;
  refresh?: string;
}

/** Write the session. Called from route handlers only — never from a component. */
export function setSession(store: CookieStore, tokens: Tokens): void {
  store.set(ACCESS_COOKIE, tokens.access, options(ACCESS_MAX_AGE));
  if (tokens.refresh) {
    store.set(REFRESH_COOKIE, tokens.refresh, options(REFRESH_MAX_AGE));
  }
}

/**
 * Clear both cookies.
 *
 * Both, always, even when only one looks stale: a refresh token left behind
 * after a sign-out is a session somebody can resume from a shared machine, and
 * "sign out" that leaves a way back in is worse than no button at all.
 */
export function clearSession(store: CookieStore): void {
  store.delete(ACCESS_COOKIE);
  store.delete(REFRESH_COOKIE);
}

/** The access token, for a server-side call. Never returned to the browser. */
export function accessToken(store: CookieStore): string | undefined {
  return store.get(ACCESS_COOKIE)?.value;
}

export function refreshToken(store: CookieStore): string | undefined {
  return store.get(REFRESH_COOKIE)?.value;
}

/**
 * Whether this visitor has a session, as far as the browser is concerned.
 *
 * Deliberately not named `isAuthenticated`: the presence of a cookie is not
 * proof of anything, and only the backend can say whether the token inside is
 * still good. This answers "should the UI offer the signed-in shell?", and any
 * screen that needs the real answer asks the server for it.
 */
export function hasSession(store: CookieStore): boolean {
  return accessToken(store) !== undefined;
}

/** The `Authorization` header for a server-side call, or nothing. */
export function authHeader(store: CookieStore): Record<string, string> {
  const token = accessToken(store);
  return token ? { Authorization: `Bearer ${token}` } : {};
}
