/**
 * T1030 — شاشة التصفّح: التبويبات والعدّادات والعدّاد التنازلي.
 *
 * كل تأكيد هنا عن **النصّ الذي يغادر الخادم**. `renderToStaticMarkup` تنتج
 * المُخرَج بلا أي بيانات ترطيب، وهو أقرب ما يمكن في اختبار وحدة إلى `curl` على
 * المسار — فما لم يظهر في هذه السلسلة لا يراه زائرٌ بلا جافاسكربت، ولا عنكبوت
 * فهرسة، ولا قارئٌ على شبكة بطيئة قبل أن يصل السكربت. ذلك معيار J5 حرفياً.
 *
 * والـ`fetch` هو المزيَّف، لا عميلنا: نصف ما يُختبَر هنا هو **أيّ طلب تُصدره
 * الصفحة** — طلبٌ واحد، وفيه التبويب — وتزييف عميلنا كان سيخفي ذلك تماماً.
 */

import { renderToStaticMarkup } from "react-dom/server";
import { readdir } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("next/headers", () => ({
  cookies: async () => ({ get: () => undefined, set: () => {}, delete: () => {} }),
}));

vi.mock("next/navigation", () => ({
  notFound: () => {
    throw new Error("NEXT_NOT_FOUND");
  },
  redirect: (to: string) => {
    throw new Error(`NEXT_REDIRECT:${to}`);
  },
}));

import Home from "@/app/page";
import { readPhase, DEFAULT_PHASE } from "@/features/browse/phase";
import { remaining } from "@/lib/format";

//: لحظةٌ ثابتة في المستقبل، فلا يتغيّر ما يُتوقَّع بتغيّر يوم التشغيل.
const ENDS_AT = "2099-12-31T20:00:00Z";

const VEHICLE = {
  id: 91,
  auction_id: 7,
  auction_ends_at: ENDS_AT,
  auction_number: 811,
  auction_state: "live",
  lot_number: 14,
  title: "تويوتا كامري 2022",
  make: "تويوتا",
  model: "كامري",
  year: 2022,
  odometer_km: 84000,
  transmission: "automatic",
  transmission_label: "أوتوماتيك",
  fuel_type: "petrol",
  fuel_type_label: "بنزين",
  condition: "good",
  condition_label: "جيدة",
  plate_type: "private",
  plate_type_label: "خصوصي",
  reserve_price: "48500.75",
  state: "listed",
  state_label: "معروضة",
  listing_state: "open",
  owner_company_name: "شركة المعارض",
  thumbnail_url: null,
};

const OTHER_VEHICLE = { ...VEHICLE, id: 92, lot_number: 15, title: "نيسان التيما 2021" };

/*
 * العدّادات **لا تساوي** طول القائمة، عمداً.
 *
 * لو كانت `active: 2` لَمَرَّ اختبارُ صفحةٍ تعدّ نتائجها بنفسها، وهي بالضبط
 * القاعدة التي يمنعها هذا الملف. الفارق هنا هو ما يجعل «من الخادم» قابلاً
 * للإثبات: لا شيء في الصفحة يستطيع اشتقاق ٤١ من مركبتين.
 */
const COUNTS = { soon: 3, active: 41, ended: 128 };

let asked: string[] = [];
let results: unknown[] = [VEHICLE, OTHER_VEHICLE];
let counts: unknown = COUNTS;
let refuse: { status: number; body: unknown } | null = null;

function answer(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

beforeEach(() => {
  asked = [];
  results = [VEHICLE, OTHER_VEHICLE];
  counts = COUNTS;
  refuse = null;

  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL) => {
      const url =
        typeof input === "string" ? input : input instanceof URL ? input.href : input.url;
      asked.push(url);

      if (refuse) return answer(refuse.body, refuse.status);

      const page: Record<string, unknown> = { total: results.length, results };
      if (counts !== null) page.counts = counts;
      return answer(page);
    }),
  );
});

afterEach(() => {
  vi.unstubAllGlobals();
});

function render(search: Record<string, string | string[] | undefined> = {}) {
  return Home({ searchParams: Promise.resolve(search) }).then(renderToStaticMarkup);
}

