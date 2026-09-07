/**
 * لا زوج ألوانٍ راسبِ التباين في قناة العميل — ويُقاس، لا يُخمَّن.
 *
 * لماذا هذا الفحص موجود
 * =====================
 * قِيست ألوان الويب فوُجد فيها عطلان حقيقيان، وكلاهما ظهر في رقمٍ لا في نظرة:
 *
 * · `border-neutral-300` نسبته ١٫٤٨ على الأبيض، وكان حدَّ **أربعة عشر حقلاً**
 *   — منها خانة رقم الجوال في تسجيل الدخول، وخانة **مبلغ المزايدة**. مكوّن
 *   الواجهة حدُّه ٣:١ (WCAG 2.2، معيار 1.4.11)، وحقلٌ لا يُرى حدُّه يجعل
 *   النموذج مساحةً بيضاء لا يُعرف أين يُكتب فيها.
 * · `text-neutral-400` نسبته ٢٫٥٢، وكان يحمل عملة المحفظة و«لا توجد صورة».
 *
 * ولماذا أُعيد كتابته (T1032)
 * ============================
 * كان قائمةَ **أصناف ممنوعة** من لوحة Tailwind الافتراضية. ثم صار نظام
 * التصميم رموزاً في `app/globals.css` — `text-warn` و`bg-surface-low` — فلم
 * يعد الحارس يعرف أياً من الألوان التي تُرسم فعلاً على الشاشة: يمرّ أخضرَ
 * وهو لا يفحص شيئاً. وحارسٌ يمرّ دائماً لا يُميَّز عن حارسٍ لا يعمل.
 *
 * فصار يفعل شيئين:
 *
 * ١. **يقرأ الرموز من `globals.css` نفسه** ويحسب التباين بمعادلة WCAG 2.x —
 *    لا نسبةَ منسوخة في تعليق تتقادم يوم يُعدَّل لون؛
 * ٢. **يصرخ إن لم يجد ما يحرسه**: رمزٌ في القائمة أدناه غير معرَّف في
 *    `globals.css` يُسقط الفحص بدل أن يُتخطّى بصمت. فإعادةُ تسمية رمزٍ لا
 *    تُطفئ الفحص عنه.
 *
 * وتبقى القائمة السوداء القديمة: أصناف Tailwind الثلاثة ما زالت ممنوعة، لأن
 * شاشاتٍ أخرى في التطبيق ما زالت على اللوحة الافتراضية.
 *
 * حدّ الأداة
 * ==========
 * فحصٌ نصّي: يقيس أزواجاً **معلَنة هنا**، ولا يقيس الصفحة المرسومة — لا
 * متصفّح، ولا حساب للتتالي. فهو حارسُ انحدارٍ لا شهادةُ وصول، وزوجٌ يُرسم في
 * الشيفرة ولا يُذكر أدناه لا يفحصه أحد.
 *
 * لماذا `border-neutral-200` مسموح وهو أخفت
 * =========================================
 * لأنه حدُّ بطاقةٍ لا حدُّ عنصرِ تحكّم: المعيار 1.4.11 يشترط ٣:١ لما يُميّز
 * مكوّناً أو حالته، لا لكل خطٍّ على الشاشة. حدُّ بطاقةٍ زخرفةٌ يبقى ما تحتها
 * مفهوماً بدونه — وفرضُ ٣:١ عليه يجعل الصفحة شبكةَ خطوطٍ سوداء بلا أن يقرأ
 * أحدٌ حرفاً أوضح.
 *
 * Run:  node ops/checks/web_colours_are_readable.mjs
 */

