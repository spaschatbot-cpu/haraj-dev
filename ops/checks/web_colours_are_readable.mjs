/**
 * لا صنف لونٍ راسبِ التباين في قناة العميل.
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
 * الطريقة، وحدُّها
 * ================
 * فحصٌ نصّي على أصناف Tailwind: يمنع الأصناف الراسبة أن تعود، ولا يدّعي أنه
 * يقيس الصفحة المرسومة — لا متصفّح هنا، والتتالي لا يُحسب بلا واحد. فهو حارسُ
 * انحدارٍ لا شهادةُ وصول، وهذا هو حدّه بالضبط ويجب أن يُقال.
 *
 * لماذا `border-neutral-200` مسموح وهو أخفت
 * =========================================
 * لأنه حدُّ بطاقةٍ لا حدُّ عنصرِ تحكّم: المعيار 1.4.11 يشترط ٣:١ لما يُميّز
 * مكوّناً أو حالته، لا لكل خطٍّ على الشاشة. حدُّ بطاقةٍ زخرفةٌ يبقى ما تحتها
 * مفهوماً بدونه — وفرضُ ٣:١ عليه يجعل الصفحة شبكةَ خطوطٍ سوداء بلا أن يقرأ
 * أحدٌ حرفاً أوضح.
 */

import { readdirSync, readFileSync, statSync } from "node:fs";
import { dirname, extname, join } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..", "..");
const WEB = join(ROOT, "web");
const ROOTS = ["app", "features"];

/**
 * الأصناف الممنوعة، ولكلٍّ سببُه ونسبتُه وبديلُه.
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

const hits = [];
for (const root of ROOTS) {
  for (const path of files(join(WEB, root))) {
    const lines = readFileSync(path, "utf8").replace(/\r\n/g, "\n").split("\n");
    lines.forEach((line, index) => {
      for (const rule of BANNED) {
        //: حدود الكلمة تمنع مطابقة `border-neutral-300` داخل
        //: `hover:border-neutral-3000` أو ما شابه — ومطابقةٌ زائدة في حارسٍ
        //: تُفقده الثقة أسرع مما تُفقده مطابقةٌ ناقصة.
        if (new RegExp(`(^|[^\\w-])${rule.className}(?![\\w-])`).test(line)) {
          hits.push({ path: path.slice(ROOT.length + 1), line: index + 1, rule });
        }
      }
    });
  }
}

if (hits.length > 0) {
  console.error("أصناف لونٍ لا تبلغ حدّ التباين في قناة العميل:\n");
  for (const { path, line, rule } of hits) {
    console.error(`  ${path}:${line}`);
    console.error(
      `    ${rule.className} — النسبة ${rule.ratio}، والحدّ ${rule.floor}`,
    );
    console.error(`    البديل: ${rule.instead}`);
  }
  console.error("");
  console.error("العميل يقرأ على جوال في ضوء النهار، لا على شاشةٍ في غرفةٍ مظلمة.");
  process.exit(1);
}

console.log("لا صنف لونٍ راسب في الويب.");