// ---------------------------------------------------------------------------

describe("J5 — الشاشة مرندَرة في الخادم", () => {
  it("طلبٌ بلا جافاسكربت يُرجع أسماء المركبات في الـHTML", async () => {
    const markup = await render();

    expect(markup).toContain("تويوتا كامري 2022");
    expect(markup).toContain("نيسان التيما 2021");
    //: والسعر كما وصل حرفاً بحرف — لا فاصلة آلاف ولا تقريب (المادة ٣-٢).
    expect(markup).toContain("48500.75");
  });

  it("أسماء التبويبات الثلاثة في الـHTML، لا في سكربت يبنيها", async () => {
    const markup = await render();

    for (const label of ["قريباً", "نشط", "منتهي"]) expect(markup).toContain(label);
  });

  it("العدّاد التنازلي يبدأ من قيمة مرندَرة، فلا فراغ قبل أن يعمل", async () => {
    const markup = await render();

    //: نفس ما تحسبه `remaining` — أي أن النصّ في الـHTML مدّةٌ حقيقية، لا
    //: شرطةٌ ولا هيكلٌ رماديّ ينتظر السكربت.
    const expected = remaining(ENDS_AT, Date.now());
    expect(expected).not.toBeNull();
    expect(markup).toContain(expected as string);
    //: واللحظة نفسها في السمة، فما يقرؤه الإنسان وما تقرؤه الآلة شيء واحد.
    expect(markup.toLowerCase()).toContain(`datetime="${ENDS_AT.toLowerCase()}"`);
  });
});

describe("العدّادات من الخادم، وفي طلب واحد", () => {
  it("الصفحة والعدّادات الثلاثة في طلب واحد لا ستة", async () => {
    await render();

    expect(asked).toHaveLength(1);
    expect(asked[0]).toContain("/api/v1/vehicles/");
  });

  it("الأرقام هي أرقام الخادم، لا طول القائمة", async () => {
    const markup = await render();

    //: القائمة مركبتان والعدّاد ٤١ — لا شيء في الصفحة يستطيع اشتقاق ذلك.
    expect(markup).toContain("41");
    expect(markup).toContain("128");
    expect(markup).toContain("3");
  });

  it("خادمٌ لا يرسل العدّادات: تبويبات بلا أرقام، لا أصفار مخترعة", async () => {
    counts = null;
    const markup = await render();

    for (const label of ["قريباً", "نشط", "منتهي"]) expect(markup).toContain(label);
    //: «٠» جملةٌ تعني «لا مزاد قادم». الخادم لم يقل ذلك، فلا تُقَل نيابةً عنه.
    expect(markup).not.toContain(">0<");
  });
});

describe("التبويب في العنوان", () => {
  it("‏`?phase=soon` يصل إلى الخادم كما هو", async () => {
    await render({ phase: "soon" });

    expect(asked[0]).toContain("phase=soon");
  });

  it("بلا تبويب في العنوان يُسأل الافتراضي — ولا يُترك للخادم أن يخمّن", async () => {
    await render();

    expect(asked[0]).toContain(`phase=${DEFAULT_PHASE}`);
  });

  it("المختار يُعلَّم من العنوان، فيصمد عبر إعادة التحميل والمشاركة", async () => {
    const markup = await render({ phase: "ended" });

    //: `aria-current` مرة واحدة فقط — تبويبان «حاليّان» شاشةٌ لا تقول شيئاً.
    expect(markup.match(/aria-current="page"/g)).toHaveLength(1);
    const current = /<a[^>]*aria-current="page"[^>]*>([\s\S]*?)<\/a>/.exec(markup);
    expect(current?.[1]).toContain("منتهي");
  });

  it("روابط التبويبات تحفظ البحث وتصفّر الترقيم", async () => {
    const markup = await render({ phase: "active", search: "كامري", offset: "24" });

    //: روابط التبويبات وحدها — روابط الترقيم في نفس الصفحة تحمل `offset` بحقّ.
    const tabs = /<nav aria-label="حالة المزاد"[\s\S]*?<\/nav>/.exec(markup)?.[0] ?? "";
    const hrefs = [...tabs.matchAll(/href="([^"]+)"/g)].map(([, href]) => href);

    expect(hrefs).toHaveLength(3);
    for (const href of hrefs) {
      expect(href).toContain("search=%D9%83%D8%A7%D9%85%D8%B1%D9%8A");
      //: من كان في الصفحة الرابعة من «نشط» لا يريد الرابعة من «منتهي» —
      //: وغالباً لا توجد، فيرى فراغاً يظنّه التبويب كلَّه.
      expect(href).not.toContain("offset=");
    }
  });

  it("تبويبٌ لا نعرفه يعود إلى الافتراضي، لا إلى 404", () => {
    expect(readPhase(new URLSearchParams("phase=whatever"))).toBe(DEFAULT_PHASE);
    expect(readPhase(new URLSearchParams())).toBe(DEFAULT_PHASE);
    expect(readPhase(new URLSearchParams("phase=ended"))).toBe("ended");
  });
});

