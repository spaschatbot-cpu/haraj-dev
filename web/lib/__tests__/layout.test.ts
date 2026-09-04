/**
 * T1027 — كل شاشة رئيسية على ثلاثة مقاسات، وما يُثبَت منها بلا متصفح.
 *
 * المعيار J9: «كل شاشة تعمل بالعربية RTL على مقاس جوال».
 *
 * ما تفعله هذه الملفّة، وما لا تفعله — بالضبط
 * ==========================================
 * لا يوجد متصفح هنا. لذلك **لا تُلتقط صورة**، ولا يُقاس بكسل، ولا يُشغَّل محرّك
 * تخطيط. ورندرة الشيفرة نفسها ثلاث مرات وحفظ ثلاثة ملفات متطابقة اختبارٌ أخضر
 * لا يُثبت شيئاً — أسوأ من فجوة معلنة (المادة ٦-٤).
 *
 * فما الذي يختلف فعلاً بين المقاسات الثلاثة إذاً؟ **الأصناف التي يطبّقها
 * المتصفح.** صنف `sm:grid-cols-2` قاعدةٌ داخل `@media (min-width: 640px)`، وأيّ
 * صنف يسري عند عرضٍ ما هو دالّة صرفة في ذلك العرض — تُحسب هنا بلا تخمين:
 *
 *   ٣٧٥  → الأصناف بلا بادئة وحدها
 *   ٧٦٨  → مضافاً إليها `sm:` (٦٤٠) و`md:` (٧٦٨)
 *   ١٢٨٠ → مضافاً إليها `lg:` (١٠٢٤) و`xl:` (١٢٨٠)
 *
 * فاللقطة لكل شاشة ولكل مقاس هي **التخطيط الساري عند ذلك العرض**: كل عنصر
 * يحمل صنفاً يقرّر الشكل، ومساره في الوثيقة، والقيمة التي تفوز في كل عائلة
 * خصائص بعد فضّ البوادئ. وأي تغيير في التخطيط — عمود يُضاف، نقطة انكسار تُزاح،
 * شبكة تُستبدل بـflex — يكسر لقطة بعينها في المقاس الذي يخصّه.
 *
 * **والسجلّ حالاتٌ لا مساراتٍ.** تسعة مسارات، وإحدى عشرة شاشة: صفحة المركبة
 * مرّتين — لأن الزائر يرى رابطاً حيث يرى الداخلُ صندوقَ مزايدة ولوحةً حيّة
 * ورفضاً فوقهما، فالثلثان اللذان يهمّان لا يُرندَران بلا جلسة — والمفضّلة
 * مرّتين، عامرةً وفارغةً، لأن الفارغة ليست الأقصر بل الأخرى: شبكتها الاستجابية
 * غير موجودة أصلاً.
 *
 * **وأربع شاشات لقطاتها الثلاث متطابقة**، لأنها لا تعلن نقطة انكسار أصلاً.
 * التطابق هنا خبر لا حشو، ولذلك هو **مُعلَن بالاسم** في اختبار مستقلّ
 * (`SIZE_INVARIANT`): شاشة تخرج من القائمة أو تدخلها تُفشل ذلك الاختبار، فيصير
 * «هذه الشاشة واحدة على المقاسات الثلاثة» قراراً يُراجَع لا صدفةً تمرّ. وما
 * يجعلها صالحة على الجوال حينها ليس صنفاً بل `flex-wrap` — ومن يقرّر أين يلتفّ
 * السطر هو محرّك التخطيط، أي أن صلاحها بالذات هي ما لا تراه هذه الملفّة.
 *
 * **وما لا تُثبته:** أن النتيجة *تبدو* صحيحة. أن النصّ لا يفيض، وأن الصورة لا
 * تُقصّ، وأن زرّاً لا يختفي خلف آخر، وأن المسافات مريحة لعينٍ عربية — كل ذلك
 * يحتاج محرّك تخطيط وعيناً بشرية. ‏Playwright وخادمٌ يعمل هما بقيّة T1027،
 * وهذه الملفّة لا تدّعي أنها هما.
 *
 * وRTL يُفحَص ولا يُفترض
 * ====================
 * التقاط HTML لا يثبت أن التخطيط منعكس — الانعكاس يحدث في المتصفح. الذي يمكن
 * فحصه فعلاً، وهو المفحوص هنا:
 *
 * ١. الاتجاه معلَن مرة واحدة على `<html>`، ولا صفحة تعلن اتجاهها بنفسها؛
 * ٢. **لا صنف اتجاه فيزيائي في المستودع** — `ml-*`، `pr-*`، `border-l`،
 *    `text-left`، `flex-row-reverse`… هذه هي الطريقة التي ينكسر بها RTL عملياً:
 *    الصنف الفيزيائي لا ينعكس مع الوثيقة، فيبقى الهامش على اليسار في صفحة
 *    تُقرأ من اليمين. الخصائص المنطقية (`ms-*`، `pe-*`، `text-start`) هي البديل
 *    وهي ما يستعمله الكود. يُفحص في المصدر **وفي HTML المرندَر** معاً، لأن
 *    الصنف المركَّب في زمن التشغيل لا يراه فحص المصدر؛
 * ٣. لا خاصية CSS فيزيائية في `globals.css`، وجزيرة الـLTR الوحيدة (`.money`)
 *    معلنة ومقصودة ومحصورة في رقم.
 *
 * وما يبقى للعين البشرية: أن الترتيب المنعكس *مفهوم* — أن السهم يشير للجهة
 * الصحيحة، وأن الرقم بجوار كلمته لا بعيداً عنها. لا شيء هنا يقول ذلك.
 *
 * والمبالغ
 * ========
 * المبلغ نصّ عشري يصل من الخادم ويُعرض كما وصل (المادة ٣-٢). فيُتحقَّق أن كل
 * مبلغ في التجهيزة يظهر **حرفاً بحرف** في كل شاشة تعرضه، وأن لا نسخة مفصولة
 * بفواصل الآلاف ولا رقماً هندياً يظهر في أي شاشة — وهما بالضبط ما يُدخله
 * تنسيقٌ يجري في المتصفح. ومجموع المحفظة في التجهيزة **لا يساوي جمع دلائها
 * عمداً**: صفحةٌ تجمع الدلاء بنفسها كانت ستعرض رقماً آخر، واللقطة تكسر.
 */

