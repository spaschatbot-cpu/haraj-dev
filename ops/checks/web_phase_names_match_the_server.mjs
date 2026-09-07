/**
 * أسماء التبويبات في الويب هي أسماء الخادم نفسها — لا مرادفاتها.
 *
 * لماذا هذا الفحص موجود
 * =====================
 * كُتب هذا الملف بعد عطلٍ حقيقي، لا احتياطاً: سمّى الخادمُ الطورَ الأول
 * `soon` وسمّاه الويبُ `upcoming`، فكان تبويب «قريباً» يبعث كلمةً يرفضها
 * الخادم بـ400 ويردّ «"upcoming" ليس خياراً صالحاً». التبويب كان مكسوراً
 * تماماً، والحزمة كلها خضراء — لأن اختبارات الويب تسأل الويبَ عن نفسه.
 *
 * والأسوأ أن التعليق فوق القائمة كان يقول حرفياً «الحالات الثلاث كما
 * يسمّيها الخادم؛ التسمية عقد لا اختيار عرض». تعليقٌ يقول القاعدة لا يطبّقها،
 * وهذا الفرق بالضبط هو ما يوجد الحارس من أجله.
 *
 * لماذا يقرأ المخطط لا العميل المولَّد
 * ===================================
 * `backend/openapi/schema.yaml` هو العقد المثبَّت — مصدرُ العميل المولَّد
 * نفسه. مقارنةُ الويب بالعميل المولَّد تقارنه بنسخةٍ قد تكون قديمة؛ ومقارنته
 * بالمخطط تسأل السؤال الصحيح: هل يسمّي الويبُ ما يسمّيه الخادم؟
 *
 * يُقرأ المخطط بمُطابِقٍ نصّي لا بمُحلّل YAML عمداً: هذا فحصٌ يعمل بلا
 * تنصيب، وحزمةُ YAML ليست في تبعيات الويب ولا يجوز أن تُضاف من أجل حارس.
 */

import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..", "..");
const SCHEMA = join(ROOT, "backend", "openapi", "schema.yaml");
const WEB_PHASES = join(ROOT, "web", "lib", "api", "phases.ts");

/** أسماء الأطوار كما يعلنها المخطط في `PhaseCounts` — الحقول المطلوبة. */
function phasesFromSchema() {
  //: نهايات الأسطر تُوحَّد أولاً. المخطط مولَّد على Windows فيصل بـCRLF، و`\n`
  //: في نمطٍ يبحث عن سطرٍ تالٍ لا يطابق `\r\n` — فلا يجد الحارسُ ما يحرسه.
  //: وقد حدث ذلك فعلاً في أول تشغيلٍ لهذا الملف.
  const text = readFileSync(SCHEMA, "utf8").replace(/\r\n/g, "\n");
  const block = text.match(/\n {4}PhaseCounts:\n([\s\S]*?)(?=\n {4}\w)/);
  if (block === null) {
    throw new Error(
      "PhaseCounts غير موجود في المخطط. إن أُعيدت تسميته فحدّث هذا الفحص — " +
        "حارسٌ لا يجد ما يحرسه يجب أن يصرخ، لا أن يمرّ.",
    );
  }
  //: `\n?` على آخر عنصر: الكتلة تنتهي عند بداية المفتاح التالي، فآخر سطر
  //: فيها بلا سطرٍ جديد بعده. بدونها يسقط آخر طورٍ من القائمة صامتاً —
  //: ويصير الحارس يقارن اثنين بثلاثة ويفشل دائماً بسببٍ خاطئ.
  const required = block[1].match(/\n {6}required:\n((?: {6}- \w+\n?)+)/);
  if (required === null) {
    throw new Error("PhaseCounts بلا `required` — لا أسماء أطوار لأقارنها.");
  }
  return [...required[1].matchAll(/- (\w+)/g)].map((m) => m[1]).sort();
}

/** أسماء الأطوار كما يكتبها الويب. */
function phasesFromWeb() {
  const text = readFileSync(WEB_PHASES, "utf8").replace(/\r\n/g, "\n");
  const line = text.match(/export const PHASES = \[([^\]]*)\]/);
  if (line === null) {
    throw new Error(
      "PHASES غير موجودة في web/lib/api/phases.ts. إن انتقلت فحدّث هذا الفحص.",
    );
  }
  return [...line[1].matchAll(/"([^"]+)"/g)].map((m) => m[1]).sort();
}

const server = phasesFromSchema();
const web = phasesFromWeb();

if (server.join(",") !== web.join(",")) {
  console.error("أسماء الأطوار في الويب لا تطابق العقد.");
  console.error(`  الخادم: ${server.join(", ")}`);
  console.error(`  الويب:  ${web.join(", ")}`);
  console.error("");
  console.error(
    "الاسم عقدٌ لا اختيار عرض: كلمةٌ لا يعرفها الخادم تعني تبويباً يردّ 400.",
  );
  console.error("العَلَم العربي في الواجهة، والاسم على السلك كما قاله الخادم.");
  process.exit(1);
}

console.log("أسماء أطوار الويب مطابقة للعقد.");