describe("الفراغ والفشل شاشتان، لا غياب", () => {
  it("التبويب الفارغ يقول لماذا هو فارغ", async () => {
    results = [];

    expect(await render({ phase: "soon" })).toContain("لا مزاد قادم الآن.");
    expect(await render({ phase: "active" })).toContain("لا مزاد جارٍ الآن");
    expect(await render({ phase: "ended" })).toContain("لا مزاد منتهٍ بعد.");
  });

  it("فراغٌ سببه البحث يُقال إنه سبب البحث", async () => {
    results = [];
    const markup = await render({ phase: "active", search: "لا شيء" });

    expect(markup).toContain("لا مركبات مطابقة لبحثك في هذا التبويب.");
    expect(markup).not.toContain("لا مزاد جارٍ الآن");
  });

  it("رفض الخادم يُعرض بجملته، والتبويبات تبقى", async () => {
    refuse = {
      status: 503,
      body: { error: { code: "service_unavailable", message: "الخدمة متوقفة مؤقتاً.", detail: {} } },
    };
    const markup = await render();

    expect(markup).toContain("الخدمة متوقفة مؤقتاً.");
    //: التبويبات تبقى، فيبقى للزائر شيء يفعله غير إعادة التحميل.
    expect(markup).toContain("قريباً");
    expect(markup).toContain("منتهي");
  });

  it("خادمٌ لا يُجيب: جملةٌ مفهومة لا صفحة بيضاء ولا «undefined»", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => {
        throw new Error("ECONNREFUSED");
      }),
    );
    const markup = await render();

    expect(markup).toContain("تعذّر الاتصال بالخادم");
    expect(markup).not.toContain("undefined");
  });
});

describe("حالة المزاد كما قالها الخادم", () => {
  it("مركبةٌ مضت لحظة انتهائها تبقى معروضة — الويب لا يرشّح بالوقت", async () => {
    //: الخادم أعادها في تبويب «نشط». ساعةُ الجهاز تقول إن الوقت مضى.
    //: في v1 كانت الواجهة تحذفها أو تكتب «انتهى» — فاختفى مزادٌ مفتوح عمّن
    //: ساعته متقدّمة. هنا: تُعرض كما جاءت، وبحالتها التي قالها الخادم.
    results = [{ ...VEHICLE, auction_ends_at: "2020-01-01T00:00:00Z" }];
    const markup = await render({ phase: "active" });

    expect(markup).toContain("تويوتا كامري 2022");
    expect(markup).toContain("معروضة");
    expect(markup).toContain("الوقت المعلَن");
    //: ولا حكمٌ على المزاد نفسه من ساعة المتصفح.
    expect(markup).not.toContain("انتهى المزاد");
  });

  it("مركبةٌ بلا لحظة انتهاء لا تُرسم لها ساعةٌ من لا شيء", async () => {
    results = [{ ...VEHICLE, auction_ends_at: null }];
    const markup = await render();

    expect(markup).toContain("تويوتا كامري 2022");
    expect(markup).not.toContain("يغلق بعد");
    expect(markup).not.toContain("الوقت المعلَن");
  });
});

