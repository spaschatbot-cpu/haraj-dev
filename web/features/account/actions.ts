"use server";

/**
 * تعديل الملف الشخصي والشركة والهوية — T1012.
 *
 * Three actions, and every rule about them lives on the server. In particular
 * the one that looks like a client-side convenience and is not: **a national id
 * is set once, and only once it is valid** (phase 007, T606). The web does not
 * check the checksum, does not decide whether this customer may still change
 * theirs, and does not grey the field out on its own reasoning — it sends what
 * was typed and renders the answer. `apps/accounts/identity.py` owns "valid",
 * and a second implementation here would be a second definition of a customer's
 * identity.
 *
 * All three write through the session cookie: the request is made by this
 * server with the token from `lib/session.ts`, so the browser never holds it.
 */

import { redirect } from "next/navigation";
import { cookies } from "next/headers";

import { ApiError, api, messageOf, request } from "@/lib/api";
import { setFlash } from "@/lib/flash";
import { authHeader } from "@/lib/session";

const ACCOUNT = "/account";

async function finish(error: unknown | null, done: string): Promise<never> {
  const store = await cookies();

  setFlash(
    store,
    error === null
      ? // The one sentence this layer writes, and it is a confirmation rather
        // than a refusal: the backend answers a successful PATCH with the
        // object, not with a message, so there is nothing of its own to echo.
        { code: "saved", message: done }
      : {
          code: error instanceof ApiError ? error.code : "",
          message: messageOf(error),
        },
  );
  redirect(ACCOUNT);
}

/** The header this server sends on the customer's behalf. */
async function auth(): Promise<Record<string, string>> {
  return authHeader(await cookies());
}

export async function saveProfile(form: FormData): Promise<void> {
  const full_name = String(form.get("full_name") ?? "").trim();
  const email = String(form.get("email") ?? "").trim();

  const headers = await auth();

  try {
    await request(() =>
      api.PATCH("/api/v1/profile/", { headers, body: { full_name, email } }),
    );
  } catch (error) {
    return finish(error, "");
  }
  return finish(null, "حُفظت بياناتك.");
}

/**
 * The company profile — sent whole, every field, every time.
 *
 * Not a diff of what changed: the endpoint takes the profile as a unit and
 * `apps/accounts/services.save_company_profile` decides whether the result is
 * complete. Sending only the edited fields would make "complete" depend on
 * which box somebody happened to touch.
 */
export async function saveCompany(form: FormData): Promise<void> {
  const fields = [
    "name",
    "representative_name",
    "commercial_register",
    "vat_number",
    "building_number",
    "street",
    "district",
    "city",
    "postal_code",
  ] as const;

  const body: Record<string, string> = {};
  for (const field of fields) body[field] = String(form.get(field) ?? "").trim();

  const headers = await auth();

  try {
    await request(() => api.PUT("/api/v1/profile/company/", { headers, body }));
  } catch (error) {
    return finish(error, "");
  }
  return finish(null, "حُفظت بيانات الشركة.");
}

/**
 * The national id. Sent as typed, judged by the server.
 *
 * A correct one is pinned forever and a wrong one may still be corrected — that
 * rule is `apps/accounts/services.set_national_id`, and it is the reason this
 * function does no validation of its own. A web-side checksum would refuse a
 * number the backend would have accepted, or accept one it would refuse, and
 * either way the customer is told something untrue about their own identity.
 */
export async function saveNationalId(form: FormData): Promise<void> {
  const national_id = String(form.get("national_id") ?? "").trim();

  const headers = await auth();

  try {
    // `PUT`, which is what the contract declares. Setting an identity is
    // idempotent by design — the same number sent twice is the same fact — and
    // the endpoint's own rule is that a *correct* one is pinned forever.
    await request(() =>
      api.PUT("/api/v1/profile/national-id/", { headers, body: { national_id } }),
    );
  } catch (error) {
    return finish(error, "");
  }
  return finish(null, "سُجّل رقم الهوية.");
}
