/**
 * لا نقطة API خاصة بالويب — T1026 / J1.
 *
 * Rule 1 of spec 011, and the rule the whole phase is arranged around:
 * **«أي شيء يحتاجه الويب ولا يوفّره العقد يُضاف إلى العقد ويستفيد منه التطبيق،
 * أو لا يُضاف.»** The value of two channels over one is that a rule written
 * once serves both; a path only the web calls is a rule only the web has, and
 * the customer who switches devices finds a different product.
 *
 * The compiler already enforces most of this. `openapi-fetch` is typed by
 * `lib/api/schema.ts`, so `api.GET("/api/v1/whatever/")` does not compile unless
 * the schema declares that path with that method. What the compiler cannot see —
 * and what this file exists for — is the two ways round it:
 *
 * 1. **a bare `fetch` to a backend path**, written by hand, typed by nobody;
 * 2. **a route handler in `app/api/` that is not the transparent proxy** — a
 *    web-only endpoint that happens to live in this repository rather than in
 *    the backend, which is the same thing wearing a different hat.
 *
 * It also checks the paths the typed client uses against the committed schema
 * directly. That is deliberately redundant with the type checker: the redundancy
 * costs nothing and it is what keeps the criterion true if somebody ever loosens
 * the client's typing — J1 asks that *every path the web calls is in the 007
 * schema*, and a check that only asserts "the build passed" is asserting
 * something else.
 *
 * Run:  node ops/checks/web_uses_the_contract_only.mjs
 */

import { readdir, readFile } from "node:fs/promises";
import { join, relative, sep } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const ROOT = join(fileURLToPath(import.meta.url), "..", "..", "..");
const WEB = join(ROOT, "web");
const SCHEMA = join(ROOT, "backend", "openapi", "schema.yaml");

const SKIP = new Set(["node_modules", ".next", "dist", "coverage"]);
const EXTENSIONS = [".ts", ".tsx"];

//: The one route handler allowed under `app/api/`, and the reason it is allowed:
//: it forwards the path unchanged, so it cannot *be* an endpoint — whatever the
//: browser asks for becomes the same path at the backend, and a path the backend
//: does not have comes back as the backend's own 404.
const PROXY = join("web", "app", "api", "backend", "[...path]", "route.ts");

const EXEMPT = new Set([
  join("web", "lib", "api", "schema.ts"),
  join("web", "lib", "api", "client.ts"),
  // Writes offending files on purpose, to prove this guard can fail.
  join("web", "lib", "__tests__", "contract.test.ts"),
]);

//: `api.GET("/path/")` and friends — every call through the generated client.
const CLIENT_CALL = /\bapi\.(GET|POST|PUT|PATCH|DELETE)\(\s*"([^"]+)"/g;

//: A hand-written fetch at a backend path. `/api/backend/` is this app's own
//: proxy prefix and is how the browser is *supposed* to reach the backend.
const RAW_FETCH = /\bfetch\(\s*[`"'](?![^`"']*\/api\/backend\/)[^`"']*\/api\/v\d/;

async function* walk(directory) {
  for (const entry of await readdir(directory, { withFileTypes: true })) {
    if (SKIP.has(entry.name)) continue;
    const path = join(directory, entry.name);
    if (entry.isDirectory()) yield* walk(path);
    else if (EXTENSIONS.some((extension) => entry.name.endsWith(extension))) yield path;
  }
}

/**
 * The paths and methods the committed schema declares.
 *
 * Read with a small line parser rather than a YAML library: this guard runs in
 * CI before anything is installed, and a check that needs a dependency is a
 * check that gets skipped on the day the install is what broke.
 */
async function contract() {
  const declared = new Map();
  let path = null;

  for (const raw of (await readFile(SCHEMA, "utf8")).split(/\r?\n/)) {
    const pathMatch = /^ {2}(\/\S+):\s*$/.exec(raw);
    if (pathMatch) {
      path = pathMatch[1];
      declared.set(path, new Set());
      continue;
    }
    const methodMatch = /^ {4}(get|post|put|patch|delete):\s*$/.exec(raw);
    if (methodMatch && path) declared.get(path).add(methodMatch[1].toUpperCase());
  }
  return declared;
}

export async function violations(root = WEB) {
  const found = [];
  const declared = await contract();

  for await (const file of walk(root)) {
    const relativePath = relative(ROOT, file);
    const key = relativePath.split("/").join(sep);
    if (EXEMPT.has(key)) continue;

    const source = await readFile(file, "utf8");
    const lines = source.split(/\r?\n/);

    // 2. a route handler that is not the proxy
    if (key.includes(join("app", "api")) && key !== PROXY) {
      found.push(
        `${relativePath}: نقطة تعيش في الويب — ما يحتاجه الويب يُضاف إلى العقد` +
          " فيرثه التطبيق، أو لا يُضاف",
      );
    }

    lines.forEach((line, index) => {
      // 1. a hand-written fetch at a backend path
      if (RAW_FETCH.test(line)) {
        found.push(
          `${relativePath}:${index + 1}: نداءٌ مكتوب بيده إلى الخلفية — استعمل` +
            " العميل المولَّد من المخطط",
        );
      }
    });

    // 3. every typed call is a path and method the contract declares
    for (const [, method, called] of source.matchAll(CLIENT_CALL)) {
      const methods = declared.get(called);
      if (!methods) {
        found.push(`${relativePath}: ${called} ليس في مخطط الفيز 007`);
      } else if (!methods.has(method)) {
        found.push(`${relativePath}: ${method} ${called} ليست في المخطط`);
      }
    }
  }
  return found;
}

if (import.meta.url === pathToFileURL(process.argv[1]).href) {
  const found = await violations();
  if (found.length) {
    console.error("الويب يستهلك العقد ولا يملك نقاطاً خاصة به:\n");
    for (const item of found) console.error(`  ${item}`);
    console.error(
      `\n${found.length} مخالفة. قيمة قناتين على واحدة أن قاعدةً تُكتب مرة` +
        " وتخدمهما؛ ونقطةٌ يستدعيها الويب وحده قاعدةٌ يملكها الويب وحده.",
    );
    process.exit(1);
  }
  console.log("كل نقطة يستدعيها الويب موجودة في مخطط الفيز 007.");
}
