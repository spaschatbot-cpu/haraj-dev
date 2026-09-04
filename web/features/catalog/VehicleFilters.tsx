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
      className="mb-6 grid gap-3 rounded-lg border border-neutral-200 bg-white p-4 sm:grid-cols-2 lg:grid-cols-5"
    >
      {keep.map((name) => {
        const value = values.get(name);
        return value ? <input key={name} type="hidden" name={name} value={value} /> : null;
      })}

      <label className="flex flex-col gap-1 text-sm lg:col-span-2">
        <span className="text-neutral-600">بحث</span>
        <input
          type="search"
          name="search"
          defaultValue={values.get("search") ?? ""}
          placeholder="ماركة أو طراز أو رقم لوت"
          className="rounded border border-neutral-300 px-3 py-2"
        />
      </label>

      <label className="flex flex-col gap-1 text-sm">
        <span className="text-neutral-600">الماركة</span>
        <input
          type="text"
          name="make"
          defaultValue={values.get("make") ?? ""}
          className="rounded border border-neutral-300 px-3 py-2"
        />
      </label>

      <label className="flex flex-col gap-1 text-sm">
        <span className="text-neutral-600">من سنة</span>
        <input
          type="number"
          name="year_from"
          inputMode="numeric"
          defaultValue={values.get("year_from") ?? ""}
          className="rounded border border-neutral-300 px-3 py-2"
        />
      </label>

      <label className="flex flex-col gap-1 text-sm">
        <span className="text-neutral-600">إلى سنة</span>
        <input
          type="number"
          name="year_to"
          inputMode="numeric"
          defaultValue={values.get("year_to") ?? ""}
          className="rounded border border-neutral-300 px-3 py-2"
        />
      </label>

      <div className="flex items-end gap-3 lg:col-span-5">
        <button
          type="submit"
          className="rounded bg-neutral-900 px-4 py-2 text-sm text-white"
        >
          طبّق الترشيح
        </button>
        {/*
          A link and not a reset button: `type="reset"` restores the fields in
          the browser and leaves the url — and therefore the results — exactly as
          they were, which reads as a broken button.
        */}
        {filtered ? (
          <a href={resetHref} className="text-sm text-neutral-600 underline">
            إزالة الترشيح
          </a>
        ) : null}
      </div>
    </form>
  );
}
