/**
 * العرض في مكان واحد — التاريخ والوقت والمبلغ.
 *
 * Rule 5 of spec 011 asks that times arrive UTC from the server and be
 * converted for display **in one place in the web**, the way `apps/core/time`
 * does it for the backend. This is that place. Two screens each calling
 * `toLocaleString` with their own options is two screens that show the same
 * auction ending at two different times the day one of them is edited.
 *
 * And the money rule, which is not a formatting preference but Article 3-2:
 * **an amount is rendered exactly as it arrived.** The server sends `"1500.00"`
 * as a string, and it reaches the screen as `"1500.00"`. Nothing here parses
 * one, adds one, rounds one, or inserts a thousands separator into one:
 *
 * * `Number("0.1") + Number("0.2")` is `0.30000000000000004` in JavaScript, so
 *   any arithmetic on a money string is a wrong balance waiting for the right
 *   two numbers;
 * * and a customer comparing this page against a statement or an invoice must
 *   not have to undo a display transformation in their head — which is the same
 *   reason every console template uses `unlocalize`.
 *
 * `ops/checks/web_money_is_never_computed.mjs` fails the build on the first
 * `Number(price)` anybody writes.
 */

//: One timezone for the whole product. The auctions are held in Saudi Arabia
//: and the times shown are the times the auction actually runs, so a customer
//: travelling does not see an auction "ending" at a different hour than the one
//: the yard is working to.
export const TIMEZONE = "Asia/Riyadh";

//: Arabic locale with Latin digits. Latin deliberately: the customer compares
//: these numbers against a bank statement, an Odoo invoice and an SMS, and all
//: three carry Latin digits.
const LOCALE = "ar-SA-u-nu-latn";

const DATE_TIME = new Intl.DateTimeFormat(LOCALE, {
  timeZone: TIMEZONE,
  dateStyle: "medium",
  timeStyle: "short",
});

const DATE_ONLY = new Intl.DateTimeFormat(LOCALE, {
  timeZone: TIMEZONE,
  dateStyle: "medium",
});

/**
 * A server timestamp, as a person reads it. Empty string for a missing one.
 *
 * An empty string rather than a dash or `"—"`: what to show in place of a
 * missing value is the calling screen's decision, and a helper that decides it
 * puts that punctuation in places nobody chose it for.
 */
export function dateTime(value: string | null | undefined): string {
  if (!value) return "";
  const moment = new Date(value);
  return Number.isNaN(moment.getTime()) ? "" : DATE_TIME.format(moment);
}

export function date(value: string | null | undefined): string {
  if (!value) return "";
  const moment = new Date(value);
  return Number.isNaN(moment.getTime()) ? "" : DATE_ONLY.format(moment);
}

/**
 * An amount, exactly as the server sent it. **No arithmetic, ever.**
 *
 * The only thing this function does is answer the "there is no amount" case in
 * one place, so every screen renders a missing price the same way rather than
 * one showing `null` and the next showing an empty cell. The digits themselves
 * are untouched — see the module docstring for why that is a rule and not a
 * style.
 */
export function amount(value: string | null | undefined): string {
  return value ?? "";
}

// ---------------------------------------------------------------------------
// المدّة الباقية — فرقٌ بين لحظتين، لا تاريخٌ يُبنى ثم يُطرح منه
// ---------------------------------------------------------------------------

const SECOND = 1000;
const MINUTE = 60;
const HOUR = 60 * MINUTE;
const DAY = 24 * HOUR;

/** «٣ أيام»، «يومان» — الصيغة العربية في مكان واحد بدل أن تُخمَّن في كل شاشة. */
function plural(value: number, one: string, two: string, few: string, many: string): string {
  if (value === 1) return one;
  if (value === 2) return two;
  //: بلا فاصل آلاف — المدّة عدّ لا مبلغ، وفاصلةٌ فيها تقرأ كتنسيق مالٍ تسلّل
  //: إلى شاشة، وهو بالضبط ما تبحث عنه فحوص المبالغ.
  return `${value} ${value <= 10 ? few : many}`;
}