import { renderToStaticMarkup } from "react-dom/server";
import { JSDOM } from "jsdom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { readdir, readFile } from "node:fs/promises";
import { join } from "node:path";

/**
 * كوكيز قابلة للضبط — الشاشات المحميّة تحتاج جلسة، والعامة تُرندَر بلا واحدة.
 *
 * A store rather than a stub returning `undefined`: half the screens in this
 * registry redirect to `/sign-in` without a session, and a snapshot of a
 * redirect is a snapshot of nothing.
 */
const cookieJar = new Map<string, string>();

vi.mock("next/headers", () => ({
  cookies: async () => ({
    get: (name: string) => {
      const value = cookieJar.get(name);
      return value === undefined ? undefined : { name, value };
    },
    set: (name: string, value: string) => {
      cookieJar.set(name, value);
    },
    delete: (name: string) => {
      cookieJar.delete(name);
    },
  }),
}));

vi.mock("next/navigation", () => ({
  notFound: () => {
    throw new Error("NEXT_NOT_FOUND");
  },
  redirect: (to: string) => {
    throw new Error(`NEXT_REDIRECT:${to}`);
  },
}));

import type { Flash } from "@/lib/flash";

import Home from "@/app/page";
import SignInPage from "@/app/sign-in/page";
import AuctionPage from "@/app/auctions/[id]/page";
import VehiclePage from "@/app/vehicles/[id]/page";
import BidsPage from "@/app/bids/page";
import FavouritesPage from "@/app/favourites/page";
import AccountPage from "@/app/account/page";
import WalletPage from "@/app/wallet/page";

// ---------------------------------------------------------------------------
// التجهيزة — بيانات الخادم كما تصل
// ---------------------------------------------------------------------------

const AUCTION = {
  id: 7,
  number: 811,
  title: "مزاد الرياض الأسبوعي",
  state: "live",
  state_label: "جارٍ",
  starts_at: "2026-09-03T08:00:00Z",
  ends_at: "2026-09-03T16:00:00Z",
  vehicle_count: 40,
  open_vehicle_count: 12,
};

const VEHICLE = {
  id: 91,
  auction_id: 7,
  /*
   * لحظة انتهاء المزاد على الكرت — عليها يقوم العدّاد التنازلي (T1030).
   *
   * بعيدةٌ في المستقبل عمداً: العدّاد يقرأ ساعة الجهاز، ولحظةٌ قريبة كانت
   * ستجعل الشيفرة تسلك مسلكين مختلفين قبل تاريخٍ ما وبعده — أي لقطةً تنكسر
   * يوماً بلا أن يغيّر أحد سطراً، وهو أسوأ اختبار: أخضر اليوم، أحمر بلا سبب.
   */
  auction_ends_at: "2099-12-31T20:00:00Z",
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

const OTHER_VEHICLE = {
  ...VEHICLE,
  id: 92,
  lot_number: 15,
  title: "نيسان التيما 2021",
  model: "التيما",
  year: 2021,
  odometer_km: 61000,
  reserve_price: "31200.00",
};

const LIVE_BID = {
  id: 5,
  vehicle_id: 91,
  auction_id: 7,
  lot_number: 14,
  vehicle_title: VEHICLE.title,
  amount: "50000.25",
  placed_at: "2026-09-03T10:10:00Z",
  is_withdrawn: false,
  is_superseded: false,
};

//: مسحوبة، فالصفّ يفقد زرّه — وهو صفّ بتخطيط مختلف عن جاره، لا نسخة منه.
const WITHDRAWN_BID = {
  ...LIVE_BID,
  id: 6,
  vehicle_id: 92,
  lot_number: 15,
  vehicle_title: OTHER_VEHICLE.title,
  amount: "47250.10",
  placed_at: "2026-09-03T09:40:00Z",
  is_withdrawn: true,
};

const BIDS = [LIVE_BID, WITHDRAWN_BID];

const PROFILE = {
  id: 3,
  phone: "966500000001",
  display_name: "أحمد",
  full_name: "أحمد بن سالم",
  email: "ahmad@example.com",
  account_type: "company",
  national_id: "",
  national_id_verified: false,
  phone_verified_at: "2026-09-01T07:00:00Z",
  has_company_profile: true,
  company_profile_complete: false,
};

const COMPANY = {
  name: "معارض الرياض",
  representative_name: "أحمد بن سالم",
  commercial_register: "1010101010",
  vat_number: "300000000000003",
  building_number: "1234",
  street: "طريق الملك عبدالعزيز",
  district: "العليا",
  city: "الرياض",
  postal_code: "12211",
  is_complete: false,
};

/**
 * المحفظة — والمجموع **ليس** جمع الدلاء عمداً.
 *
 * `total` is a field the ledger answers with. Making the fixture's total differ
 * from `available + held + locked` is the only way a snapshot can tell the two
 * apart: a page that added the three up would print a different number here and
 * the snapshot would break, which is exactly what G5 asks for.
 */
const WALLET = {
  currency: "SAR",
  total: "19000.00",
  available: "9250.40",
  held_for_auctions: "8000.00",
  locked_for_dues: "1500.75",
  buckets: [
    {
      kind: "insurance_free",
      label: "تأمين متاح",
      amount: "9250.40",
      entry_count: 4,
      statement: "x",
    },
    {
      kind: "insurance_held",
      label: "تأمين محجوز لمزاد",
      amount: "8000.00",
      entry_count: 1,
      statement: "x",
    },
  ],
  holds: [
    {
      id: 3,
      amount: "8000.00",
      reason: "bidding",
      reason_label: "ضمان المزايدة",
      auction: { id: 7, number: 811 },
      invoice: null,
      created_at: "2026-09-03T10:10:00Z",
    },
  ],
  as_of: "2026-09-03T10:11:00Z",
};

/**
 * الرفض كما يكتبه الخادم — جملته ورقمه، في كوكي لمرة واحدة.
 *
 * `lower_needs_confirm` is the one refusal that renders a different *form*
 * rather than a sentence above the same one, and its `detail` carries the
 * standing bid the customer is being asked to confirm going below. Both halves
 * are layout no other fixture reaches: the confirmation block, and a decimal
 * string that has to survive from the refusal to the screen unchanged.
 */
const REFUSAL: Flash = {
  code: "lower_needs_confirm",
  message: "مزايدتك القائمة أعلى من هذا المبلغ. أكِّد الخفض إن كنت تقصده.",
  detail: { requested: "45000.00", standing: LIVE_BID.amount },
};

//: قوائم العميل فارغة — يُضبط لكل شاشة تطلب ذلك، ويُصفَّر قبل كل اختبار.
let listsAreEmpty = false;

function answer(body: unknown) {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { "content-type": "application/json" },
  });
}

