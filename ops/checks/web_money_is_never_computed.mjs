/**
 * لا صفحة تحسب سعراً بنفسها — T1009، والمادة ٣-٢ في الويب.
 *
 * Two rules, one file, because they are the same rule seen from two sides.
 *
 * **1. No amount ever becomes a number.** `Number("0.1") + Number("0.2")` is
 * `0.30000000000000004` in JavaScript exactly as it is in Python, and the
 * backend went to the trouble of sending every amount as a decimal *string* so
 * that it would reach a screen unchanged. A `Number(price)` anywhere in the web
 * undoes that at the last possible moment, in the place where it is hardest to
 * see: the value still looks right for every amount somebody tests with.
 *
 * **2. No page works out a price.** T1009's acceptance says it directly —
 * *فحص نصّي يؤكد أن لا صفحة تحسب سعراً بنفسها*. The price a vehicle page shows
 * is `reserve_price` as the server sent it. A "current price" derived here from
 * bids, a minimum increment added to something, a total assembled from parts:
 * each is a second answer to a question the backend already answers, and the
 * backend's answer is the one the money moves against.
 *
 * What is checked
 * ---------------
 * Arithmetic (`+ - * /`), `Number(`, `parseFloat(`, `parseInt(` and
 * `toFixed(` applied to an identifier whose name says it is money. The name list
 * is the enforcement surface, so it names the fields the contract actually
 * carries rather than trying to guess at intent.
 *
 * Comments are stripped first: a comment cannot compute anything, and the file
 * most likely to *discuss* `Number(price)` is the module that exists to forbid
 * it.
 *
 * Run:  node ops/checks/web_money_is_never_computed.mjs
 */

import { readdir, readFile } from "node:fs/promises";
import { join, relative, sep } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const ROOT = join(fileURLToPath(import.meta.url), "..", "..", "..");
const WEB = join(ROOT, "web");

const SKIP = new Set(["node_modules", ".next", "dist", "coverage"]);
const EXTENSIONS = [".ts", ".tsx"];

const EXEMPT = new Set([
  // Generated from the schema; it declares the string types this file protects.
  join("web", "lib", "api", "schema.ts"),
  // The guard's own test (T1024/J4), which writes the four offending shapes as
  // source strings and asserts each is caught. A guard nobody has watched fail
  // is a promise, so proving it has to be possible — and the proof necessarily
  // contains the thing being forbidden.
  join("web", "lib", "__tests__", "wallet.test.ts"),
  // Proves these guards can fail, by seeding each forbidden shape as a source
  // string. A guard nobody has watched fail is a promise — and this file is
  // where one that matched nothing was caught.
  join("web", "lib", "__tests__", "contract.test.ts"),
]);

//: Identifiers that hold an amount. Taken from the contract's own field names,
//: plus the words people reach for when introducing a local variable for one.
const MONEY_NAMES = [
  "reserve_price",
  "amount",
  "amount_paid",
  "balance",
  "outstanding",
  "price",
  "total_due",
  "deposit_required",
  "minimum_bid",
];

const NAMES = MONEY_NAMES.join("|");

const FORBIDDEN = [
  {
    pattern: new RegExp(`\\b(?:Number|parseFloat|parseInt)\\s*\\([^)]*\\b(?:${NAMES})\\b`),
    why: "تحويل مبلغ إلى عدد — `0.1 + 0.2` في جافاسكربت ليس `0.3`",
  },
  {
    pattern: new RegExp(`\\b(?:${NAMES})\\b\\s*[+\\-*/]\\s*(?!\\s*[)\\],;])`),
    why: "حساب على مبلغ — الخادم يقرّر المبلغ والواجهة تعرضه",
  },
  {
    pattern: new RegExp(`[+\\-*/]\\s*\\b(?:${NAMES})\\b`),
    why: "حساب على مبلغ — الخادم يقرّر المبلغ والواجهة تعرضه",
  },
  {
    pattern: new RegExp(`\\b(?:${NAMES})\\b[^\\n]{0,40}\\.toFixed\\s*\\(`),
    why: "تقريب مبلغ — يُعرض كما وصل بالضبط",
  },
  {
    // T1025 / J3: **a price weighed against something.** Arithmetic is not the
    // only way the web can reach a money decision — `amount < minimum_bid`
    // computes nothing and decides everything. A comparison against a number
    // literal or against another amount is the shape of «هل يكفي؟», and that
    // question is answered in `apps/bidding` and `apps/money`, once.
    //
    // Comparison against a plain *variable* is deliberately not matched:
    // `bucket.kind === filter` is routing, and a guard that cannot tell those
    // apart is a guard people switch off.
    //
    // `String.raw`, because in a plain template literal `\b` is the backspace
    // character and the pattern would silently match nothing — a check that
    // reports green without looking, which is worse than no check at all.
    pattern: new RegExp(
      String.raw`\b(?:${NAMES})\b\s*(?:[<>]=?|={2,3}|!==?)\s*(?:-?\d|["']\d|\b(?:${NAMES})\b)`,
    ),
    why: "موازنة مبلغ برقم أو بمبلغ — «هل يكفي؟» يُجاب في الخلفية",
  },
];

async function* walk(directory) {
  for (const entry of await readdir(directory, { withFileTypes: true })) {
    if (SKIP.has(entry.name)) continue;
    const path = join(directory, entry.name);
    if (entry.isDirectory()) yield* walk(path);
    else if (EXTENSIONS.some((extension) => entry.name.endsWith(extension))) yield path;
  }
}

/** Blank out comments, keeping line numbers. A comment computes nothing. */
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
      for (const { pattern, why } of FORBIDDEN) {
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
    console.error("المبالغ تُعرض كما وصلت، ولا تُحسب في الويب:\n");
    for (const item of found) console.error(`  ${item}`);
    console.error(
      `\n${found.length} مخالفة. الخادم يقرّر والواجهة تعرض (المادتان ٣-٢ و٤-٥).`,
    );
    process.exit(1);
  }
  console.log("لا حساب على مبلغ في الويب.");
}
