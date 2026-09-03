/**
 * رسالة لمرة واحدة بين فعلٍ وصفحة — في كوكي، لا في الرابط.
 *
 * A server action that fails has to get the server's sentence onto the page it
 * redirects to. The obvious way is the query string, and it is the wrong way.
 *
 * A message in the url is a message anybody can write. `…/sign-in?message=<any
 * sentence>` renders whatever the link says, so a crafted link becomes a
 * page — on our domain, in our layout, in Arabic — that says the customer's
 * account is suspended and to call a number. React escapes the text, so it is
 * not an XSS; it is a phishing surface, which is worse in the sense that
 * nothing in the code looks broken.
 *
 * So the flash goes in an `HttpOnly` cookie the server writes and the next
 * render consumes. Only our own server can put a sentence in it, which is the
 * property that matters. It survives exactly one page load, because a refusal
 * still on screen two navigations later reads as a new refusal.
 *
 * The message inside is always the server's own words (T1005). This module
 * carries them; it never writes one.
 */

import type { cookies } from "next/headers";

type CookieStore = Awaited<ReturnType<typeof cookies>>;

const FLASH_COOKIE = "haraj_flash";

//: Long enough to survive a redirect on a slow connection, short enough that a
//: refusal cannot resurface in a session somebody comes back to later.
const MAX_AGE = 60;

export interface Flash {
  /** The backend's stable code, for a screen that wants to branch. */
  code: string;
  /** The backend's Arabic sentence, ready to render. */
  message: string;
}

export function setFlash(store: CookieStore, flash: Flash): void {
  store.set(FLASH_COOKIE, JSON.stringify(flash), {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    path: "/",
    maxAge: MAX_AGE,
  });
}

/**
 * Read the flash and clear it, in one call.
 *
 * Reading without clearing is how a message ends up shown twice — once on the
 * page it was meant for and again on the next one the visitor opens — and the
 * two callers who would have to remember to clear it are the two who forget.
 */
export function takeFlash(store: CookieStore): Flash | null {
  const raw = store.get(FLASH_COOKIE)?.value;
  if (!raw) return null;

  store.delete(FLASH_COOKIE);

  try {
    const parsed: unknown = JSON.parse(raw);
    if (
      typeof parsed === "object" &&
      parsed !== null &&
      typeof (parsed as Flash).message === "string"
    ) {
      return { code: String((parsed as Flash).code ?? ""), message: (parsed as Flash).message };
    }
  } catch {
    // A cookie we cannot read is a cookie from an older version of this code,
    // or one somebody edited. Either way it has already been deleted above, and
    // showing nothing is the right outcome.
  }
  return null;
}