beforeEach(() => {
  cookieJar.clear();
  listsAreEmpty = false;
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL) => {
      const url = typeof input === "string" ? input : (input as Request).url;

      // A new customer's lists, for the screens that ask for that state.
      if (listsAreEmpty && /\/(?:bids\/mine|favourites)\//.test(url)) {
        return answer({ total: 0, results: [] });
      }

      if (url.includes("/bids/mine/")) return answer({ total: BIDS.length, results: BIDS });
      if (url.includes("/favourites/")) {
        return answer({ total: 2, results: [VEHICLE, OTHER_VEHICLE] });
      }
      if (url.includes("/profile/company/")) return answer(COMPANY);
      if (url.includes("/profile/")) return answer(PROFILE);
      if (url.includes("/wallet/")) return answer(WALLET);

      if (url.includes("/vehicles/") && url.includes("/auctions/")) {
        return answer({ total: 1, results: [VEHICLE] });
      }
      //: شبكة الجذر: `/api/v1/vehicles/?…` — صفحةٌ ومعها العدّادات الثلاثة في
      //: الرد نفسه، وهي الطريقة الوحيدة التي تصل بها إلى الشاشة.
      if (/\/vehicles\/(\?|$)/.test(url)) {
        return answer({
          total: 1,
          results: [VEHICLE],
          counts: { upcoming: 3, active: 41, ended: 128 },
        });
      }
      if (/\/auctions\/\d+\//.test(url)) return answer(AUCTION);
      if (url.includes("/auctions/")) return answer({ total: 1, results: [AUCTION] });
      return answer(VEHICLE);
    }),
  );
});

afterEach(() => {
  vi.unstubAllGlobals();
});

async function render(element: Promise<React.ReactElement> | React.ReactElement) {
  return renderToStaticMarkup(await element);
}

// ---------------------------------------------------------------------------
// سجلّ الشاشات — كل شاشة رئيسية في `app/`، مرّة واحدة
// ---------------------------------------------------------------------------

interface Screen {
  /** الاسم في اللقطة. يُغيَّر فيُنشئ لقطة جديدة، فلا يُغيَّر بلا سبب. */
  name: string;
  /** الشاشات خلف الدخول تُحوِّل بلا جلسة، فلا تُرندَر بلا واحدة. */
  signedIn?: boolean;
  /** رفضٌ من الخادم ينتظر العرض — الشاشة حينها تخطيط آخر لا نصّ زائد. */
  flash?: Flash;
  /** قوائم العميل فارغة — أول ما يراه عميل جديد. */
  emptyLists?: boolean;
  /** المبالغ التي يجب أن تظهر حرفاً بحرف على هذه الشاشة. */
  amounts?: string[];
  render: () => Promise<string>;
}

