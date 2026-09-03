/**
 * لا منطق أهلية في الويب — T1014 / J3، ونظير `one_eligibility_gate.py`.
 *
 * J7 is the criterion this protects: *عميل غير مؤهَّل يُرفض بنفس السبب
 * المُعدَّد الذي يظهر في التطبيق، **حرفياً***. Two channels giving one customer
 * the same refusal is not something you can achieve by being careful in two
 * places — it is something you achieve by there being one place. That place is
 * `apps/bidding/eligibility.py`, which has its own guard on the backend side
 * (phase 006) refusing any second reader of the facts eligibility is decided on.
 *
 * This is the same rule pointed at `web/`, and it is enforced differently for a
 * reason worth stating up front: on the backend, *reading* one of those facts
 * outside the gate is deciding with it, so reading is what is forbidden. In the
 * web the opposite is true — showing a deposit, a held balance or an outstanding
 * amount is this product's wallet screen, and a guard that forbade naming them
 * would forbid the feature.
 *
 * So it refuses the two shapes that are unambiguous:
 *
 * 1. **two eligibility fields compared with each other** — «هل معه ما يكفي؟» has
 *    exactly that shape and no innocent construct does. A screen that shows a
 *    number renders it; a screen that decides weighs it against another;
 * 2. **a refusal reason spelled out in shipped code** — `no_deposit`,
 *    `unpaid_dues`. A screen that branches on one is a step from a screen that
 *    *phrases* it, and a phrase here is a sentence that disagrees with the app's
 *    about the same refusal. The server sends `message` ready to render.
 *
 * A price compared against a floor — `amount < minimum_bid` — is the same class
 * of mistake and is caught by `web_money_is_never_computed.mjs`, which owns the
 * money names. Two guards, no overlap, and neither guessing.
 *
 * Run:  node ops/checks/web_no_eligibility_logic.mjs
 */

import { readdir, readFile } from "node:fs/promises";
import { join, relative, sep } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const ROOT = join(fileURLToPath(import.meta.url), "..", "..", "..");
const WEB = join(ROOT, "web");

const SKIP = new Set(["node_modules", ".next", "dist", "coverage"]);
const EXTENSIONS = [".ts", ".tsx"];

const EXEMPT = new Set([
  // Generated from the schema: it declares the field names, it does not read
  // them.
  join("web", "lib", "api", "schema.ts"),
  // Writes offending files on purpose, to prove this guard can fail.
  join("web", "lib", "__tests__", "bidding.test.ts"),
  // Proves these guards can fail, by seeding each forbidden shape as a source
  // string. A guard nobody has watched fail is a promise — and this file is
  // where one that matched nothing was caught.
  join("web", "lib", "__tests__", "contract.test.ts"),
]);

//: The fields a bid's eligibility is decided from, named as the API sends them.
//:
//: Taken from `ops/checks/one_eligibility_gate.py`, but **not** enforced the
//: same way, and the difference is the design of this file. The backend guard
//: forbids *reading* these outside the gate, because on that side reading one is
//: deciding with it. The web's relationship to them is the opposite: showing a
//: deposit, a held balance or an outstanding amount is this product's wallet
//: screen, and a rule that forbade naming them would forbid the feature.
//:
//: A text check cannot tell display from decision for a single field — and a
//: guard that guesses produces a wall of false positives, which is a guard
//: people switch off. So it refuses only the two shapes that are unambiguous.
const FACTS = [
  "insurance_free",
  "insurance_held",
  "insurance_locked",
  "outstanding_dues",
  "deposit_required",
  "required_deposit",
  "phone_verified_at",
  "exception_note",
  "exception_granted_by",
  "is_open_for_bidding",
];

//: The enumerated refusal reasons, from `apps/bidding/models.RefusalReason`.
const REASONS = [
  "no_deposit",
  "unpaid_dues",
  "auction_not_live",
  "auction_ended",
  "vehicle_not_biddable",
  "below_floor",
  "phone_not_verified",
  "profile_incomplete",
  "own_vehicle",
];

const FACT_NAMES = FACTS.join("|");
const COMPARISON = "(?:[<>]=?|={2,3}|!==?)";

const FORBIDDEN = [
  {
    // **Two eligibility fields compared with each other.** «هل معه ما يكفي؟» has
    // exactly this shape and no innocent one does: a screen showing a number
    // renders it, a screen deciding weighs it against another. This is the
    // question `check_eligibility` exists to be the only answer to.
    // `String.raw`, not a plain template: in a template literal `\b` is the
    // backspace character, not a word boundary, and the regex silently becomes
    // one that matches nothing. A guard that matches nothing passes every file
    // and reports green — the worst failure mode a check has, and one no test of
    // the *clean* tree can detect. The test that seeds a violation is what
    // caught it here.
    pattern: new RegExp(
      String.raw`\b(?:${FACT_NAMES})\b[^\n]{0,20}${COMPARISON}[^\n]{0,20}\b(?:${FACT_NAMES})\b`,
    ),
    why: "موازنة شرط أهلية بآخر — «هل معه ما يكفي؟» يُجاب في الخلفية وحدها",
    // Everywhere, tests included: a test that weighs a deposit against a
    // requirement is a test of logic that must not exist.
    inTests: true,
  },
  {
    // **A refusal reason spelled out in shipped code.** A screen that branches on
    // one is a step from a screen that *phrases* it, and a phrase here is a
    // sentence that disagrees with the app's about the same refusal. The server
    // sends `message` ready to render.
    pattern: new RegExp(`["'\`](?:${REASONS.join("|")})["'\`]`),
    why: "سببُ رفضٍ مكتوب في الويب — المجموعة مغلقة في الخلفية، والنسخة هي ما يشيخ",
    // Shipped code only. A test proving a refusal passes through untouched has
    // to name one, and a stale name in a test surfaces as a failing test — a
    // smaller and much louder problem than a stale copy on a screen.
    inTests: false,
  },
];

//: A test file, by directory or by suffix.
const IS_TEST = /(^|[\\/])__tests__[\\/]|\.test\.tsx?$/;

async function* walk(directory) {
  for (const entry of await readdir(directory, { withFileTypes: true })) {
    if (SKIP.has(entry.name)) continue;
    const path = join(directory, entry.name);
    if (entry.isDirectory()) yield* walk(path);
    else if (EXTENSIONS.some((extension) => entry.name.endsWith(extension))) yield path;
  }
}

/** Blank out comments, keeping line numbers. A comment decides nothing. */
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

export async function violations(root = WEB) {
  const found = [];

  for await (const path of walk(root)) {
    const relativePath = relative(ROOT, path);
    if (EXEMPT.has(relativePath.split("/").join(sep))) continue;

    const lines = withoutComments(await readFile(path, "utf8")).split(/\r?\n/);
    lines.forEach((line, index) => {
      const isTest = IS_TEST.test(relativePath);
      for (const { pattern, why, inTests } of FORBIDDEN) {
        if (isTest && !inTests) continue;
        if (pattern.test(line)) {
          found.push(`${relativePath}:${index + 1}: ${why}`);
          return;
        }
      }
    });
  }
  return found;
}

if (import.meta.url === pathToFileURL(process.argv[1]).href) {
  const found = await violations();
  if (found.length) {
    console.error("الأهلية تُقرَّر في الخلفية وحدها:\n");
    for (const item of found) console.error(`  ${item}`);
    console.error(
      `\n${found.length} مخالفة. قناتان بجواب واحد لا تُبنى بالانتباه في` +
        " موضعين، بل بوجود موضع واحد (J7).",
    );
    process.exit(1);
  }
  console.log("لا منطق أهلية في الويب.");
}
