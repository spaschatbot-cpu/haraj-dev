/**
 * لا مكوّن خادمٍ يكتب كوكي — Next يمنعه، ولا اختبار عندنا يراه.
 *
 * العطل الذي وُلد هذا لأجله (قِيس في المتصفّح، 2026-09-07)
 * =======================================================
 * `lib/flash.ts` كانت تُصدّر `takeFlash(store)`: تقرأ الرسالة ثم **تحذف
 * الكوكي في السطر التالي**. ونادتها **سبع صفحات**، كلّها مكوّنات خادم. وNext
 * يرفض تعديل كوكي في رندرة:
 *
 *   Error: Cookies can only be modified in a Server Action or Route Handler
 *
 * فكان كلُّ فعلٍ يضع رسالةً ثم يحوّل — مزايدة مرفوضة، سحبُ مزايدة، شحنُ
 * محفظة، طلبُ استرداد — ينتهي بشاشة **خطأ خادم** بدل جملة الخادم. أي أن
 * الرسالة التي بُني `flash.ts` كلّه لإيصالها لم تصل مرةً واحدة.
 *
 * **ولماذا لم يمسكه اختبار:** الاختبارات تستبدل `next/headers` بمخزنٍ متساهل
 * (`vi.mock`) يقبل `set` و`delete` في أي وقت. فسبع شاشات مرّت خضراءَ على عطلٍ
 * يقع في كل تحميل. ولا يمكن لهذا أن يُصلَح باختبارٍ آخر على المخزن نفسه —
 * القاعدة عن **أين** يُنادى الشيء، لا عن ماذا يفعل.
 *
 * ما يُفحص
 * ========
 * ملفّات الرندرة — `app/**` من `page.tsx` و`layout.tsx` و`template.tsx`
 * و`default.tsx` — لا تستورد ولا تنادي شيئاً يكتب كوكي:
 *
 * * الدوالّ المصدَّرة التي تكتب: `setFlash` · `setSession` · `clearSession`؛
 * * ولا `store.set(` / `store.delete(` مباشرةً على مخزن الكوكيز.
 *
 * ويُستثنى ملفٌّ يعلن `"use server"` في أوّله: ذاك فعلُ خادمٍ لا رندرة —
 * ويُقرأ من الملفّ نفسه لا من قائمةٍ هنا، فلا يُمنَح استثناءً بالنسيان.
 *
 * وهذا الفحص **يصرخ إن لم يجد ما يحرسه**: صفرُ ملفّات رندرةٍ يعني أن المسار
 * تغيّر وأن الحارس صار يفحص العدم.
 *
 * Run:  node ops/checks/web_renders_never_write_cookies.mjs
 */

import { readdir, readFile } from "node:fs/promises";
import { join, relative, sep } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const ROOT = join(fileURLToPath(import.meta.url), "..", "..", "..");
const WEB = join(ROOT, "web");

const SKIP = new Set(["node_modules", ".next", "dist", "coverage"]);

//: أسماء الملفّات التي يُرندرها Next كمكوّنات خادم. `route.ts` ليست منها —
//: معالجُ مسارٍ يجوز له أن يكتب، وهو أحد المواضع الثلاثة التي يجوز فيها.
const RENDERED = new Set(["page.tsx", "layout.tsx", "template.tsx", "default.tsx"]);

//: الدوالّ التي تكتب كوكي. أسماؤها من `lib/` نفسها، فإعادةُ تسمية واحدةٍ
//: تُظهرها هنا مفقودةً بدل أن تُسقط الحراسة بصمت (انظر التحقّق أدناه).
const WRITERS = ["setFlash", "setSession", "clearSession"];