const SCREENS: Screen[] = [
  {
    /*
     * المزادات هي الرئيسية: شبكة تصفّح (T1030) — تبويبات وشبكة استجابية —
     * وقائمة المزادات المنفصلة أُحيلت إلى هنا، فلا شاشة لها في هذه القائمة.
     *
     * It used to be a paragraph, and it used to be size-invariant. Now it is
     * the screen most visitors open first, it carries the same responsive grid
     * the auction page does, and it renders a price — so it belongs in the
     * amount scan too, and it has left `SIZE_INVARIANT` deliberately.
     */
    name: "المزادات (الرئيسية)",
    amounts: [VEHICLE.reserve_price],
    render: () => render(Home({ searchParams: Promise.resolve({}) })),
  },
  {
    name: "مركبات المزاد",
    amounts: [VEHICLE.reserve_price],
    render: () =>
      render(
        AuctionPage({
          params: Promise.resolve({ id: "7" }),
          searchParams: Promise.resolve({}),
        }),
      ),
  },
  {
    name: "صفحة المركبة",
    amounts: [VEHICLE.reserve_price],
    render: () => render(VehiclePage({ params: Promise.resolve({ id: "91" }) })),
  },
  {
    /*
     * الصفحة نفسها وقد دخل صاحبها ورُفض — وهي ثلثاها لا حالةٌ هامشية.
     *
     * Signed out, this page renders a link where the bidding is. So the bid box,
     * the live panel, the favourite marker and a refusal above them — the
     * controls the site exists for — appear in no snapshot at any size unless a
     * screen asks for them, and the layout that goes wrong on a phone is this
     * one: a form, a warning block and two buttons in a column 375 wide.
     *
     * It is also the only screen that renders a class composed at run time
     * (`Notice` builds its own from a tone), which is what the rendered-HTML
     * direction scan below exists to catch and had nothing to catch without it.
     */
    name: "صفحة المركبة — داخل وبرفض",
    signedIn: true,
    flash: REFUSAL,
    amounts: [VEHICLE.reserve_price, LIVE_BID.amount, "45000.00"],
    render: () => render(VehiclePage({ params: Promise.resolve({ id: "91" }) })),
  },
  {
    name: "المزايدات",
    signedIn: true,
    amounts: [LIVE_BID.amount, WITHDRAWN_BID.amount],
    render: () => render(BidsPage({ searchParams: Promise.resolve({}) })),
  },
  {
    name: "المفضّلة",
    signedIn: true,
    amounts: [VEHICLE.reserve_price, OTHER_VEHICLE.reserve_price],
    render: () => render(FavouritesPage({ searchParams: Promise.resolve({}) })),
  },
  {
    /*
     * القائمة الفارغة — أول ما يراه عميل جديد، وتخطيطٌ آخر لا نسخةٌ أقصر.
     *
     * The vehicle grid is the one element on this screen that answers the size,
     * and here it is not rendered at all: a single centred sentence stands in
     * its place. That is why this screen is size-invariant while the full one is
     * not — the emptiness *is* the layout — and a snapshot of the populated list
     * says nothing about the state most new customers open first.
     */
    name: "المفضّلة — بلا مركبات",
    signedIn: true,
    emptyLists: true,
    render: () => render(FavouritesPage({ searchParams: Promise.resolve({}) })),
  },
  {
    name: "الحساب",
    signedIn: true,
    render: () => render(AccountPage()),
  },
  {
    name: "الدخول",
    render: () => render(SignInPage({ searchParams: Promise.resolve({}) })),
  },
  {
    name: "المحفظة",
    signedIn: true,
    amounts: [WALLET.total, WALLET.available, WALLET.held_for_auctions, WALLET.locked_for_dues],
    render: () => render(WalletPage()),
  },
];

async function html(screen: Screen): Promise<string> {
  cookieJar.clear();
  listsAreEmpty = screen.emptyLists === true;
  if (screen.signedIn) cookieJar.set("haraj_access", "session-token");
  // The flash is a cookie the server wrote and this render consumes — the same
  // path a real refusal takes, rather than a prop handed to the component.
  if (screen.flash) cookieJar.set("haraj_flash", JSON.stringify(screen.flash));
  return screen.render();
}

// ---------------------------------------------------------------------------
// فضّ بوادئ Tailwind — أي صنف يسري عند أي عرض
// ---------------------------------------------------------------------------

//: نقاط انكسار Tailwind v4 الافتراضية، بالبكسل. لو غُيِّرت في `@theme` غُيِّرت
//: هنا — وهي مكتوبة مرة واحدة لأن تكرارها هو أن يختلف الاثنان يوماً.
const BREAKPOINTS: Record<string, number> = {
  sm: 640,
  md: 768,
  lg: 1024,
  xl: 1280,
  "2xl": 1536,
};

const SIZES = [
  { name: "جوال 375", width: 375 },
  { name: "لوح 768", width: 768 },
  { name: "سطح مكتب 1280", width: 1280 },
];

//: الشاشات التي تعلن صفر نقاط انكسار، فتخطيطها واحد على المقاسات الثلاثة —
//: بترتيب `SCREENS`. القائمة تُقرأ وتُقرَّر، لا تُستنتج من تطابق ثلاثة ملفات.
const SIZE_INVARIANT = [
  //: «المزادات (الرئيسية)» خرجت من هنا يوم صارت شبكة تصفّح (T1030): شبكة
  //: المركبات تتّسع من عمود إلى ثلاثة، فلقطاتها الثلاث مختلفة فعلاً —
  //: وخروجها من القائمة قرارٌ مكتوب لا صدفةٌ مرّت.
  "المزايدات",
  //: وهذه ليست الشاشة نفسها وقد قصُرت: الشبكة الاستجابية الوحيدة فيها غير
  //: مرندَرة أصلاً حين لا يكون هناك ما يُعرض. المفضّلة العامرة تتّسع، والفارغة
  //: لا شيء فيها يتّسع — وهما سطران هنا لأنهما قراران مختلفان.
  "المفضّلة — بلا مركبات",
  "الدخول",
];

