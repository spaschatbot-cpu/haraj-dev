/**
 * T1025 و T1026 — الحارسان اللذان يحرسان المبدأ الحاكم للفيز.
 *
 * The phase's governing principle is one sentence: **قناتان، عقد واحد، منطق
 * واحد.** Two criteria hold it, and each is a guard rather than a habit:
 *
 * * **J1** — every path the web calls is in the 007 contract. A path only the
 *   web calls is a rule only the web has, and the customer who switches from the
 *   site to the app finds a different product;
 * * **J3** — no business rule in the web. Not a price worked out, not an
 *   eligibility condition evaluated.
 *
 * Every guard here is run *and* proven able to fail. That second half is not
 * ceremony: this file is where a regex that matched nothing was caught earlier
 * in the phase — a check that passes every file and reports green, which is the
 * worst state a guard can be in and one that no test of a clean tree can detect.
 */

import { afterEach, describe, expect, it } from "vitest";
import { mkdtemp, rm, writeFile, mkdir } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";

const scratches: string[] = [];

/** A throwaway tree with one flat file in it, cleaned up after each test. */
async function seed(name: string, source: string): Promise<string> {
  const root = await mkdtemp(join(tmpdir(), "haraj-seed-"));
  scratches.push(root);

  await writeFile(join(root, name), source, "utf8");
  return root;
}

afterEach(async () => {
  await Promise.all(scratches.splice(0).map((root) => rm(root, { recursive: true, force: true })));
});

// ---------------------------------------------------------------------------
// T1026 / J1 — the web calls the contract and nothing else
// ---------------------------------------------------------------------------

describe("لا نقطة خاصة بالويب", () => {
  it("كل نقطة يستدعيها الويب في مخطط الفيز 007", async () => {
    const { violations } = await import(
      "../../../ops/checks/web_uses_the_contract_only.mjs"
    );

    expect(await violations()).toEqual([]);
  });

  it("يمسك مساراً غير موجود في المخطط", async () => {
    // The type checker refuses this too. The guard is deliberately redundant
    // with it: J1 asks that every path is in the schema, and a check that only
    // asserts "the build passed" is asserting something else — it would stop
    // holding the moment somebody loosened the client's typing.
    const root = await seed("invented.ts", 'await api.GET("/api/v1/invented/");\n');

    const { violations } = await import(
      "../../../ops/checks/web_uses_the_contract_only.mjs"
    );
    const found = await violations(root);

    expect(found).toHaveLength(1);
    expect(found[0]).toContain("ليس في مخطط");
  });

  it("يمسك طريقة لا يعلنها المخطط لمسار يعلنه", async () => {
    // `/api/v1/auctions/` exists and is read-only. A POST to it is a path the
    // contract has and a capability it does not.
    const root = await seed("wrong-method.ts", 'await api.POST("/api/v1/auctions/", {});\n');

    const { violations } = await import(
      "../../../ops/checks/web_uses_the_contract_only.mjs"
    );

    expect(await violations(root)).toHaveLength(1);
  });

  it("يمسك نداءً مكتوباً بيده إلى الخلفية", async () => {
    const root = await seed(
      "raw.ts",
      'const r = await fetch("http://backend/api/v1/wallet/");\n',
    );

    const { violations } = await import(
      "../../../ops/checks/web_uses_the_contract_only.mjs"
    );
    const found = await violations(root);

    expect(found).toHaveLength(1);
    expect(found[0]).toContain("مكتوب بيده");
  });

  it("يمسك نقطةً تعيش في الويب", async () => {
    // A web-only endpoint that happens to live in this repository is the same
    // thing as one that lives in the backend, wearing a different hat.
    const root = await mkdtemp(join(tmpdir(), "haraj-seed-"));
    scratches.push(root);
    await mkdir(join(root, "app", "api", "favourites"), { recursive: true });
    await writeFile(
      join(root, "app", "api", "favourites", "route.ts"),
      'export const GET = async () => new Response("[]");\n',
      "utf8",
    );

    const { violations } = await import(
      "../../../ops/checks/web_uses_the_contract_only.mjs"
    );
    const found = await violations(root);

    expect(found).toHaveLength(1);
    expect(found[0]).toContain("نقطة تعيش في الويب");
  });
});

// ---------------------------------------------------------------------------
// T1025 / J3 — no rule in the web: not a price, not an eligibility condition
// ---------------------------------------------------------------------------

describe("لا قاعدة عمل في الويب", () => {
  it("الشجرة نظيفة من حساب سعر ومن شرط أهلية", async () => {
    const money = await import("../../../ops/checks/web_money_is_never_computed.mjs");
    const eligibility = await import(
      "../../../ops/checks/web_no_eligibility_logic.mjs"
    );

    expect(await money.violations()).toEqual([]);
    expect(await eligibility.violations()).toEqual([]);
  });

  it("يمسك موازنة مبلغ بحدٍّ — «هل يكفي؟» ليست سؤال الويب", async () => {
    // Arithmetic is not the only way to reach a money decision: this computes
    // nothing and decides everything.
    const root = await seed("floor.ts", "const enough = amount < minimum_bid;\n");

    const { violations } = await import(
      "../../../ops/checks/web_money_is_never_computed.mjs"
    );
    const found = await violations(root);

    expect(found).toHaveLength(1);
    expect(found[0]).toContain("موازنة مبلغ");
  });

  it("يمسك موازنة مبلغ برقم", async () => {
    const root = await seed("positive.ts", "const owed = outstanding > 0;\n");

    const { violations } = await import(
      "../../../ops/checks/web_money_is_never_computed.mjs"
    );

    expect(await violations(root)).toHaveLength(1);
  });

  it("لا يمسك مقارنةً بمتغيّر — الترشيح توجيه لا قاعدة", async () => {
    // `bucket.kind === filter` is routing. A guard that cannot tell routing from
    // a rule produces a wall of false positives, which is a guard people switch
    // off — and then it protects nothing at all.
    const root = await seed("routing.ts", "const active = bucket === filter;\n");

    const { violations } = await import(
      "../../../ops/checks/web_money_is_never_computed.mjs"
    );

    expect(await violations(root)).toEqual([]);
  });

  it("يمسك موازنة شرط أهلية بآخر", async () => {
    const root = await seed(
      "gate.ts",
      "export const may = (m) => m.insurance_free >= m.required_deposit;\n",
    );

    const { violations } = await import(
      "../../../ops/checks/web_no_eligibility_logic.mjs"
    );

    expect(await violations(root)).toHaveLength(1);
  });
});
