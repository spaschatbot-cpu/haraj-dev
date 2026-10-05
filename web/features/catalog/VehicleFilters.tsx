/**
 * الترشيح — نموذج `GET` يعمل بلا جافاسكربت. T1008.
 *
 * A plain `<form method="get">`. No state, no handler, no fetch: the browser
 * serialises the fields into the query string and asks the server again, and the
 * server component re-renders the list from `apps/auctions/listing.py`.
 *
 * That is the acceptance criterion — *الترشيح يعمل بلا جافاسكربت (نموذج GET)؛
 * والنتيجة تطابق التطبيق لنفس المعايير* — and the second half of it is why the
 * filtering is not done in the browser. A client-side filter would be a second
 * implementation of "which cars match", and the two would agree until one was
 * edited; then the app and the web would answer the same search differently
 * (rule 3, and Article 4-5).
 *
 * It also means every filtered view has a url. A customer who found four cars
 * can send that search to somebody, and a crawler can follow it.
 *
 * The fields here are exactly the query parameters the contract declares for
 * `vehicles_list` — `search`, `make`, `year_from`, `year_to`. Adding a filter
 * means adding it to the API first (rule 1), where the app inherits it.
 */

//: Kept out of the markup so the reset link and the inputs cannot disagree
//: about which names belong to the filter and which belong to paging.
export const FILTER_FIELDS = ["search", "make", "year_from", "year_to"] as const;

/**
 * المرشِّحات الموجودة في العنوان، محصورةً في ما يعلنه العقد.
 *
 * معاملٌ لا نعرفه يصل في العنوان يُسقَط هنا بدل أن يُمرَّر ليرفضه الـAPI برسالة
 * لا يستطيع الزائر أن يفعل بها شيئاً.
 *
 * وهي دالة واحدة لأنها كانت حلقةً مكتوبة في صفحة المزاد، وشبكةُ الجذر تحتاج
 * الحلقة نفسها: نسختان تعنيان أن مرشِّحاً يُضاف يوماً فيعمل في شاشة ولا يعمل
 * في الأخرى (المادة ٤-٥).
 */
export function readFilters(query: URLSearchParams): Record<string, string> {
  const filters: Record<string, string> = {};
  for (const field of FILTER_FIELDS) {
    const value = query.get(field);
    if (value) filters[field] = value;
  }
  return filters;
}

/** هل يُرشَّح الآن؟ — فالفراغ حينها سببه البحث لا التبويب. */
export function isFiltered(query: URLSearchParams): boolean {
  return FILTER_FIELDS.some((field) => query.get(field));
}

export function VehicleFilters({
  action,
  values,
  keep = [],
}: {
  /** The route this form submits back to — its own page. */
  action: string;
  values: URLSearchParams;
  /**
   * معاملاتٌ في العنوان يجب أن تنجو من الإرسال — التبويب أوّلها.
   *
   * نموذج `GET` يستبدل سلسلة الاستعلام كلها بحقوله، فبحثٌ داخل تبويب «منتهي»
   * كان سيعيد الزائر إلى التبويب الافتراضي بلا أن يطلب ذلك. الحقل المخفي هو
   * ما يجعل البحث يبقى **داخل** التبويب الذي فُتح فيه.
   */
  keep?: readonly string[];
}) {
  const filtered = isFiltered(values);

  //: «إزالة الترشيح» تزيل الترشيح وحده. لو أعادت الزائر إلى العنوان العاري
  //: لأخرجته من تبويبه أيضاً — وهو لم يطلب ذلك، وسيقرؤه انتقالاً لا مسحاً.
  const cleared = new URLSearchParams();
  for (const name of keep) {
    const value = values.get(name);
    if (value) cleared.set(name, value);
  }
  const resetHref = cleared.toString() ? `${action}?${cleared.toString()}` : action;

  return (
    <form
      method="get"
      action={action}
      /*
        شريطٌ في بطاقةٍ واحدة على اثنتي عشرة خانة — نظام التصميم (T1032).
        ولونُه وحركتُه في `globals.css` (`.search-bar`) لا هنا: قيمةٌ تُكتب في
        مكوّنٍ تُنسخ إلى الثاني ثمّ تفترق (`docs/palette.md` §٣-٢).
        والحقول في صفٍّ واحد على سطح المكتب لأن الترشيح فعلٌ واحد: أربعةُ
        حقولٍ متفرّقة تُقرأ أربعةَ قراراتٍ منفصلة.
      */
      className="search-bar mb-6 grid grid-cols-1 items-end gap-3 rounded-2xl p-4 shadow-sm md:grid-cols-12"
    >
      {keep.map((name) => {
        const value = values.get(name);
        return value ? <input key={name} type="hidden" name={name} value={value} /> : null;
      })}

      <label className="flex flex-col gap-1 md:col-span-4">
        <span className="search-label text-caption font-semibold">بحث</span>
        <input
          type="search"
          name="search"
          defaultValue={values.get("search") ?? ""}
          placeholder="ماركة / طراز / رقم الموقف…"
          className="search-field h-11 w-full rounded-lg px-3 text-body-md"
        />
      </label>

      {/*
        حقلُ نصّ لا قائمة اختيار، وإن كان التصميم المرجعيّ قائمة.

        قائمةٌ بأسماء الماركات هنا تعني **مصدراً ثانياً** لما تعرفه قاعدة
        البيانات: ماركةٌ تدخل المخزون ولا تدخل هذه القائمة تصير غير قابلة
        للترشيح، وماركةٌ تخرج تبقى خياراً يعطي صفر نتيجة. وليس في العقد نقطةٌ
        تُعيد الماركات المتاحة — يوم تُضاف، تصير القائمة صحيحة وتُبنى.
      */}
      <label className="flex flex-col gap-1 md:col-span-3">
        <span className="search-label text-caption font-semibold">الماركة</span>
        <input
          type="text"
          name="make"
          defaultValue={values.get("make") ?? ""}
          placeholder="تويوتا…"
          className="search-field h-11 w-full rounded-lg px-3 text-body-md"
        />
      </label>

      <label className="flex flex-col gap-1 md:col-span-2">
        <span className="search-label text-caption font-semibold">من سنة</span>
        <input
          type="number"
          name="year_from"
          inputMode="numeric"
          defaultValue={values.get("year_from") ?? ""}
          className="search-field h-11 w-full rounded-lg px-3 text-body-md tnum"
        />
      </label>

      <label className="flex flex-col gap-1 md:col-span-2">
        <span className="search-label text-caption font-semibold">إلى سنة</span>
        <input
          type="number"
          name="year_to"
          inputMode="numeric"
          defaultValue={values.get("year_to") ?? ""}
          className="search-field h-11 w-full rounded-lg px-3 text-body-md tnum"
        />
      </label>

      <div className="flex items-center gap-3 md:col-span-1">
        <button
          type="submit"
          className="search-submit flex h-11 w-full items-center justify-center gap-1.5 rounded-lg px-4 text-label-md"
        >
          <svg
            className="search-icon h-4 w-4 shrink-0"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.5"
            strokeLinecap="round"
            aria-hidden="true"
          >
            <circle cx="11" cy="11" r="7" />
            <path d="m20 20-3.5-3.5" />
          </svg>
          طبّق
        </button>
        {/*
          A link and not a reset button: `type="reset"` restores the fields in
          the browser and leaves the url — and therefore the results — exactly as
          they were, which reads as a broken button.
        */}
        {filtered ? (
          <a
            href={resetHref}
            className="search-label whitespace-nowrap text-label-md underline"
          >
            إزالة
          </a>
        ) : null}
      </div>
    </form>
  );
}