/**
 * الأصناف السارية عند عرضٍ ما، مرتَّبةً كما ترتّبها ورقة الأنماط.
 *
 * A variant this function does not recognise as a breakpoint — `hover:`,
 * `focus:`, `group-*` — drops the whole token: those describe the page under a
 * finger, not the layout at rest, and a snapshot that mixed them would change
 * for reasons that have nothing to do with a screen size.
 */
function applying(classAttribute: string, width: number): string[] {
  const byBreakpoint = new Map<number, string[]>();

  for (const token of classAttribute.split(/\s+/).filter(Boolean)) {
    const parts = token.split(":");
    const bare = parts.pop() as string;
    if (parts.some((variant) => !(variant in BREAKPOINTS))) continue;

    const min = parts.length === 0 ? 0 : Math.max(...parts.map((v) => BREAKPOINTS[v] ?? 0));
    if (width < min) continue;

    const bucket = byBreakpoint.get(min);
    if (bucket) bucket.push(bare);
    else byBreakpoint.set(min, [bare]);
  }

  return [...byBreakpoint.entries()]
    .sort(([a], [b]) => a - b)
    .flatMap(([, tokens]) => tokens);
}

//: عائلات الخصائص التي تقرّر **شكل** الصفحة. غيرها — لون، ظلّ، حجم خطّ — لا
//: يدخل اللقطة: لقطةٌ تتغيّر حين يتغيّر لون حدٍّ هي لقطةٌ يوافق عليها القارئ
//: بلا قراءة، وهي حينها لا تحرس شيئاً.
const FAMILIES: Array<[string, RegExp]> = [
  ["عرض", /^(grid|flex|inline-flex|inline-block|inline|block|hidden|contents|table)$/],
  ["أعمدة", /^grid-cols-(\d+|none|subgrid)$/],
  ["امتداد", /^col-span-(\d+|full)$/],
  ["محور", /^flex-(row|col)(-reverse)?$/],
  ["التفاف", /^flex-(wrap|nowrap|wrap-reverse)$/],
  ["أقصى-عرض", /^max-w-\S+$/],
  ["عرض-مطلق", /^w-\S+$/],
  ["تمرير-أفقي", /^overflow-x-\S+$/],
  ["محاذاة", /^text-(start|end|center|left|right)$/],
  ["توسيط", /^mx-auto$/],
];

/** آخر قيمة تفوز في كل عائلة — وهو ما يفعله المتصفح حين يتساوى الوزن. */
function resolved(classAttribute: string, width: number): Map<string, string> {
  const out = new Map<string, string>();

  for (const token of applying(classAttribute, width)) {
    for (const [family, pattern] of FAMILIES) {
      if (pattern.test(token)) out.set(family, token);
    }
  }

  // `display:grid` بلا `grid-template-columns` عمودٌ واحد — وهو الوضع الفعلي
  // على الجوال لكل شبكة في هذا المستودع، فيُكتب صراحةً بدل أن يُقرأ بالغياب.
  if (out.get("عرض") === "grid" && !out.has("أعمدة")) {
    out.set("أعمدة", "grid-cols-1 (افتراضي)");
  }

  return out;
}

/** مسار العنصر في الوثيقة — يتغيّر حين يتغيّر الهيكل، وهو نصف قيمة اللقطة. */
function pathOf(element: Element): string {
  const parts: string[] = [];

  for (let node: Element | null = element; node && node.tagName !== "BODY"; ) {
    const parent: Element | null = node.parentElement;
    let part = node.tagName.toLowerCase();
    if (parent) {
      const siblings = [...parent.children].filter((c) => c.tagName === node!.tagName);
      if (siblings.length > 1) part += `[${siblings.indexOf(node) + 1}]`;
    }
    parts.unshift(part);
    node = parent;
  }

  return parts.join(">");
}

interface Box {
  path: string;
  classes: string;
  layout: Map<string, string>;
}

function parse(markup: string): Document {
  return new JSDOM(`<!doctype html><html dir="rtl"><body>${markup}</body></html>`).window.document;
}

/** كل عنصر يقرّر شكلاً، بترتيب الوثيقة، عند عرضٍ بعينه. */
function boxes(markup: string, width: number): Box[] {
  const found: Box[] = [];
  for (const element of parse(markup).body.querySelectorAll("[class]")) {
    const classes = element.getAttribute("class") ?? "";
    const layout = resolved(classes, width);
    if (layout.size > 0) found.push({ path: pathOf(element), classes, layout });
  }
  return found;
}

/**
 * كل صنف على كل عنصر — لا الأصناف التي تقرّر الشكل وحدها.
 *
 * `boxes` deliberately keeps only what decides a layout, and a direction class
 * that decides nothing about the *shape* — `ml-2` on a badge — would slip
 * straight through it. This is the wider net, and it exists because the first
 * mutation run proved the narrow one missed exactly that case.
 */
function everyClass(markup: string): Array<{ path: string; token: string }> {
  const found: Array<{ path: string; token: string }> = [];
  for (const element of parse(markup).body.querySelectorAll("[class]")) {
    for (const token of (element.getAttribute("class") ?? "").split(/\s+/)) {
      if (token) found.push({ path: pathOf(element), token });
    }
  }
  return found;
}