describe("المدّة فرقٌ بين لحظتين UTC", () => {
  const at = (iso: string) => Date.parse(iso);

  it("تُقرأ بالأيام والساعات فوق اليوم، وبالساعة تحته", () => {
    expect(remaining("2026-09-06T12:00:00Z", at("2026-09-03T09:00:00Z"))).toBe(
      "3 أيام و3 ساعات",
    );
    expect(remaining("2026-09-04T09:00:00Z", at("2026-09-03T09:00:00Z"))).toBe("يوم واحد");
    expect(remaining("2026-09-05T09:00:00Z", at("2026-09-03T09:00:00Z"))).toBe("يومان");
    expect(remaining("2026-09-03T10:02:03Z", at("2026-09-03T09:00:00Z"))).toBe("01:02:03");
  });

  it("لا تُبنى تواريخ محلية: عبور منتصف الليل لا يغيّر الفرق", () => {
    //: نفس الفرق — ساعة — على جانبي منتصف الليل بتوقيت الرياض (٢١:٠٠ UTC).
    expect(remaining("2026-09-03T20:30:00Z", at("2026-09-03T19:30:00Z"))).toBe("01:00:00");
    expect(remaining("2026-09-03T21:30:00Z", at("2026-09-03T20:30:00Z"))).toBe("01:00:00");
  });

  it("‏`null` للحظة مضت أو غائبة أو غير مقروءة", () => {
    expect(remaining("2026-09-03T09:00:00Z", at("2026-09-03T09:00:00Z"))).toBeNull();
    expect(remaining("2026-09-03T08:59:59Z", at("2026-09-03T09:00:00Z"))).toBeNull();
    expect(remaining(null, Date.now())).toBeNull();
    expect(remaining("ليس تاريخاً", Date.now())).toBeNull();
  });
});

describe("لا نسخة ثانية من العقد", () => {
  const api = fileURLToPath(new URL("../api", import.meta.url));

  /**
   * الطبقة المؤقّتة حُذفت — وهذا الاختبار هو ما يمنع عودتها.
   *
   * كان هنا `lib/api/awaiting.ts`: أنواعٌ مكتوبة بيد تعلن `phase` و`counts` و
   * `auction_ends_at` لأن الويب سبق العقد. وحمل تاريخ انتهائه في اختبارٍ يفشل
   * يوم يعلن المخطط تلك الحقول — ففشل يوم أعلنها، وحُذف الملف، وصارت الأنواع
   * تأتي من المولَّد.
   *
   * والقاعدة التي كسرها ذلك الملف مؤقّتاً هي T1002: **العميل مولَّد لا مكتوب**.
   * نوعٌ مكتوب بيد بجوار نوعٍ مولَّد لا يخطئ يوم يُكتب، وإنما يوم يتغيّر
   * المخطط ولا يتغيّر هو — فيقول البناءُ إن الحقل موجود، ويقول الخادم لا.
   *
   * فالفحص على **الوجود** لا على المحتوى: أي ملفٍّ جديد في `lib/api/` خارج
   * القائمة المعروفة يُسقط الحزمة، ويُقرأ عمداً لا يُضاف سهواً.
   */
  it("لا ملفّ في lib/api خارج المعروف — الأنواع تُولَّد ولا تُكتب", async () => {
    const known = new Set([
      "client.ts", //: `fetch` المهيّأ بالكوكيز والعنوان
      "errors.ts", //: رفضُ الخادم كما كتبه، لا صياغةٌ من عندنا
      "index.ts", //: الواجهة الواحدة (T1026 يقرؤها)
      "phases.ts", //: قيمُ الأطوار مشتقّةً من مفاتيح المولَّد
      "schema.ts", //: المولَّد نفسه
    ]);

    const found = (await readdir(api)).filter((name) => name.endsWith(".ts"));
    const extra = found.filter((name) => !known.has(name));

    expect(
      extra,
      `ملفّات جديدة في lib/api. إن كانت أنواعاً فهي نسخةٌ ثانية من العقد (T1002): ${extra.join(", ")}`,
    ).toEqual([]);
  });
});