import { readdirSync, readFileSync, statSync } from "node:fs";
import { dirname, extname, join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..", "..");
const WEB = join(ROOT, "web");
const TOKENS_FILE = join(WEB, "app", "globals.css");
const ROOTS = ["app", "features"];

/**
 * الأصناف الممنوعة من لوحة Tailwind الافتراضية، ولكلٍّ سببُه ونسبتُه وبديلُه.
 *
 * النسب من ألوان Tailwind الافتراضية على أبيض. حين يتغيّر لونٌ أساسي في
 * الإطار يجب أن تُعاد القياسات — وهذا التعليق هو ما يقول ذلك لمن يأتي بعد.
 */
const BANNED = [
  {
    className: "text-neutral-400",
    ratio: "2.52",
    floor: "4.5 (نصّ عادي — معيار 1.4.3)",
    instead: "text-neutral-500 (4.74)",
  },
  {
    className: "border-neutral-300",
    ratio: "1.48",
    floor: "3:1 (حدّ عنصر تحكّم — معيار 1.4.11)",
    instead: "border-neutral-500 (4.74)",
  },
  {
    className: "border-neutral-400",
    ratio: "2.52",
    floor: "3:1 (حدّ عنصر تحكّم — معيار 1.4.11)",
    instead: "border-neutral-500 (4.74)",
  },
];

/**
 * أزواج نظام التصميم كما تُرسم فعلاً، وحدُّ كلٍّ منها.
 *
 * `floor` رقمٌ لا شعار: **4.5** لنصٍّ عادي (1.4.3)، و**3** لنصٍّ كبير أو
 * لعنصرٍ يميّز حالة (1.4.6 و1.4.11). ومن يضيف زوجاً هنا يكتب حدَّه ولماذا هو
 * ذاك الحدّ — لا يختار الأسهل.
 */
const PAIRS = [
  { on: "on-surface", over: "surface", floor: 4.5, what: "نصّ الصفحة" },
  { on: "on-surface", over: "surface-lowest", floor: 4.5, what: "نصّ البطاقة" },
  { on: "on-surface", over: "surface-low", floor: 4.5, what: "نصّ اللوح الغائر" },
  { on: "on-surface", over: "surface-container", floor: 4.5, what: "نصّ الحبّة" },
  {
    on: "on-surface-variant",
    over: "surface-lowest",
    floor: 4.5,
    what: "تسميات المواصفات",
  },
  {
    on: "on-surface-variant",
    over: "surface-low",
    floor: 4.5,
    what: "تسميات داخل اللوح",
  },
  {
    on: "on-surface-variant",
    over: "surface-container",
    floor: 4.5,
    what: "نصّ زرّ معطَّل — «المزاد لم يبدأ بعد» يجب أن يُقرأ",
  },
  { on: "on-primary", over: "primary", floor: 4.5, what: "زرّ «مزايدة»" },
  { on: "on-secondary", over: "secondary", floor: 4.5, what: "الفعل الثانوي" },
  {
    on: "on-secondary-fixed",
    over: "secondary-fixed",
    floor: 4.5,
    what: "شارة «مفتوح للمزايدة»",
  },
  {
    on: "inverse-on-surface",
    over: "inverse-surface",
    floor: 4.5,
    what: "الرقم المرجعي فوق الصورة",
  },
  {
    on: "warn",
    over: "warn-surface",
    floor: 4.5,
    what: "شريط العدّاد تحت الساعة",
  },
  {
    on: "critical",
    over: "critical-surface",
    floor: 4.5,
    what: "شريط العدّاد في آخر عشر دقائق",
  },
  {
    on: "error",
    over: "surface-low",
    floor: 4.5,
    what: "«حادث» و«حريق» و«غرق» — الكلمة التي تقرّر شراءً",
  },
  {
    on: "secondary",
    over: "surface-lowest",
    floor: 4.5,
    what: "الروابط والتمييز",
  },
  {
    on: "outline",
    over: "surface-lowest",
    floor: 4.5,
    what: "«السابق» و«التالي» المعطَّلان، ونصّ الإرشاد في الحقول",
  },
  {
    on: "outline",
    over: "surface",
    floor: 4.5,
    what: "النصّ الخافت على خلفية الصفحة",
  },
];

function* files(dir) {
  for (const name of readdirSync(dir)) {
    const path = join(dir, name);
    if (statSync(path).isDirectory()) {
      yield* files(path);
    } else if ([".ts", ".tsx"].includes(extname(name))) {
      yield path;
    }
  }
}

/** الرموز كما هي في `globals.css` — المصدر الوحيد، لا نسخةٌ هنا. */
export function tokens(file = TOKENS_FILE) {
  const found = new Map();
  const source = readFileSync(file, "utf8");
  for (const [, name, hex] of source.matchAll(
    /--color-([a-z0-9-]+):\s*(#[0-9a-fA-F]{6})\s*;/g,
  )) {
    found.set(name, hex.toLowerCase());
  }
  return found;
}

/** الإضاءة النسبية، WCAG 2.x §relative-luminance. */
function luminance(hex) {
  const channels = [1, 3, 5].map((at) => parseInt(hex.slice(at, at + 2), 16) / 255);
  const [r, g, b] = channels.map((c) =>
    c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4,
  );
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

export function contrast(front, back) {
  const [a, b] = [luminance(front), luminance(back)].sort((x, y) => y - x);
  return (a + 0.05) / (b + 0.05);
}

export function violations({ web = WEB, tokensFile = TOKENS_FILE } = {}) {
  const found = [];

  //: أولاً: الرموز المعلَنة موجودة. رمزٌ مفقود يُسقط الفحص ولا يُتخطّى —
  //: فإعادةُ تسميةٍ لا تُطفئ الحراسة عنه بصمت.
  const palette = tokens(tokensFile);
  for (const pair of PAIRS) {
    for (const name of [pair.on, pair.over]) {
      if (!palette.has(name)) {
        found.push(
          `globals.css: الرمز \`--color-${name}\` غير معرَّف، والفحص يحرسه ` +
            `(${pair.what}). عُدّل الاسم أو حُذف اللون؟`,
        );
      }
    }
  }

  //: ثم: كل زوجٍ يُقاس.
  for (const pair of PAIRS) {
    const front = palette.get(pair.on);
    const back = palette.get(pair.over);
    if (!front || !back) continue;
    const ratio = contrast(front, back);
    if (ratio < pair.floor) {
      found.push(
        `globals.css: \`${pair.on}\` على \`${pair.over}\` نسبته ` +
          `${ratio.toFixed(2)} والحدّ ${pair.floor} — ${pair.what}`,
      );
    }
  }

  //: وأخيراً: أصناف Tailwind الممنوعة، حيثما بقيت شاشةٌ عليها.
  for (const root of ROOTS) {
    for (const path of files(join(web, root))) {
      const lines = readFileSync(path, "utf8").replace(/\r\n/g, "\n").split("\n");
      lines.forEach((line, index) => {
        for (const rule of BANNED) {
          //: حدود الكلمة تمنع مطابقة `border-neutral-300` داخل
          //: `border-neutral-3000` أو ما شابه.
          if (new RegExp(`(^|[\\s"'\`])${rule.className}([\\s"'\`]|$)`).test(line)) {
            found.push(
              `${path.slice(ROOT.length + 1)}:${index + 1}: \`${rule.className}\` ` +
                `نسبته ${rule.ratio} والحدّ ${rule.floor} — استعمل ${rule.instead}`,
            );
          }
        }
      });
    }
  }

  return found;
}

//: `process.argv[1]` غير معرَّف تحت `node -e`، والحارس يُستورَد من اختبارٍ
//: يثبت أنه يستطيع الفشل — فاستيرادٌ يرمي هو حارسٌ لا يُجرَّب.
const invoked = process.argv[1] ? pathToFileURL(process.argv[1]).href : "";
if (import.meta.url === invoked) {
  const found = violations();
  if (found.length) {
    console.error("تباينٌ راسب في قناة العميل:\n");
    for (const item of found) console.error(`  ${item}`);
    console.error(`\n${found.length} مخالفة.`);
    process.exit(1);
  }
  console.log(`لا زوج ألوانٍ راسب — ${PAIRS.length} زوجاً مقيساً في الويب.`);
}
