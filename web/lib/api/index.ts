/**
 * الواجهة الواحدة بين `features` و`lib/api` — T1001.
 *
 * `docs/team-plan.md` gives the web three layers and one rule about them:
 * *`features` لا تستورد `lib/api` إلا عبر واجهة واحدة*. This file is that
 * interface. A feature imports `@/lib/api` and nothing deeper — never
 * `@/lib/api/schema`, never `@/lib/api/client` — so the generated module stays
 * replaceable and, more importantly, so there is one place to look when asking
 * "what can the web actually ask the backend for?".
 *
 * That question is the point. Rule 1 of spec 011 is **لا نقطة API خاصة
 * بالويب**: anything the web needs and the contract does not offer gets added
 * to the contract, where the app inherits it — or does not get added. A single
 * export surface is what makes that reviewable rather than aspirational, and
 * `T1026`'s check reads this file.
 *
 * Nothing in here decides anything. There is no price computed, no eligibility
 * evaluated, no "can they bid" answered (rule 3, and Article 4-5). Every one of
 * those questions is asked of the server, which already owns the answer and
 * already has tests for it.
 */

export { api, backendUrl, request } from "./client";
// طبقة مؤقّتة معلَنة — انظر `awaiting.ts` لسبب وجودها وموعد حذفها.
export { PHASES } from "./awaiting";
export type { Phase, PhaseCounts, Vehicle, VehiclePage } from "./awaiting";
export { ApiError, CLIENT_CODES, messageOf, toApiError } from "./errors";
export type { ApiErrorBody, ErrorDetail } from "./errors";
export type { components, operations, paths } from "./schema";
