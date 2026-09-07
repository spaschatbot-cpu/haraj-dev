/**
 * تبديلُ رمزٍ منتهٍ برمزٍ حيّ، مرةً واحدة، قبل أن تُرندَر الصفحة.
 *
 * العطل الذي وُلد هذا لأجله (قِيس في المتصفّح، 2026-09-07)
 * =======================================================
 * رمز الوصول عمره خمس عشرة دقيقة، ورمز التحديث ثلاثون يوماً، و`refreshToken()`
 * كانت مكتوبةً ومُختبَرة **ولا ينادِيها أحد**. فبعد ربع ساعة: الشاشة تعرض
 * صندوق المزايدة، وسطرُ «السعر + الضريبة» يكتب «—»، وضغطُ «دخول المزاد»
 * يُنتج خطأ خادم — ولا شيء يقول للعميل أن جلسته انتهت. رأيتُه يقع بالحرف.
 *
 * لماذا هنا لا في رندرة الصفحة
 * =============================
 * **مكوّن الخادم لا يستطيع كتابة كوكي.** ولو حدّث الرمزَ في الرندرة لضاع
 * الرمز الجديد — والأسوأ من ضياعه أن **رموز التحديث تدور**: الخلفية تُبطل
 * الرمز المقدَّم وتصدر غيره، و`RefreshTokenReused` على رمزٍ دار **تُلغي كل
 * رموز العميل** (`apps/accounts/tokens.py`). فتحديثٌ لا يُحفَظ ليس هدراً، بل
 * خروجٌ قسريّ من كل الأجهزة عند النداء التالي.
 *
 * فالمواضع التي يجوز فيها التحديث ثلاثة، وكلها تكتب كوكي: هذا الوسيط،
 * ومعالجات المسارات، وأفعال الخادم (`lib/authed.ts`).
 *
 * ولماذا **التنقّل وحده**
 * ======================
 * السباق هو الخطر: طلبان يجدان الكوكي غائباً فيحدّثان معاً، فيصل الثاني برمزٍ
 * أبطله الأول — وتُلغى كل الرموز. فيقتصر التحديث على **تنقّلٍ حقيقي إلى
 * وثيقة**: لا جلبٌ مسبق من الموجّه، ولا نداء RSC، ولا أصلٌ ساكن. تنقّلٌ واحد
 * في اللحظة هو ما يفعله متصفّحٌ بشريّ، والباقي يذهب بالرمز الذي عنده ويتلقّى
 * جوابه.
 *
 * وحين يفشل التحديث تُمسَح الكوكيّتان: رمزُ تحديثٍ مرفوض لن يُقبل في المحاولة
 * التالية، وتركُه يعني عميلاً يُرفض في كل صفحة بلا أن يُعرَض عليه الدخول.
 *
 * وهنا أيضاً تُستهلَك رسالةُ المرّة الواحدة
 * ==========================================
 * وللسبب نفسه بالضبط: `lib/flash.ts` كانت تحذف كوكيّها **في الرندرة**،
 * فتُنتج `Cookies can only be modified in a Server Action or Route Handler`
 * — أي خطأ خادمٍ على كل صفحةٍ يحوّل إليها فعلٌ برسالة. قِيس في المتصفّح.
 *
 * والحذف من **الرد** يحفظ الدلالة كما كانت: الطلب يحمل الكوكي فتقرؤه
 * الرندرة، والرد يمسحه فلا يصل التنقّل التالي — مرةٌ واحدة، تماماً.
 */

import { NextResponse, type NextRequest } from "next/server";

import { api } from "@/lib/api";
import { FLASH_COOKIE } from "@/lib/flash";
import { ACCESS_COOKIE, REFRESH_COOKIE } from "@/lib/session";

/**
 * ما لا يُنقَّل فيه — بالسلبِ لا بالإيجاب.
 *
 * قائمةُ ما **يُحدَّث** كانت ستنسى مساراً يوم يُضاف، وقائمةُ ما يُستثنى تنسى
 * أصلاً ساكناً فيمرّ بلا ضرر.
 */
export const config = {
  matcher: ["/((?!_next/|favicon.ico|api/backend/).*)"],
};

/** أهذا تنقّلٌ إلى وثيقة، أم شيءٌ آخر يطلبه الإطار؟ */
function isDocumentNavigation(request: NextRequest): boolean {
  //: `next-router-prefetch` يعني جلباً مسبقاً لرابطٍ لم يُضغط بعد، و`rsc`
  //: يعني تحديث جزءٍ من شجرة مرندَرة. كلاهما قد ينطلق عدة مرات معاً — وهو
  //: بالضبط السباق الذي يُلغي كل الرموز.
  if (request.headers.get("next-router-prefetch")) return false;
  if (request.headers.get("rsc")) return false;
  if (request.headers.get("sec-fetch-mode") === "navigate") return true;
  return (request.headers.get("accept") ?? "").includes("text/html");
}