/** اللقطة نفسها: سطر لكل عنصر، بالقيم السارية عند هذا العرض. */
function projection(markup: string, width: number): string {
  return boxes(markup, width)
    .map((box, index) => {
      const value = FAMILIES.map(([family]) => family)
        .filter((family) => box.layout.has(family))
        .map((family) => `${family}=${box.layout.get(family)}`)
        .join(" · ");
      return `${String(index + 1).padStart(2, "0")} ${box.path} :: ${value}`;
    })
    .join("\n");
}

/** عدد أعمدة الشبكة الفعلي، أو `null` لعنصر ليس شبكة. */
function columns(box: Box): number | null {
  if (box.layout.get("عرض") !== "grid") return null;
  const declared = box.layout.get("أعمدة") ?? "";
  const match = /grid-cols-(\d+)/.exec(declared);
  return match?.[1] ? Number(match[1]) : 1;
}

/** كل شبكة في الشاشة بمسارها، وعدد أعمدتها عند عرضٍ بعينه. */
function gridsAt(markup: string, width: number): Map<string, number> {
  const found = new Map<string, number>();
  for (const box of boxes(markup, width)) {
    const count = columns(box);
    if (count !== null) found.set(box.path, count);
  }
  return found;
}

// ---------------------------------------------------------------------------
// ١. لقطة بنية لكل شاشة
// ---------------------------------------------------------------------------

describe("لقطات البنية", () => {
  for (const screen of SCREENS) {
    it(screen.name, async () => {
      expect(await html(screen)).toMatchSnapshot();
    });
  }
});

// ---------------------------------------------------------------------------
// ٢. التخطيط الساري عند كل مقاس — ثلاث لقطات مختلفة فعلاً لكل شاشة
// ---------------------------------------------------------------------------

describe("التخطيط الساري على المقاسات الثلاثة", () => {
  for (const screen of SCREENS) {
    for (const size of SIZES) {
      it(`${screen.name} — ${size.name}`, async () => {
        expect(projection(await html(screen), size.width)).toMatchSnapshot();
      });
    }
  }
});

// ---------------------------------------------------------------------------
// ٣. ما يجب أن يصحّ عند كل عرض — قواعد، لا لقطات
// ---------------------------------------------------------------------------

describe("J9 — الشاشة على مقاس جوال", () => {
  it("كل شبكة استجابية تبدأ بعمود واحد على الجوال", async () => {
    // A grid that declares a breakpoint has decided it needs more than one
    // column *somewhere*. Starting it at two on a 375px screen is how a card
    // list becomes two columns of unreadable slivers.
    const offenders: string[] = [];

    for (const screen of SCREENS) {
      for (const box of boxes(await html(screen), 375)) {
        const responsive = /(?:sm|md|lg|xl|2xl):grid-cols-/.test(box.classes);
        if (responsive && columns(box) !== 1) {
          offenders.push(`${screen.name} — ${box.path}: ${box.classes}`);
        }
      }
    }

    expect(offenders).toEqual([]);
  });

  it("ولا شبكة تتجاوز عمودين على الجوال", async () => {
    // The one non-responsive grid in the tree is the vehicle card's spec list —
    // four short label/value pairs, two per row, which is readable at 375. Three
    // columns of anything at that width is not, responsive or otherwise.
    const offenders: string[] = [];

    for (const screen of SCREENS) {
      for (const box of boxes(await html(screen), 375)) {
        const count = columns(box);
        if (count !== null && count > 2) {
          offenders.push(`${screen.name} — ${box.path}: ${box.classes}`);
        }
      }
    }

    expect(offenders).toEqual([]);
  });

  it("الأعمدة لا تنقص كلما اتّسعت الشاشة", async () => {
    // `min-width` media queries only ever add. A layout whose column count falls
    // between 375 and 1280 is a breakpoint written backwards — which reads as
    // "fine on my laptop" and is broken on exactly the tablet nobody tested.
    const offenders: string[] = [];

    for (const screen of SCREENS) {
      const markup = await html(screen);
      const perSize = SIZES.map((size) => gridsAt(markup, size.width));

      for (const path of perSize[0]?.keys() ?? []) {
        const counts = perSize.map((grids) => grids.get(path) ?? 0);
        const rising = counts.every(
          (count, step) => step === 0 || count >= (counts[step - 1] ?? 0),
        );
        if (!rising) offenders.push(`${screen.name} — ${path}: ${counts.join(" → ")}`);
      }
    }

    expect(offenders).toEqual([]);
  });

  it("والشاشات ذات الشبكات الاستجابية تتّسع فعلاً على سطح المكتب", async () => {
    // The other half of the same rule: a breakpoint that changes nothing is a
    // class somebody deleted the effect of and left the name behind. Every
    // screen that declares one must be measurably wider at 1280 than at 375.
    const widened: string[] = [];
    const declared: string[] = [];

    for (const screen of SCREENS) {
      const markup = await html(screen);

      if (!boxes(markup, 375).some((box) => /(?:sm|md|lg|xl|2xl):grid-cols-/.test(box.classes))) {
        continue;
      }
      declared.push(screen.name);

      const phone = gridsAt(markup, 375);
      const desktop = gridsAt(markup, 1280);
      const grew = [...phone].some(([path, before]) => (desktop.get(path) ?? 0) > before);
      if (grew) widened.push(screen.name);
    }

    expect(declared.length).toBeGreaterThan(0);
    expect(widened).toEqual(declared);
  });

  it("ولا بادئة صنف يجهلها الفاضّ — وإلا اختفى الصنف من اللقطة بلا أثر", async () => {
    // The resolver drops any token whose variant it does not recognise as a
    // breakpoint, which is right for `hover:` and wrong for anything new: a
    // `dark:` or a `print:` or an arbitrary `[&>*]:` would leave the size
    // projection silently, and a snapshot missing a line reads exactly like a
    // snapshot that never had one. So the vocabulary is declared, and a variant
    // nobody has decided about fails here instead of disappearing there.
    const known = new Set([...Object.keys(BREAKPOINTS), "hover"]);
    const unknown = new Set<string>();

    for (const screen of SCREENS) {
      for (const { token } of everyClass(await html(screen))) {
        const parts = token.split(":");
        parts.pop();
        for (const variant of parts) if (!known.has(variant)) unknown.add(variant);
      }
    }

    expect([...unknown]).toEqual([]);
  });

  it("والشاشات التي لا يتغيّر تخطيطها بالمقاس معروفة بالاسم", async () => {
    // Four of the eleven render the same layout at 375, 768 and 1280 — they
    // declare no breakpoint at all. That is a legitimate answer for a form, a
    // single-column list and a list with nothing in it, and it is written down
    // here rather than left to be inferred from three matching snapshot files:
    // an identical snapshot proves nothing on its own, and a screen that quietly
    // joins or leaves this list has had its responsive behaviour changed by
    // somebody who should say so.
    const invariant: string[] = [];

    for (const screen of SCREENS) {
      const markup = await html(screen);
      const shapes = new Set(SIZES.map((size) => projection(markup, size.width)));
      if (shapes.size === 1) invariant.push(screen.name);
    }

    expect(invariant).toEqual(SIZE_INVARIANT);
  });

  it("‏`viewport` معلَن، وإلا فالجوال يرندر صفحة سطح مكتب مصغَّرة", async () => {
    // Without `width=device-width` a phone lays the page out at ~980px and
    // scales it down: every media query in the sheet then answers for a screen
    // nobody is holding, and every check above becomes true of nothing.
    const source = await readFile(join("app", "layout.tsx"), "utf8");

    expect(source).toMatch(/export const viewport/);
    expect(source).toMatch(/width:\s*"device-width"/);
    expect(source).toMatch(/initialScale:\s*1/);
  });
});

