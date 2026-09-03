/**
 * كرت المركبة يُرسَم في مكوَّن واحد — T1010، ونظير `one_vehicle_card.py`.
 *
 * The v1 failure this exists for, in the task's own words: the home page alone
 * had four ways of drawing a vehicle card and three different field lists, so a
 * field added to the product appeared in some places and vanished from the
 * others. Nobody noticed until a customer asked why the mileage showed on the
 * auction page and not in search results — and by then all four had drifted in
 * different directions and there was no version to make the others match.
 *
 * The backend has the same guard for the same reason (phase 005, T413). This is
 * its counterpart in the web.
 *
 * What counts as drawing a card
 * -----------------------------
 * Reading two or more of the fields that *are* the card — the ones a card shows
 * and nothing else needs together — inside a `.tsx` file that is not the card
 * component. One field is a page legitimately mentioning a car's title; three
 * is a second card being born.
 *
 * The threshold is deliberately low and the exemption list is deliberately
 * short. A page that genuinely needs to show a car in a shape the card does not
 * cover should change the card, which is the whole point: then every list gets
 * the change.
 *
 * Run:  node ops/checks/web_one_vehicle_card.mjs
 */

import { readdir, readFile } from "node:fs/promises";
import { join, relative, sep } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const ROOT = join(fileURLToPath(import.meta.url), "..", "..", "..");
const WEB = join(ROOT, "web");

const SKIP = new Set(["node_modules", ".next", "dist", "coverage"]);

//: The one place a vehicle card is drawn.
const CARD = join("web", "features", "catalog", "VehicleCard.tsx");

//: Files allowed to read the card's fields without being the card. Each is a
//: decision recorded here, not a filename that happens to slip past a pattern.
const EXEMPT = new Set([
  CARD,
  // The vehicle's own page. It shows one car in full — a specification table,
  // structured data, an image — which is a different rendering from a card in a
  // grid, not a copy of one. Folding it into the card component would give the
  // card a "detailed" mode, and a component with a mode is two components
  // sharing a file (T1009).
  join("web", "app", "vehicles", "[id]", "page.tsx"),
  // The guard's own test, which builds a violating file on purpose.
  join("web", "features", "catalog", "__tests__", "one-card.test.ts"),
]);

//: Fields that together mean "this is a vehicle card". Chosen because a card
//: shows them and nothing else in the web has a reason to read them as a set.
const CARD_FIELDS = [
  "thumbnail_url",
  "reserve_price",
  "lot_number",
  "state_label",
  "transmission_label",
  "fuel_type_label",
  "condition_label",
  "odometer_km",
  "auction_number",
];

//: Two is a coincidence; three is a card. Set here so raising it is a visible
//: decision rather than a quiet edit to a regular expression.
const THRESHOLD = 3;

async function* walk(directory) {
  for (const entry of await readdir(directory, { withFileTypes: true })) {
    if (SKIP.has(entry.name)) continue;
    const path = join(directory, entry.name);
    if (entry.isDirectory()) yield* walk(path);
    else if (entry.name.endsWith(".tsx")) yield path;
  }
}

export async function violations(root = WEB) {
  const found = [];

  for await (const path of walk(root)) {
    const relativePath = relative(ROOT, path);
    if (EXEMPT.has(relativePath.split("/").join(sep))) continue;

    const source = await readFile(path, "utf8");
    const used = CARD_FIELDS.filter((field) =>
      new RegExp(`\\b${field}\\b`).test(source),
    );

    if (used.length >= THRESHOLD) {
      found.push(
        `${relativePath}: يرسم كرت مركبة بنفسه (${used.join("، ")}) — ` +
          "استعمل features/catalog/VehicleCard.tsx",
      );
    }
  }
  return found;
}

if (import.meta.url === pathToFileURL(process.argv[1]).href) {
  const found = await violations();
  if (found.length) {
    console.error("كرت المركبة يُرسَم في مكوَّن واحد:\n");
    for (const item of found) console.error(`  ${item}`);
    console.error(
      `\n${found.length} مخالفة. في v1 كانت الصفحة الرئيسية وحدها فيها أربعة` +
        " مسارات لرسم الكرت وثلاث قوائم حقول، فأي حقل جديد يظهر في بعضها" +
        " ويختفي في الباقي بصمت.",
    );
    process.exit(1);
  }
  console.log("لا رسم لكرت مركبة خارج المكوَّن.");
}
