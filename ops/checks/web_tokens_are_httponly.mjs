/**
 * لا رمز جلسة خارج كوكيز HttpOnly — T1004 / J8.
 *
 * Spec 011 §8, and the sentence that justifies it: *ثغرة XSS واحدة على موقع
 * فيه محفظة تعني حساباً مسروقاً*. A token in `localStorage` is readable by any
 * script that runs on the page — a dependency three levels down the tree, an
 * analytics snippet, a reflected parameter. A token in an `HttpOnly` cookie is
 * not, and the same XSS then costs a session's worth of actions instead of the
 * account and the balance behind it.
 *
 * This is exactly the shape of rule that has to be enforced rather than
 * remembered, because the person who breaks it knows it. The shortcut is
 * written by somebody who has just spent an hour on the refresh flow and
 * decides their case is the exception — "only the refresh token", "only in
 * memory", "only in dev". Each is reasonable in the moment and none survives an
 * XSS.
 *
 * What it refuses
 * ---------------
 * 1. `localStorage` or `sessionStorage` touched anywhere in `web/`, at all. Not
 *    "touched with a token" — at all. Deciding whether a given key is a token
 *    means reading the variable's provenance, which a text check cannot do and
 *    a reviewer does not do reliably either. A screen that genuinely needs to
 *    remember a filter can ask for an exemption here, in a file somebody reads.
 * 2. `document.cookie`, which by definition cannot see an `HttpOnly` cookie and
 *    so is only ever reached for when somebody is about to store a token in a
 *    readable one.
 * 3. A cookie set with `httpOnly: false`, or with the flag missing, in the
 *    session module.
 *
 * Run:  node ops/checks/web_tokens_are_httponly.mjs
 */

import { readdir, readFile } from "node:fs/promises";
import { join, relative, sep } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const ROOT = join(fileURLToPath(import.meta.url), "..", "..", "..");
const WEB = join(ROOT, "web");

const SKIP = new Set(["node_modules", ".next", "dist", "coverage"]);
const EXTENSIONS = [".ts", ".tsx", ".mjs", ".js", ".jsx"];

//: Files allowed to name these APIs in *code*, and why. An exemption is a
//: decision somebody makes in this file, not a side effect of a clever filename,
//: and there is exactly one — adding a second should be uncomfortable.
const EXEMPT = new Set([
  // Proves this guard can fail, by writing a file that breaks the rule and
  // asserting it is caught. A guard nothing has ever seen fail is a promise.
  join("web", "lib", "__tests__", "session.test.ts"),
]);

const FORBIDDEN = [
  { pattern: /\blocalStorage\b/, why: "‏localStorage — رمزٌ هنا يقرؤه أي سكربت على الصفحة" },
  { pattern: /\bsessionStorage\b/, why: "‏sessionStorage — يقرؤه أي سكربت أيضاً" },
  { pattern: /\bdocument\.cookie\b/, why: "‏document.cookie لا يرى كوكيز HttpOnly أصلاً" },
  { pattern: /httpOnly\s*:\s*false/, why: "كوكي جلسة بلا HttpOnly" },
];

async function* walk(directory) {
  for (const entry of await readdir(directory, { withFileTypes: true })) {
    if (SKIP.has(entry.name)) continue;
    const path = join(directory, entry.name);
    if (entry.isDirectory()) yield* walk(path);
    else if (EXTENSIONS.some((extension) => entry.name.endsWith(extension))) yield path;
  }
}

/**
 * Blank out comments, keeping every line where it was.
 *
 * A comment cannot store a token, and the file most likely to *discuss*
 * `localStorage` is `lib/session.ts` — the module whose entire purpose is to
 * keep tokens out of it. A check that cannot tell an explanation from a use
 * forces that explanation to be deleted, and the rule then survives only in
 * whatever this file's error message manages to say.
 *
 * Lines are preserved rather than removed so a reported line number still
 * points at the offending line in an editor.
 */
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

    // Whole-line block comments are the common case and are handled first, so
    // the scan below never sees the text inside them.
    let cleaned = line.replace(/\/\*[\s\S]*?\*\//g, " ");

    const open = cleaned.indexOf("/*");
    if (open !== -1) {
      cleaned = cleaned.slice(0, open);
      inBlock = true;
    }

    // `[^:]` guards the `//` in a url. A `https://` in a string is not a
    // comment, and truncating there would hide whatever followed it.
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
        if (pattern.test(line)) found.push(`${relativePath}:${index + 1}: ${why}`);
      }
    });
  }
  return found;
}

// `pathToFileURL` rather than an interpolated string: on Windows the
// template form produces `file://C:\...`, which never equals
// `import.meta.url`, so the guard silently does nothing — and a check that
// exits 0 without opening a file is worse than no check, because CI reports
// it green.
if (import.meta.url === pathToFileURL(process.argv[1]).href) {
  const found = await violations();
  if (found.length) {
    console.error("رموز الجلسة تعيش في كوكيز HttpOnly وحدها:\n");
    for (const item of found) console.error(`  ${item}`);
    console.error(
      `\n${found.length} مخالفة. موقعٌ فيه محفظة: ثغرة XSS واحدة مع رمز يقرؤه` +
        " جافاسكربت تعني حساباً مسروقاً ورصيداً مسحوباً.",
    );
    process.exit(1);
  }
  console.log("لا رمز جلسة خارج كوكيز HttpOnly.");
}