/**
 * ما بقي من الوقت حتى `endsAt`، أو `null` إن مضى أو لم يُعرف.
 *
 * **فرقٌ بين لحظتين UTC، وهذا هو كل شيء.** `Date.parse` يعطي لحظةً مطلقة على
 * خط الزمن، و`now` مثلها، والطرح بينهما مدّةٌ لا منطقةَ زمنية لها ولا تتأثر
 * بتغيّر اليوم عند منتصف الليل المحلي. الطريقة الأخرى — أن يُبنى تاريخ محلي من
 * النصّ ثم يُطرح منه تاريخ محلي آخر — هي التي تنكسر عند تغيّر اليوم وعند
 * اختلاف المنطقة، ولذلك لا تُكتب هنا ولا في أي مكان آخر.
 *
 * **و`null` ليست «انتهى المزاد».** هي «مضت اللحظة المعلَنة بحسب هذه الساعة»،
 * وساعةُ جهاز العميل ليست الحقيقة: في v1 بُني العدّاد على هذه المقارنة، فأظهر
 * «انتهى» لمن ساعته متقدّمة دقيقتين والمزاد ما زال مفتوحاً. من يقرّر أن المزاد
 * انتهى هو الخادم وحده، عبر حالة الكرت وتبويبه — ومن يقرأ هذه الدالة يعرض
 * جملةً عن **الوقت المعلَن**، لا حكماً على المزاد.
 *
 * الشكل: يومٌ فأكثر تُقرأ بالأيام والساعات — لا أحد يتابع الثواني قبل ثلاثة
 * أيام — وما دون اليوم ساعةٌ ودقيقةٌ وثانية، لأن آخر ساعة هي التي تُتابَع.
 */
export function remaining(
  endsAt: string | null | undefined,
  now: number,
): string | null {
  if (!endsAt) return null;

  const end = Date.parse(endsAt);
  if (Number.isNaN(end)) return null;

  const seconds = Math.floor((end - now) / SECOND);
  if (seconds <= 0) return null;

  const days = Math.floor(seconds / DAY);
  if (days > 0) {
    const hours = Math.floor((seconds % DAY) / HOUR);
    const spelledDays = plural(days, "يوم واحد", "يومان", "أيام", "يوماً");
    if (hours === 0) return spelledDays;
    return `${spelledDays} و${plural(hours, "ساعة", "ساعتان", "ساعات", "ساعة")}`;
  }

  const clock = [
    Math.floor(seconds / HOUR),
    Math.floor((seconds % HOUR) / MINUTE),
    seconds % MINUTE,
  ];
  return clock.map((part) => String(part).padStart(2, "0")).join(":");
}

/**
 * لحظة إنتاج هذا الرد — نقطة انطلاق كل عدّاد على الصفحة.
 *
 * تُقرأ **مرة واحدة لكل طلب** في طبقة البيانات، ثم تُمرَّر إلى ما يعرضها. لا
 * تُقرأ داخل رندرة مكوّن، لسببين لكلٍّ منهما وزن:
 *
 * ١. رندرة المكوّن يجب أن تكون دالّة صرفة في مدخلاتها — و`react-hooks/purity`
 *    يرفض ذلك صراحةً — لأن مكوّناً يقرأ الساعة بنفسه يُنتج شيئاً مختلفاً في
 *    كل إعادة رندرة بلا أن يتغيّر مدخل؛
 * ٢. واثنتا عشرة بطاقة تقرأ الساعة اثنتي عشرة مرة هي اثنتا عشرة لحظة مختلفة
 *    في صفحة واحدة. العدّادات على صفحةٍ واحدة يجب أن تنطلق من لحظة واحدة، وإلا
 *    اختلفت ثانيةً عن جارتها بلا سبب يراه أحد.
 *
 * وهي `async` لأن موضعها هو مرحلة جلب البيانات في مكوّن الخادم، حيث تُنتظَر مع
 * ما يُنتظَر — لا مرحلة الرندرة.
 */
export async function respondedAt(): Promise<number> {
  return Date.now();
}

/** An integer the server sent, for display. Never used on a money value. */
export function count(value: number | null | undefined): string {
  return value === null || value === undefined ? "" : value.toLocaleString(LOCALE);
}