// ---------------------------------------------------------------------------
// ٤. العربية وRTL — ما يُفحَص منه فعلاً
// ---------------------------------------------------------------------------

async function* walk(directory: string, extensions: string[]): AsyncGenerator<string> {
  for (const entry of await readdir(directory, { withFileTypes: true })) {
    if (entry.name === "node_modules" || entry.name === ".next") continue;
    const path = join(directory, entry.name);
    if (entry.isDirectory()) yield* walk(path, extensions);
    else if (extensions.some((extension) => entry.name.endsWith(extension))) yield path;
  }
}

//: أصناف تعرف اليمين من اليسار. هذه بالضبط هي التي **لا** تنعكس مع `dir="rtl"`،
//: فالصنف يبقى على اليسار في صفحة تُقرأ من اليمين — وهو الشكل الوحيد الذي
//: ينكسر به RTL بلا أن يظهر شيء في مراجعة الشيفرة.
const PHYSICAL_EXACT = new Set([
  "text-left",
  "text-right",
  "float-left",
  "float-right",
  "border-l",
  "border-r",
  "rounded-l",
  "rounded-r",
  "space-x-reverse",
  "divide-x-reverse",
  "flex-row-reverse",
  "flex-col-reverse",
]);

const PHYSICAL_PREFIXES = [
  "ml-",
  "mr-",
  "pl-",
  "pr-",
  "left-",
  "right-",
  "border-l-",
  "border-r-",
  "rounded-l-",
  "rounded-r-",
  "rounded-tl-",
  "rounded-tr-",
  "rounded-bl-",
  "rounded-br-",
  "scroll-ml-",
  "scroll-mr-",
  "origin-left",
  "origin-right",
];

function isPhysical(token: string): boolean {
  const bare = token.split(":").pop() as string;
  if (PHYSICAL_EXACT.has(bare)) return true;
  return PHYSICAL_PREFIXES.some((prefix) => bare.startsWith(prefix));
}

