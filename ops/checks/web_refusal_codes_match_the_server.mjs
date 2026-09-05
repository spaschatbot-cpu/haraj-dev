/**
 * تعداد أسباب الرفض في الويب هو تعداد الخادم — لا نصفه.
 *
 * لماذا وُجد هذا الفحص
 * ====================
 * للتطبيق حارسٌ يفعل هذا منذ T710
 * (`mobile/test/architecture/refusal_codes_match_the_server_test.dart`)، وقد
 * أمسك فعلاً: يوم أُضيف `refund_pending` إلى `RefusalReason` سقط في الحال،
 * فلم يتسرّب فرقٌ بين قناة وقناة.
 *
 * وللويب لم يكن نظير. فقائمته في `lib/__tests__/bidding.test.ts` كانت ستّة
 * رموز والخادم يعدّ عشرة — أربعة غائبة قبل هذا التغيير أصلاً
 * (`auction_not_live`، `vehicle_not_biddable`، `profile_incomplete`،
 * `unpaid_dues` موجود لكن الثلاثة الأخرى لا). قائمةٌ ناقصة لا تُنتج فشلاً،
 * فلا يمسكها أحد.
 *
 * ولماذا يهمّ رغم أن الويب لا يقرّر شيئاً
 * =====================================
 * لا يقرّر، لكنه **يتفرّع**: زرّ «وثّق جوالك» عند `phone_not_verified`، و«ألغِ
 * طلب الاسترداد» عند `refund_pending`. فرعٌ مكتوبٌ على قائمةٍ لا تطابق الخادم
 * لا يُفعَّل أبداً — والعميل يرى جملةً صحيحة بلا الفعل الذي تصفه.
 *
 * وهو معيار J7 حرفياً: «عميل غير مؤهَّل يُرفض بنفس السبب المُعدَّد في
 * القناتين».
 *
 * المصدر واحد: `backend/apps/bidding/models.py::RefusalReason`.
 */

import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..", "..");
const BACKEND = join(ROOT, "backend", "apps", "bidding", "models.py");
const WEB_TEST = join(ROOT, "web", "lib", "__tests__", "bidding.test.ts");

/** الرموز كما يعدّدها `RefusalReason` في الخادم. */
function serverCodes() {
  const text = readFileSync(BACKEND, "utf8").replace(/\r\n/g, "\n");
  const block = text.match(
    /class RefusalReason\(models\.TextChoices\):\n((?: {4}\w+ = .*\n)+)/,
  );
  if (block === null) {
    throw new Error(
      "RefusalReason غير موجود في backend/apps/bidding/models.py. إن انتقل " +
        "فحدّث هذا الفحص — حارسٌ لا يجد ما يحرسه يجب أن يصرخ لا أن يمرّ.",
    );
  }
  return [...block[1].matchAll(/= "([\w_]+)"/g)].map((m) => m[1]).sort();
}

/** الرموز كما يعدّدها الويب في قائمة J7. */
function webCodes() {
  const text = readFileSync(WEB_TEST, "utf8").replace(/\r\n/g, "\n");
  const list = text.match(/const REFUSALS = \[\n([\s\S]*?)\n {2}\] as const;/);
  if (list === null) {
    throw new Error(
      "قائمة REFUSALS غير موجودة في web/lib/__tests__/bidding.test.ts. " +
        "إن انتقلت فحدّث هذا الفحص.",
    );
  }
  return [...list[1].matchAll(/\["([\w_]+)"/g)].map((m) => m[1]).sort();
}

const server = serverCodes();
const web = webCodes();

const missing = server.filter((code) => !web.includes(code));
const invented = web.filter((code) => !server.includes(code));

if (missing.length > 0 || invented.length > 0) {
  console.error("تعداد أسباب الرفض في الويب لا يطابق الخادم.\n");
  if (missing.length > 0) {
    console.error(`  ناقصٌ في الويب: ${missing.join(", ")}`);
  }
  if (invented.length > 0) {
    console.error(`  لا وجود له في الخادم: ${invented.join(", ")}`);
  }
  console.error("");
  console.error("المصدر: backend/apps/bidding/models.py::RefusalReason.");
  console.error(
    "معيار J7 — العميل يُرفض بنفس السبب المُعدَّد في القناتين، والفرعُ المكتوب",
  );
  console.error("على رمزٍ لا يرسله الخادم لا يُفعَّل أبداً.");
  process.exit(1);
}

console.log(`تعداد أسباب الرفض في الويب مطابق للخادم — ${server.length} سبباً.`);
