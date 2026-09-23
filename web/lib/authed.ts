/**
 * ترويسةُ الهويّة لـ**فعل خادم** — تُجدِّد الرمزَ إن مات، وتحفظ الجديد.
 *
 * العطل (قِيس على `haraj.spas.sa` في ٢٤ سبتمبر ٢٠٢٦)
 * ================================================
 * عميلٌ دخل، ثم بعد ربع ساعةٍ ضغط «تسجيل الرقم» في «تعديل البيانات»، فوجد
 * نفسَه في صفحة الدخول بـ«يلزم تسجيل الدخول». وسجلُّ الخلفيّة يقول القصّةَ كلَّها:
 *
 *     21:41:19  GET /api/v1/profile/              200
 *     21:42:07  PUT /api/v1/profile/national-id/  401
 *
 * بين السطرين انقضى عمرُ كوكي الوصول (هو عمرُ الرمز، `lib/session.ts`). و
 * `middleware.ts` يجدّد الرمزَ **على تنقّلٍ إلى وثيقة وحده** — وفعلُ الخادم
 * `POST` لا تنقّل، فيمرّ بلا رمز. وكان تعليقُ الوسيط يقول إن أفعالَ الخادم
 * تجدّد بنفسها «في `lib/authed.ts`» — **ولم يكن الملفُّ موجوداً**. فكلُّ فعلٍ
 * (مزايدة، سحبُها، حفظُ بيانات، مفضّلة، استرداد، شحن) يُرفض بعد ربع ساعةٍ من
 * الدخول، ويُحوَّل العميلُ إلى صفحةٍ تطلب الدخول وجلستُه ما زالت حيّة.
 *
 * وهو أسوأُ ما يكون في المزايدة: الدقيقةُ الأخيرة من المزاد هي بالضبط اللحظةُ
 * التي مضى فيها على دخول العميل أكثرُ من ربع ساعة.
 *
 * لماذا يجوز التجديدُ هنا
 * ======================
 * الوسيطُ يحصر التجديدَ في التنقّل خوفاً من **السباق**: طلبان يجدّدان معاً،
 * فيصل الثاني برمزٍ دار وأبطله الأوّل، و`RefreshTokenReused` **تُلغي كلَّ رموز
 * العميل**. وأفعالُ الخادم لا تتسابق: Next يُرسلها من الصفحة الواحدة **واحداً
 * بعد واحد** في طابور. وفعلُ الخادم يستطيع كتابةَ الكوكي — وهو الشرطُ الآخر
 * الذي كتبه الوسيط («تحديثٌ لا يُحفَظ خروجٌ قسريّ»).
 */

import { cookies } from "next/headers";

import { backendUrl } from "@/lib/api";
import { authHeader, clearSession, hasSession, refreshToken, setSession } from "@/lib/session";

export async function authedHeaders(): Promise<Record<string, string>> {
  const store = await cookies();
  if (hasSession(store)) return authHeader(store);

  const refresh = refreshToken(store);
  if (!refresh) return {};

  // `fetch` عارياً كما في `middleware.ts` لا `api.POST` — وليس لسبب الوسيط
  // (سقوطُ الجسم هناك)، بل لأن الرفضَ هنا **جوابٌ** يُتّخذ عليه قرار، و
  // `request()` ترمي على كلّ رفض.
  let answer: Response;
  try {
    answer = await fetch(`${backendUrl()}/api/v1/auth/refresh/`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "Accept-Language": "ar" },
      body: JSON.stringify({ refresh }),
      cache: "no-store",
    });
  } catch {
    // الخلفيّة لم تُجب: لا تُمسح الجلسة على عطلِ شبكة — العميلُ لم يُخطئ.
    return {};
  }

  if (!answer.ok) {
    // رمزُ تحديثٍ مرفوض لن يُقبل في المحاولة التالية، وتركُه يعني رفضاً في كلّ
    // فعلٍ بلا عرضٍ للدخول. يُمسح الاثنان معاً كما في الوسيط.
    clearSession(store);
    return {};
  }

  const pair = (await answer.json()) as { access: string; refresh?: string; expires_in?: number };
  setSession(store, { access: pair.access, refresh: pair.refresh, expiresIn: pair.expires_in });
  return { Authorization: `Bearer ${pair.access}` };
}