describe("العربية وRTL", () => {
  it("‏`lang` و`dir` على الوثيقة", async () => {
    // On `<html>`, not on a wrapper inside it: Tailwind's logical properties,
    // the browser's caret and selection behaviour and a screen reader's
    // pronunciation all read the direction from there.
    //
    // Read as source rather than rendered. `app/layout.tsx` imports
    // `next/font/google`, which is a build-time transform and not a function
    // outside Next's pipeline — so rendering it here would test a mock of the
    // font loader, and the attribute is what is under test.
    const source = await readFile(join("app", "layout.tsx"), "utf8");

    expect(source).toMatch(/<html[^>]*lang="ar"/);
    expect(source).toMatch(/<html[^>]*dir="rtl"/);
  });

  it("ولا صفحة تعلن اتجاهها بنفسها", async () => {
    // A screen that grew its own `dir` is the beginning of the retrofit T1003
    // exists to prevent — and the second one would disagree with the first.
    const offenders: string[] = [];

    for (const root of ["app", "features"]) {
      for await (const path of walk(root, [".tsx"])) {
        if (path.endsWith(join("app", "layout.tsx"))) continue;
        const source = await readFile(path, "utf8");
        if (/\bdir\s*=\s*["'{]/.test(source)) offenders.push(path);
      }
    }

    expect(offenders).toEqual([]);
  });

  it("لا صنف اتجاه فيزيائي في المصدر", async () => {
    // The failure this catches is silent by construction: `ml-4` renders, looks
    // deliberate in a diff, and puts the margin on the wrong side of every
    // Arabic screen it appears on. The logical twin (`ms-4`) is one letter away.
    const offenders: string[] = [];

    for (const root of ["app", "features"]) {
      for await (const path of walk(root, [".tsx", ".ts"])) {
        const source = await readFile(path, "utf8");
        // Every string and template literal in the file, tokenised. Reading the
        // literals rather than the raw text keeps an English word in a comment
        // from being read as a class name.
        for (const [, single, double, template] of source.matchAll(
          /'([^'\n]*)'|"([^"\n]*)"|`([^`]*)`/g,
        )) {
          for (const token of (single ?? double ?? template ?? "").split(/\s+/)) {
            if (token && isPhysical(token)) offenders.push(`${path}: ${token}`);
          }
        }
      }
    }

    expect(offenders).toEqual([]);
  });

  it("ولا في HTML المرندَر — حيث تظهر الأصناف المركَّبة في زمن التشغيل", async () => {
    // `Notice` builds its class string from a tone. A source scan reads the two
    // halves separately and can miss what they add up to; the rendered document
    // is the only place the composed value exists.
    const offenders: string[] = [];

    for (const screen of SCREENS) {
      for (const { path, token } of everyClass(await html(screen))) {
        if (isPhysical(token)) offenders.push(`${screen.name} — ${path}: ${token}`);
      }
    }

    expect(offenders).toEqual([]);
  });

  it("ولا خاصية CSS فيزيائية في الورقة، وجزيرة الـLTR وحيدة ومعلنة", async () => {
    // `.money` sets `direction: ltr` on purpose — a number reads left to right
    // in Arabic too, and an amount caught in the bidi algorithm is an amount
    // whose minus sign moves. It is the one exception, so it is named here: a
    // second `direction` rule appearing in this sheet is a retrofit starting.
    const sheet = await readFile(join("app", "globals.css"), "utf8");

    const island = /\.money\s*\{[^}]*\}/.exec(sheet);
    expect(island).not.toBeNull();
    expect(island?.[0]).toContain("direction: ltr");

    const rest = sheet.replace(/\.money\s*\{[^}]*\}/, "").replace(/\/\*[\s\S]*?\*\//g, "");

    expect(rest).not.toMatch(/\b(?:margin|padding|border|inset)-(?:left|right)\b/);
    expect(rest).not.toMatch(/\btext-align\s*:\s*(?:left|right)\b/);
    expect(rest).not.toMatch(/\bdirection\s*:/);
  });
});

// ---------------------------------------------------------------------------
// ٥. المبالغ في اللقطات نصوص عشرية
// ---------------------------------------------------------------------------

describe("المبالغ كما وصلت", () => {
  it("كل مبلغ يظهر حرفاً بحرف على شاشته", async () => {
    for (const screen of SCREENS) {
      const markup = await html(screen);
      for (const value of screen.amounts ?? []) {
        expect(markup, `${screen.name} — ${value}`).toContain(value);
      }
    }
  });

  it("ولا نسخة منسَّقة منه في أي شاشة", async () => {
    // A thousands separator or an Arabic-Indic digit inside an amount is the
    // fingerprint of a number that was parsed and re-printed somewhere between
    // the ledger and the screen. `1500.75` reaching a customer as `١٬٥٠٠٫٧٥` is
    // a value they cannot match against their bank statement — and one that
    // arrived by way of a `Number`.
    const separated = SCREENS.flatMap((screen) => screen.amounts ?? []).map((value) =>
      value.replace(/\B(?=(\d{3})+\.)/, ","),
    );

    for (const screen of SCREENS) {
      const markup = await html(screen);
      for (const value of separated) {
        expect(markup, `${screen.name} — ${value}`).not.toContain(value);
      }
      expect(markup, screen.name).not.toMatch(/[٠-٩۰-۹]/);
    }
  });
});

// ---------------------------------------------------------------------------
// ٦. ما كان يُفحَص قبل هذه الجولة، ولا يزال
// ---------------------------------------------------------------------------

describe("الثلاثة مقاسات — ما يمكن إثباته بلا متصفح", () => {
  it("لا عرض ثابت بالبكسل في أي شاشة", async () => {
    // The one authoring mistake that reliably breaks a phone. It renders
    // identically in a string test and produces a horizontal scrollbar on every
    // phone — which is exactly why a text check earns its place here.
    const offenders: string[] = [];

    for (const root of ["app", "features"]) {
      for await (const path of walk(root, [".tsx", ".css"])) {
        const source = await readFile(path, "utf8");
        // `w-[420px]`, `width: 420px`, `min-width: 900px` — a fixed floor wider
        // than a phone. `max-width` is fine and is how the layouts are written.
        if (/\bw-\[\d{3,}px\]|(?<!max-)\bmin-width:\s*\d{3,}px|(?<!max-)\bwidth:\s*\d{3,}px/.test(source)) {
          offenders.push(path);
        }
      }
    }

    expect(offenders).toEqual([]);
  });

  it("الجداول العريضة تمرّر أفقياً داخل نفسها", async () => {
    // A statement table on a phone either scrolls inside its own container or
    // makes the whole page scroll sideways. The second is how a page stops
    // being readable at all.
    const source = await readFile(join("app", "wallet", "statement", "page.tsx"), "utf8");

    expect(source).toContain("overflow-x-auto");
  });
});
