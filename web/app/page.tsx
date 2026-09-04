/**
 * شاشة التصفّح — شبكة مركبات مسطّحة تحت تبويب بحالة المزاد. T1030.
 *
 * ما الذي تغيّر عن «قائمة مزادات ثم مركباتها»
 * ===========================================
 * مزادٌ واحد في الأسبوع يعني أن قائمة المزادات صفحةٌ فيها سطرٌ واحد، وأن
 * الزائر يدفع نقرةً كاملة ليصل إلى الشيء الوحيد الذي جاء من أجله: السيارات.
 * فصار المدخل شبكةً مسطّحة **عبر** المزادات، والتبويب هو «أيّ مزاد أنظر إليه
 * الآن»: قريباً · نشط · منتهي. و`/auctions` باقيةٌ كما هي — التبويبات مدخلٌ
 * جديد لا بديلٌ يحذف ما يعمل.
 *
 * مرندَرة في الخادم — معيار J5
 * ============================
 * لا `use client` في هذه الشاشة ولا في شيء تستدعيه إلا العدّاد. طلبٌ بلا
 * جافاسكربت يُرجع أسماء المركبات وأسعارها والعدّادات الثلاثة **نصّاً في
 * الـHTML**؛ والعدّاد التنازلي وحده يحتاج المتصفح، وهو يبدأ من قيمةٍ حسبها
 * الخادم فلا يترك فراغاً قبل أن يعمل. `lib/__tests__/phase-tabs.test.ts` يرندر
 * هذه الصفحة إلى نصّ ثابت ويؤكّد ذلك.
 *
 * طلبٌ واحد
 * =========
 * الصفحة والعدّادات الثلاثة تصل معاً — انظر `features/browse/browse.ts` لسبب
 * كون ذلك قاعدةً لا تحسيناً.
 *
 * والفشل والفراغ شاشتان، لا غياب
 * ==============================
 * حين يرفض الخادم أو لا يُجيب تُعرض جملته والتبويبات فوقها، فيبقى للزائر شيء
 * يفعله (يبدّل التبويب، يعيد المحاولة). وحين يردّ بلا مركبات يُقال **لماذا**:
 * «لا مزاد قادم الآن» شيء، و«لا مطابق لبحثك» شيء آخر، وشبكةٌ بيضاء ليست أياً
 * منهما.
 */

import type { Metadata } from "next";

import { browse } from "@/features/browse/browse";
import { PhaseTabs } from "@/features/browse/PhaseTabs";
import { readPhase, tabOf } from "@/features/browse/phase";
import { Pagination } from "@/features/catalog/Pagination";
import { VehicleGrid } from "@/features/catalog/VehicleCard";
import { VehicleFilters, isFiltered, readFilters } from "@/features/catalog/VehicleFilters";
import { PageShell } from "@/features/shell/PageShell";
import { messageOf } from "@/lib/api";
import { respondedAt } from "@/lib/format";
import { readPaging, toParams } from "@/lib/paging";

export const metadata: Metadata = {
  title: { absolute: "حراج — تصفّح المركبات" },
  description: "مركبات المزاد القريب والجاري والمنتهي، بعدّاد لكل حالة.",
};

//: تُرندَر لكل طلب. حالة المزاد وعدّادات التبويبات تتغيّر خلال اليوم، وصفحةٌ
//: محفوظة وقت البناء تقول لزائرٍ إن المزاد ما زال جارياً بعد ساعة من إغلاقه.
export const dynamic = "force-dynamic";

const PATH = "/";

export default async function Home({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const query = toParams(await searchParams);
  const { limit, offset } = readPaging(query);
  const phase = readPhase(query);
  const tab = tabOf(phase);
  const now = await respondedAt();

  let page: Awaited<ReturnType<typeof browse>> | null = null;
  let refusal: string | null = null;

  try {
    page = await browse({ phase, filters: readFilters(query), limit, offset });
  } catch (error) {
    // جملة الخادم كما كتبها — الويب لا يؤلّف نصّاً لرفضٍ يعرفه الخادم
    // (`lib/api/errors.ts`). وهي هنا لا في حدود الخطأ، لتبقى التبويبات
    // معروضة: زائرٌ أمام شاشة فارغة يعيد التحميل، وأمام تبويبات يجرّب غيرها.
    refusal = messageOf(error);
  }

  return (
    <PageShell title="تصفّح المركبات">
      <PhaseTabs current={phase} counts={page?.counts ?? null} query={query} path={PATH} />

      <VehicleFilters action={PATH} values={query} keep={["phase"]} />

      {refusal === null && page !== null ? (
        <>
          <VehicleGrid
            vehicles={page.vehicles}
            now={now}
            empty={isFiltered(query) ? "لا مركبات مطابقة لبحثك في هذا التبويب." : tab.empty}
          />

          <Pagination
            query={query}
            total={page.total}
            limit={limit}
            offset={offset}
            path={PATH}
          />
        </>
      ) : (
        <div
          role="status"
          className="rounded-lg border border-amber-200 bg-amber-50 p-6 text-center"
        >
          <p className="text-amber-900">{refusal}</p>
          <p className="mt-2 text-sm text-amber-800">
            لم تصل قائمة المركبات. جرّب تحديث الصفحة أو تبويباً آخر.
          </p>
        </div>
      )}
    </PageShell>
  );
}
