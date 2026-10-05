/**
 * الفاتورة كما يراها العميل — حالتُها وتفصيلُها، في مكانٍ واحد.
 *
 * كرتُ المشتريات وصفحةُ الفاتورة يعرضان الشيءَ نفسَه، فيُبنيان من هنا: لو
 * كتب كلٌّ منهما تفصيلَه لاختلف ترتيبُ البنود بينهما في أوّل تعديل. والبنودُ
 * بترتيب v1 (`menu/purchases.php`): سعرُ المركبة، الرسوم، الضريبة، الإجمالي،
 * المدفوع، المتبقّي.
 *
 * وكلُّ رقمٍ حقلٌ من الخادم كما هو — لا جمعَ ولا طرحَ هنا. `outstanding` بالذات
 * ليس `amount - amount_paid`: الملغاةُ متبقّيها صفرٌ أيّاً كانت أعمدتُها.
 */

import { amount } from "@/lib/format";

export type InvoiceView = {
  id?: number;
  number?: string;
  state?: string;
  state_label?: string;
  amount?: string;
  amount_paid?: string;
  outstanding?: string;
  net_amount?: string;
  admin_fee?: string;
  tax_amount?: string;
};

//: المعنى قبل اللون (`docs/palette.md` §٢): المسدَّدةُ تمّت، والمستحقّةُ تنتظر،
//: والمسودّةُ والملغاةُ لا حالةَ لهما يُنتظر منها شيء.
const TONE: Record<string, string> = {
  paid: "tone-emerald",
  partial: "tone-amber",
  open: "tone-amber",
  draft: "tone-slate",
  cancelled: "tone-slate",
};

export function InvoiceStateChip({ invoice }: { invoice: InvoiceView }) {
  return (
    <span
      className={`${TONE[invoice.state ?? ""] ?? "tone-slate"} inline-block rounded-full border px-3 py-0.5 text-label-sm`}
    >
      {invoice.state_label}
    </span>
  );
}

function Row({ label, value, strong }: { label: string; value?: string; strong?: boolean }) {
  return (
    <div className="flex justify-between gap-4">
      <dt className="text-neutral-500">{label}</dt>
      <dd className={`money${strong ? " font-semibold" : ""}`}>{amount(value)}</dd>
    </div>
  );
}

/**
 * التفصيلُ يظهر حين يوجد. فاتورةُ أودو المرآةُ تصل بإجماليٍّ بلا بنود — أصفارٌ
 * ثلاثة بحكم القيد `invoice_parts_add_up_to_its_total` — وعرضُ «سعر المركبة ٠»
 * عليها كذبٌ بالأرقام. فتُعرض بإجماليها وحده.
 */
export function InvoiceBreakdown({ invoice }: { invoice: InvoiceView }) {
  const itemised = [invoice.net_amount, invoice.admin_fee, invoice.tax_amount].some(
    (part) => Number(part ?? 0) !== 0,
  );

  return (
    <dl className="space-y-2 text-sm">
      {itemised ? (
        <>
          <Row label="سعر المركبة" value={invoice.net_amount} />
          <Row label="رسوم إدارية" value={invoice.admin_fee} />
          <Row label="الضريبة" value={invoice.tax_amount} />
        </>
      ) : null}
      <Row label="المبلغ" value={invoice.amount} strong={itemised} />
      <Row label="المسدَّد" value={invoice.amount_paid} />
      <Row label="المتبقّي" value={invoice.outstanding} strong />
    </dl>
  );
}