export async function middleware(request: NextRequest) {
  const access = request.cookies.get(ACCESS_COOKIE)?.value;
  const refresh = request.cookies.get(REFRESH_COOKIE)?.value;

  const navigating = isDocumentNavigation(request);

  /**
   * تمسح الرسالة من الرد إن كان هذا تنقّلاً — والجلبُ المسبق لا يمسح، وإلا
   * أكل رابطٌ لم يُضغط رسالةً لم تُعرض بعد.
   */
  const consumeFlash = (response: NextResponse) => {
    if (navigating && request.cookies.has(FLASH_COOKIE)) {
      response.cookies.delete(FLASH_COOKIE);
    }
    return response;
  };

  //: رمزٌ حيّ، أو زائرٌ بلا جلسة أصلاً — لا تحديث في الحالتين، والرسالة
  //: تُستهلَك على أي حال: زائرٌ بلا جلسة يرى رفض الدخول ثم يمضي.
  if (access || !refresh || !navigating) {
    return consumeFlash(NextResponse.next());
  }

  /*
    العميل المولَّد لا `fetch` مكتوباً بيد — القاعدة الأولى في الفيز 011
    (`ops/checks/web_uses_the_contract_only.mjs`)، وهو محقّ حتى هنا: مسارٌ
    يُكتب حرفاً في هذا الملفّ هو مسارٌ لا يعرف المترجم أنه تغيّر يوم يتغيّر
    المخطط. و`api` يقرأ `backendUrl()` من تلقائه في الخادم.

    و`request()` **لا تُستعمل**: تلك ترمي `ApiError` على كل رفض، وهنا الرفض
    ليس خطأً بل **الجواب**: «هذا الرمز لم يعد صالحاً» قرارٌ يُتّخذ عليه.
  */
  let pair: { access: string; refresh?: string; expires_in?: number } | null = null;
  try {
    const answer = await api.POST("/api/v1/auth/refresh/", {
      body: { refresh },
    });
    if (answer.data) pair = answer.data;
  } catch {
    //: الخلفية لم تُجب. لا تُمسح الجلسة على عطلِ شبكة — العميل لم يُخطئ،
    //: ورمزه ما زال صالحاً على الأرجح. يمرّ الطلب بلا رمز، فتُرسَم الصفحة
    //: العامة، والمحاولة التالية تُعيد الكرّة.
    return consumeFlash(NextResponse.next());
  }

  if (pair === null) {
    //: رُفض الرمز — منتهٍ أو مُبطَل أو مُعاد استعماله. يُمسح الاثنان معاً:
    //: رمزُ تحديثٍ مرفوض لن يُقبل غداً، وتركُه يعني رفضاً في كل صفحة.
    const refused = NextResponse.next();
    refused.cookies.delete(ACCESS_COOKIE);
    refused.cookies.delete(REFRESH_COOKIE);
    return consumeFlash(refused);
  }

  /*
    **والطلبُ نفسه يحمل الرمز الجديد** — يُضبط **قبل** بناء الرد.
    `NextResponse.next({ request })` يلتقط الترويسات كما هي عند ندائه، فضبطُ
    الكوكي بعده يعني رندرةً بجلسةٍ ميّتة ثم رمزاً يعمل في الصفحة التالية: أي
    وميضُ «سجّل دخولك» على كل عودةٍ بعد ربع ساعة.
  */
  request.cookies.set(ACCESS_COOKIE, pair.access);
  const response = NextResponse.next({ request });

  /*
    الأعلام هي أعلام `lib/session.ts` نفسها ومكرَّرةٌ هنا اضطراراً: الوسيط
    يعمل على `NextResponse` لا على مخزن `cookies()`، فلا يستطيع نداء
    `setSession`. و`web_tokens_are_httponly.mjs` يفحص هذا الملفّ كما يفحص
    ذاك، فسقوطُ `httpOnly` هنا يُسقط البناء.
  */
  const options = {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax" as const,
    path: "/",
  };
  response.cookies.set(ACCESS_COOKIE, pair.access, {
    ...options,
    maxAge: Math.max((pair.expires_in ?? 15 * 60) - 2, 1),
  });
  if (pair.refresh) {
    response.cookies.set(REFRESH_COOKIE, pair.refresh, {
      ...options,
      maxAge: 60 * 60 * 24 * 30,
    });
  }

  return consumeFlash(response);
}

/*
  عقدة لا الحافّة — والسبب مقيس.

  الوسيط يعمل على الحافّة افتراضاً، وعميلُ العقد (`openapi-fetch`) هناك
  **يرسل الطلب بلا جسم**: تصل الخلفيةَ `POST /auth/refresh/` فارغةً فتردّ
  «هذا الحقل مطلوب»، ويُقرأ الجواب رفضاً للرمز فتُمسَح الجلسة — أي خروجٌ
  كامل بدل تجديد. قِيس بترويسة تشخيص: `status=400 detail.refresh=[required]`
  ورمزٌ حيٌّ في القاعدة لم يُمسّ.

  والخلفية تُنادى من الشبكة الخاصّة في الإنتاج على أي حال، والحافّة لا تجلس
  عليها — وهو السبب نفسه المكتوب في `app/api/backend/[...path]/route.ts`.
*/
export const runtime = "nodejs";
