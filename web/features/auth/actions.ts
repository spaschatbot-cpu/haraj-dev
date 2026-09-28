"use server";

/**
 * الدخول بالجوال وOTP — أفعال خادم، تعمل بلا جافاسكربت. T1011.
 *
 * Two actions, one per step, both plain form submissions. `<form action={…}>`
 * with a server action is a real `POST` to this server: it works before
 * hydration and it works with scripting off, which is the same standard the
 * browse pages are held to. A sign-in that needs JavaScript is a sign-in that
 * fails for the visitor on the slow connection who most needs it to work.
 *
 * **The code never appears in a url and the token never reaches the browser.**
 * The action calls the backend server-side and writes the session with
 * `lib/session.ts`, so the only thing that crosses to the client is a redirect.
 *
 * Distinguishing "we could not send it" from "that code is wrong"
 * ---------------------------------------------------------------
 * This is the acceptance criterion, and it is phase 007's T603 lesson arriving
 * in the web. In v1 an SMS provider outage was reported to the customer as an
 * incorrect code: they retyped a correct code until they were locked out, and
 * support could not tell the two cases apart afterwards either. The backend now
 * answers with different codes and different sentences, and the only thing this
 * layer has to do is **not flatten them** — so it shows the server's sentence
 * as it came and never substitutes a generic one (T1005).
 */

import { redirect } from "next/navigation";
import { cookies } from "next/headers";

import { ApiError, api, messageOf, request } from "@/lib/api";
import { setFlash } from "@/lib/flash";
import { setSession } from "@/lib/session";

/** Where a signed-in visitor lands. */
const AFTER_SIGN_IN = "/account";

//: «أكمل تسجيلك» — حيث يذهب من ينقص ملفَّه شيءٌ بعد الرمز. انظر `verifyCode`.
const COMPLETE_REGISTRATION = "/sign-in/complete";

async function fail(error: unknown, back: string): Promise<never> {
  const store = await cookies();
  setFlash(store, {
    code: error instanceof ApiError ? error.code : "",
    // The server's own words. A sentence written here would be a second
    // wording of a refusal the backend already phrased, and the two would
    // disagree in front of a customer depending on which channel they opened.
    message: messageOf(error),
  }, back);
  redirect(back);
}

/**
 * Step one: send the code.
 *
 * The phone number is echoed back in the redirect so step two knows whose code
 * it is. That is not a secret — the customer just typed it — and putting it in
 * the url means a reload of the code screen does not lose it.
 */
export async function sendCode(form: FormData): Promise<void> {
  const phone = String(form.get("phone") ?? "").trim();

  try {
    await request(() =>
      api.POST("/api/v1/auth/code/", { body: { phone, purpose: "login" } }),
    );
  } catch (error) {
    // `return`, not `await`: `fail` never resolves — it redirects, and Next
    // implements a redirect by throwing. Returning it is also what tells the
    // type checker that nothing below this line runs.
    return fail(error, `/sign-in?phone=${encodeURIComponent(phone)}`);
  }

  redirect(`/sign-in?phone=${encodeURIComponent(phone)}&sent=1`);
}

/**
 * Step two: verify the code, and become signed in.
 *
 * The same endpoint registers a new customer and signs in an existing one — the
 * backend decides which, and this layer does not look the number up first (that
 * would be a rule, and rules live on the server). What the account still lacks
 * is the server's answer too (`registration_missing`), read right after.
 */
export async function verifyCode(form: FormData): Promise<void> {
  const phone = String(form.get("phone") ?? "").trim();
  const code = String(form.get("code") ?? "").trim();
  const back = `/sign-in?phone=${encodeURIComponent(phone)}&sent=1`;

  /*
    **الرمزُ وحدَه، ثمّ القرار** — ترتيبُ v1 وطلبُ المالك (٢٨ سبتمبر ٢٠٢٦):
    «أوّل حاجة أدخل الرقم، بعد كده الـverification، بعد كده يعمل detection:
    الحساب موجود؟ بياناته ناقصة؟ جديد؟».

    وكان الاسمُ يُطلب هنا مع الرمز «للتسجيل الجديد فقط»، فيُتجاهَل بصمتٍ لكلّ
    حسابٍ موجودٍ باسمٍ فارغ — والمنقولون من v1 كثيرٌ منهم كذلك (قِيس على حساب
    المالك نفسِه). و`defer_profile` يُنشئ الحسابَ الجديدَ بلا اسم، ثمّ يُسأل
    الخادمُ عمّا ينقص (`registration_missing`) — والقرارُ قرارُه.
  */
  let tokens;
  try {
    tokens = await request(() =>
      api.POST("/api/v1/auth/verify/", { body: { phone, code, defer_profile: true } }),
    );
  } catch (error) {
    return fail(error, back);
  }

  const store = await cookies();
  //: و`expires_in` معه: عمرُ الكوكي = عمرُ الرمز، فغيابُه إشارةُ انتهاءٍ
  //: يقرؤها `middleware.ts` ليبدّله. بلا هذا يعيش الكوكي يوماً كاملاً على
  //: رمزٍ عمره ربع ساعة، فتقول الشاشة «داخل» وكل فعلٍ يردّ 401.
  setSession(store, {
    access: tokens.access,
    refresh: tokens.refresh,
    expiresIn: tokens.expires_in,
  });

  // ماذا ينقص؟ بالرمز الجديد نفسِه — الكوكي كُتب للتوّ ولا يُقرأ في هذا الطلب.
  // وفشلُ هذا السؤال لا يُسقط الدخول: الجلسةُ قائمة، و«حسابي» تسأل ثانيةً.
  const missing = await request(() =>
    api.GET("/api/v1/profile/", { headers: { Authorization: `Bearer ${tokens.access}` } }),
  )
    .then((profile) => profile.registration_missing.length)
    .catch(() => 0);

  redirect(missing > 0 ? COMPLETE_REGISTRATION : AFTER_SIGN_IN);
}

/**
 * Sign out: clear the cookies and go back to the public site.
 *
 * A form `POST`, never a link. A `GET` that ends a session is a session ended
 * by a prefetch, a crawler, or an image tag on somebody else's page.
 */
export async function signOut(): Promise<void> {
  const store = await cookies();
  const { clearSession } = await import("@/lib/session");
  clearSession(store);
  redirect("/");
}
