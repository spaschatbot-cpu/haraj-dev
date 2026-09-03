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
 * This is the same guard pointed at `web/`. What it refuses is the web forming
 * an opinion about whether somebody may bid:
 *
 * 1. **reading an eligibility fact** — a deposit, dues, a hold, an exception, a
 *    verification flag. The web may render a number the server sent; it may not
 *    look one up in order to decide something;
 * 2. **comparing an amount against a floor** — `amount < minimum`,
 *    `>= deposit_required`. A minimum computed here is a bid the web refuses
 *    that the server would have taken, or offers that the server will refuse;
 * 3. **naming a refusal reason** — writing `no_deposit` or `unpaid_dues` in the
 *    web is writing a second copy of a closed set, and the copy is what goes
 *    stale when a reason is added.
 *
 * Why (3) is worth forbidding even though it looks harmless
 * ---------------------------------------------------------
 * A screen that branches on a reason is one step from a screen that *phrases*
 * that reason, and a phrase here is a sentence that disagrees with the app's for
 * the same refusal. The server sends `message` ready to render; a channel that
 * needs to know which reason it is, to do something other than display it, is a
 * channel making a decision.
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
]);

//: The facts eligibility is decided on. Mirrors `FACTS` in
//: `ops/checks/one_eligibility_gate.py`, deliberately: two channels enforcing
//: the same rule against two different lists is the drift the rule forbids.
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

const FORBIDDEN = [
  {
    pattern: new RegExp(`\\b(?:${FACT_NAMES})\\b`),
    why: "قراءة شرط أهلية — القرار في apps/bidding/eligibility.py وحده",
    // Everywhere, tests included: a test that reads a deposit in order to
    // decide something is a test of logic that must not exist.
    inTests: true,
  },
  {
    pattern: new RegExp(`["'\`](?:${REASONS.join("|")})["'\`]`),
    why: "سببُ رفضٍ مكتوب في الويب — المجموعة مغلقة في الخلفية، والنسخة هي ما يشيخ",
    // Shipped code only. A test proving that a refusal is passed through
    // untouched has to name a refusal, and forbidding that would forbid testing
    // the rule. A stale name in a test surfaces as a test that no longer matches
    // reality — a smaller and much louder problem than a stale copy on a screen.
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
