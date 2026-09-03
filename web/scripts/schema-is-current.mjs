/**
 * المخطط المرفوع = ما يولّده المخطط الآن — T1002 / J2.
 *
 * `lib/api/schema.ts` is committed, and everything the web sends or reads is
 * typed by it. That makes a stale copy the worst possible failure: the build is
 * green, `tsc` is happy, and the mismatch is discovered by a customer whose
 * request the backend rejects for a field the web still thinks exists.
 *
 * So the file is regenerated here and compared, byte for byte, with the one in
 * the repository. A backend field renamed without `npm run schema` fails CI —
 * which is the acceptance criterion word for word: *تغيير حقل في الخلفية بلا
 * إعادة توليد يُفشل بناء الويب، لا يمرّ ليُكتشف في المتصفح.*
 *
 * The comparison is against the generator's output rather than against the YAML
 * directly, because the YAML is itself pinned on the backend side
 * (`backend/tests/test_schema_is_pinned.py`) and checking the same thing twice
 * in two ways proves less than checking each link of the chain once.
 */

import { mkdtemp, readFile, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { execFile } from "node:child_process";
import { promisify } from "node:util";

const run = promisify(execFile);

const SCHEMA = "../backend/openapi/schema.yaml";
const GENERATOR = "node_modules/openapi-typescript/bin/cli.js";
const COMMITTED = "lib/api/schema.ts";

const scratch = await mkdtemp(join(tmpdir(), "haraj-schema-"));
const regenerated = join(scratch, "schema.ts");

try {
  // The generator's own entry point, run by this same node — not through
  // `npx` with a shell. A shell here would be a string this script concatenates
  // paths into, and the path comes from `tmpdir()`, which on a developer's
  // machine can contain a space or worse.
  await run(process.execPath, [GENERATOR, SCHEMA, "-o", regenerated]);

  const [fresh, committed] = await Promise.all([
    readFile(regenerated, "utf8"),
    readFile(COMMITTED, "utf8"),
  ]);

  if (fresh !== committed) {
    console.error(
      `\n${COMMITTED} لا يطابق ما يولّده ${SCHEMA}.\n\n` +
        "شغّل:  npm run schema  ثم ارفع الملف الناتج.\n\n" +
        "المخطط عقد، والعقد الذي لا يُجبِر ليس عقداً: نسخة قديمة هنا تعني بناءً\n" +
        "أخضر وخطأً يكتشفه عميل في متصفحه.\n",
    );
    process.exit(1);
  }

  console.log("lib/api/schema.ts مطابق للمخطط.");
} finally {
  await rm(scratch, { recursive: true, force: true });
}