//: كتابةٌ مباشرة على المخزن، لمن يكتبها بيده بدل استيراد دالّة.
const DIRECT = /\b(?:store|cookieStore|jar)\s*\.\s*(?:set|delete)\s*\(/;

async function* walk(directory) {
  for (const entry of await readdir(directory, { withFileTypes: true })) {
    if (SKIP.has(entry.name)) continue;
    const path = join(directory, entry.name);
    if (entry.isDirectory()) yield* walk(path);
    else yield path;
  }
}

/** يُفرَّغ التعليق: تعليقٌ لا يكتب كوكي، وهذا الملفّ يذكر كل اسمٍ يمنعه. */
function withoutComments(source) {
  const out = [];
  let inBlock = false;
  for (let line of source.split(/\r?\n/)) {
    if (inBlock) {
      const close = line.indexOf("*/");
      if (close === -1) {
        out.push("");
        continue;
      }
      line = line.slice(close + 2);
      inBlock = false;
    }
    let cleaned = line.replace(/\/\*[\s\S]*?\*\//g, " ");
    const open = cleaned.indexOf("/*");
    if (open !== -1) {
      cleaned = cleaned.slice(0, open);
      inBlock = true;
    }
    const slashes = cleaned.search(/(^|[^:])\/\//);
    if (slashes !== -1) cleaned = cleaned.slice(0, slashes + 1);
    out.push(cleaned);
  }
  return out.join("\n");
}

export async function violations(web = WEB) {
  const found = [];
  let rendered = 0;

  //: أوّلاً: الأسماء الممنوعة ما زالت موجودة. اسمٌ اختفى يعني حارساً يفحص
  //: كلمةً لا وجود لها — وهو حارسٌ يمرّ دائماً.
  const flashSource = await readFile(join(web, "lib", "flash.ts"), "utf8");
  const sessionSource = await readFile(join(web, "lib", "session.ts"), "utf8");
  const declared = flashSource + sessionSource;
  for (const name of WRITERS) {
    if (!new RegExp(`export function ${name}\\b`).test(declared)) {
      found.push(
        `lib: \`${name}\` لم تعد مصدَّرة، والفحص يمنع نداءها في رندرة. ` +
          `عُدّل الاسم؟ حدِّث القائمة في هذا الملفّ.`,
      );
    }
  }

  for await (const path of walk(join(web, "app"))) {
    const name = path.slice(path.lastIndexOf(sep) + 1);
    if (!RENDERED.has(name)) continue;
    rendered += 1;

    const source = await readFile(path, "utf8");
    //: `"use server"` في أوّل الملفّ يجعله فعلَ خادمٍ لا رندرة.
    if (/^\s*(?:\/\*[\s\S]*?\*\/\s*)?["']use server["']/.test(source)) continue;

    const relativePath = relative(ROOT, path);
    const lines = withoutComments(source).split(/\r?\n/);
    lines.forEach((line, index) => {
      for (const writer of WRITERS) {
        if (new RegExp(`\\b${writer}\\s*\\(`).test(line)) {
          found.push(
            `${relativePath}:${index + 1}: \`${writer}(\` في رندرة — ` +
              `الكوكي يُكتب في فعل خادمٍ أو معالج مسارٍ أو الوسيط، لا هنا`,
          );
        }
      }
      if (DIRECT.test(line)) {
        found.push(
          `${relativePath}:${index + 1}: كتابةٌ مباشرة على مخزن الكوكيز في رندرة`,
        );
      }
    });
  }

  if (rendered === 0) {
    found.push(
      "web/app: لا ملفّ رندرةٍ واحد — تغيّر المسار أو الأسماء، والفحص يحرس العدم.",
    );
  }

  return found;
}

if (import.meta.url === (process.argv[1] ? pathToFileURL(process.argv[1]).href : "")) {
  const found = await violations();
  if (found.length) {
    console.error("كوكي يُكتب في رندرة — وNext يرفضه في زمن التشغيل:\n");
    for (const item of found) console.error(`  ${item}`);
    console.error(
      `\n${found.length} مخالفة. الكتابة في فعل خادمٍ أو معالج مسارٍ أو الوسيط.`,
    );
    process.exit(1);
  }
  console.log("لا رندرةَ تكتب كوكي.");
}
