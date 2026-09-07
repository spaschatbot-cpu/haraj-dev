/**
 * الممرّ يمرّر المسار كما كُتب — ومنه الشرطة الأخيرة.
 *
 * عطلٌ وقع فعلاً (2026-09-07): كل نداءٍ **كاتب** من المتصفّح يسقط بـ500 بينما
 * النداء نفسه إلى الخلفية بـ`curl` يعود 200. والفرق حرفٌ واحد: `params.path`
 * مصفوفةُ مقاطع، والمقطع الفارغ في آخر `/bids/quote/` ليس مقطعاً، فيبني
 * `join("/")` مساراً بلا شرطة. وكل مسار في الخلفية ينتهي بشرطة — فجانغو
 * يحوّل `GET` الناقص بـ301 (`APPEND_SLASH`) وينجو صامتاً، **ولا يحوّل
 * `POST`** لأن التحويل يُفقد الجسم، بل يرمي `RuntimeError`.
 *
 * ولهذا يُقاس **العنوان المُرسَل** لا رمزُ الجواب: خادمٌ متسامح يجعل
 * الاختبارَ أخضرَ والعطلَ قائماً، وما يُحرَس هنا هو عقد الملفّ نفسه — أن ما
 * يُطلَب منه هو ما يصل الخلفية.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("next/headers", () => ({
  cookies: async () => ({
    get: () => undefined,
    set: () => {},
    delete: () => {},
  }),
}));

import { NextRequest } from "next/server";

import { GET, POST } from "@/app/api/backend/[...path]/route";

let sent: string[] = [];

beforeEach(() => {
  sent = [];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL) => {
      sent.push(typeof input === "string" ? input : (input as Request).url ?? String(input));
      return new Response("{}", {
        status: 200,
        headers: { "content-type": "application/json" },
      });
    }),
  );
});

afterEach(() => {
  vi.unstubAllGlobals();
});

//: يُنادى بالطلب وحده — والتوقيع نفسه هو نصف الإصلاح: الممرّ لم يعد يقرأ
//: `params.path` أصلاً، فلا سبيل إلى إعادة تركيب المسار من مقاطعه.

describe("الممرّ يمرّر المسار كما كُتب", () => {
  it("الشرطة الأخيرة تصل الخلفية في POST", async () => {
    await POST(
      new NextRequest("http://web.test/api/backend/api/v1/bids/quote/", {
        method: "POST",
        body: JSON.stringify({ amount: "100.00" }),
      }),
    );

    expect(sent).toHaveLength(1);
    expect(sent[0]).toMatch(/\/api\/v1\/bids\/quote\/$/);
  });

  it("ومسارٌ بلا شرطة يبقى بلا شرطة — لا يُضاف شيء أيضاً", async () => {
    //: النصف الآخر من «كما كُتب». ممرٌّ يُلحق شرطةً دائماً كان سيصلح هذا العطل
    //: ويصير هو نفسه طبقةَ تحويلٍ في الطريق — وهو ما يمنعه عقد هذا الملفّ.
    await GET(new NextRequest("http://web.test/api/backend/api/v1/healthz"));

    expect(sent[0]).toMatch(/\/api\/v1\/healthz$/);
  });

  it("ومعايير الاستعلام تمرّ كما هي", async () => {
    await GET(
      new NextRequest("http://web.test/api/backend/api/v1/vehicles/?limit=5&phase=active"),
    );

    expect(sent[0]).toContain("/api/v1/vehicles/?limit=5&phase=active");
  });
});
