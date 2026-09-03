/**
 * العرض في مكان واحد — التاريخ والوقت والمبلغ.
 *
 * Rule 5 of spec 011 asks that times arrive UTC from the server and be
 * converted for display **in one place in the web**, the way `apps/core/time`
 * does it for the backend. This is that place. Two screens each calling
 * `toLocaleString` with their own options is two screens that show the same
 * auction ending at two different times the day one of them is edited.
 *
 * And the money rule, which is not a formatting preference but Article 3-2:
 * **an amount is rendered exactly as it arrived.** The server sends `"1500.00"`
 * as a string, and it reaches the screen as `"1500.00"`. Nothing here parses
 * one, adds one, rounds one, or inserts a thousands separator into one:
 *
 * * `Number("0.1") + Number("0.2")` is `0.30000000000000004` in JavaScript, so
 *   any arithmetic on a money string is a wrong balance waiting for the right
 *   two numbers;
 * * and a customer comparing this page against a statement or an invoice must
 *   not have to undo a display transformation in their head — which is the same
 *   reason every console template uses `unlocalize`.
 *
 * `ops/checks/web_money_is_never_computed.mjs` fails the build on the first
 * `Number(price)` anybody writes.
 */

//: One timezone for the whole product. The auctions are held in Saudi Arabia
//: and the times shown are the times the auction actually runs, so a customer
//: travelling does not see an auction "ending" at a different hour than the one
//: the yard is working to.
export const TIMEZONE = "Asia/Riyadh";

//: Arabic locale with Latin digits. Latin deliberately: the customer compares
//: these numbers against a bank statement, an Odoo invoice and an SMS, and all
//: three carry Latin digits.
const LOCALE = "ar-SA-u-nu-latn";

const DATE_TIME = new Intl.DateTimeFormat(LOCALE, {
  timeZone: TIMEZONE,
  dateStyle: "medium",
  timeStyle: "short",
});

const DATE_ONLY = new Intl.DateTimeFormat(LOCALE, {
  timeZone: TIMEZONE,
  dateStyle: "medium",
});

/**
 * A server timestamp, as a person reads it. Empty string for a missing one.
 *
 * An empty string rather than a dash or `"—"`: what to show in place of a
 * missing value is the calling screen's decision, and a helper that decides it
 * puts that punctuation in places nobody chose it for.
 */
export function dateTime(value: string | null | undefined): string {
  if (!value) return "";
  const moment = new Date(value);
  return Number.isNaN(moment.getTime()) ? "" : DATE_TIME.format(moment);
}

export function date(value: string | null | undefined): string {
  if (!value) return "";
  const moment = new Date(value);
  return Number.isNaN(moment.getTime()) ? "" : DATE_ONLY.format(moment);
}

/**
 * An amount, exactly as the server sent it. **No arithmetic, ever.**
 *
 * The only thing this function does is answer the "there is no amount" case in
 * one place, so every screen renders a missing price the same way rather than
 * one showing `null` and the next showing an empty cell. The digits themselves
 * are untouched — see the module docstring for why that is a rule and not a
 * style.
 */
export function amount(value: string | null | undefined): string {
  return value ?? "";
}

/** An integer the server sent, for display. Never used on a money value. */
export function count(value: number | null | undefined): string {
  return value === null || value === undefined ? "" : value.toLocaleString(LOCALE);
}
