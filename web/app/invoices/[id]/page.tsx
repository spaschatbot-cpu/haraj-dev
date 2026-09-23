/**
 * فاتورة واحدة، وسدادها — T1023.
 *
 * The methods offered are `invoice.payment_methods`, which the server computes
 * for **this** invoice. A list written here would be a second opinion about how
 * a purchase may be settled — and it would offer a card, which
 * `PaymentMethod` deliberately does not have: a purchase is settled from money
 * already deposited or by a bank transfer the bank confirms, never by a card
 * charge that can be reversed months later against a vehicle that has already
 * left the yard.
 *
 * `outstanding` is a server field, not `amount - amount_paid` worked out here.
 * The subtraction looks safe and is not: a cancelled invoice's outstanding is
 * zero regardless of what its columns say, and that rule lives on the model.
 */

import type { Metadata } from "next";
import { cookies } from "next/headers";
import { notFound, redirect } from "next/navigation";

import { Notice } from "@/features/shell/Notice";
import { PageShell } from "@/features/shell/PageShell";
import { ApiError, api, request } from "@/lib/api";
import { readFlash } from "@/lib/flash";
import { amount, dateTime } from "@/lib/format";
import { readNumber } from "@/lib/paging";
import { authHeader, hasSession } from "@/lib/session";

export const metadata: Metadata = {
  title: "الفاتورة",
  robots: { index: false, follow: false },
};

export const dynamic = "force-dynamic";

//: One entry of `invoice.payment_methods`. The server sends the value *and* its
//: Arabic name, so there is no label table here at all — which is the same rule
//: the vehicle card follows: a translation kept in the web is a second
//: definition of what a value is called, and it goes stale silently.
export default async function InvoicePage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const store = await cookies();
  if (!hasSession(store)) redirect("/sign-in");

  const { id } = await params;
  const invoiceId = readNumber(id, 0);
  const flash = readFlash(store);
  const headers = authHeader(store);

  let invoice;
  try {
    invoice = await request(() =>
      api.GET("/api/v1/invoices/{id}/", { headers, params: { path: { id: invoiceId } } }),
    );
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) notFound();
    if (error instanceof ApiError && (error.status === 401 || error.status === 403)) {
      redirect("/sign-in");
    }
    throw error;
  }

  // حسابُ الشركة للحوالة — نقطةٌ عامّة (`AllowAny`)، وفشلُها لا يُسقط الفاتورة:
  // تُعرض بلا رقم حسابٍ وبجملةٍ تقول ذلك، لا شاشةَ خطأٍ مكان فاتورةٍ صحيحة.
  const bank = await request(() => api.GET("/api/v1/bank-transfer/", {})).catch(() => null);
  const owed = Number(invoice.outstanding) > 0;

  return (
    <PageShell title={`فاتورة ${invoice.number}`}>
      <Notice
        message={flash?.message ?? ""}
        tone={flash?.code === "invoice_paid" ? "info" : "error"}
      />

      <div className="max-w-md rounded-lg border border-neutral-200 bg-white p-4">
        <dl className="space-y-3 text-sm">
          <div className="flex justify-between gap-4">
            <dt className="text-neutral-500">الحالة</dt>
            <dd className="font-semibold">{invoice.state_label}</dd>
          </div>
          <div className="flex justify-between gap-4">
            <dt className="text-neutral-500">المبلغ</dt>
            <dd className="money">{amount(invoice.amount)}</dd>
          </div>
          <div className="flex justify-between gap-4">
            <dt className="text-neutral-500">المسدَّد</dt>
            <dd className="money">{amount(invoice.amount_paid)}</dd>
          </div>
          <div className="flex justify-between gap-4">
            <dt className="text-neutral-500">المتبقّي</dt>
            {/* The server's field. Not `amount - amount_paid`. */}
            <dd className="money font-semibold">{amount(invoice.outstanding)}</dd>
          </div>
          <div className="flex justify-between gap-4">
            <dt className="text-neutral-500">صدرت</dt>
            <dd>{dateTime(invoice.issued_at)}</dd>
          </div>
          {invoice.due_at ? (
            <div className="flex justify-between gap-4">
              <dt className="text-neutral-500">تستحق</dt>
              <dd>{dateTime(invoice.due_at)}</dd>
            </div>
          ) : null}
        </dl>
      </div>

      {/*
        **حوالةٌ بنكيّةٌ وحدَها — ولا زرَّ «سدّد».** كان هنا نموذجٌ باختيارين
        («من الرصيد» و«تحويل بنكي») يُرسَلان إلى نقطةٍ **مغلقةٍ بقرار المالك**
        (T954) فيُرفضان دائماً: «رصيد التأمين ممنوع السداد منه للفواتير». والفاتورةُ
        يسجّل سدادَها الموظّفُ أو أودو حين يؤكّد البنكُ الحوالة. فالصفحةُ تقول ما
        يفعله العميل فعلاً: يحوّل المتبقّي إلى حساب الشركة، ثم يطلب استردادَ
        تأمينه بعد السداد.

        و`Number()` هنا مقارنةٌ بالصفر لا حساب: هل بقي شيءٌ أم لا — والرقمُ
        المعروض هو حقلُ الخادم `outstanding` كما هو.
      */}
      {owed ? (
        <section className="mt-6 max-w-md rounded-lg border border-neutral-200 bg-white p-4">
          <h2 className="mb-1 font-semibold">السداد بحوالة بنكية</h2>
          <p className="mb-4 text-sm text-neutral-600">
            حوّل المتبقّي <span className="money font-semibold">{amount(invoice.outstanding)}</span>{" "}
            ريال إلى حساب الشركة، واكتب رقم الفاتورة <span className="money">{invoice.number}</span> في
            بيان الحوالة. يُسجَّل السداد حين يؤكّده البنك.
          </p>
          {bank?.configured ? (
            <dl className="space-y-2 rounded bg-neutral-50 p-3 text-sm">
              {bank.beneficiary ? (
                <div className="flex justify-between gap-4">
                  <dt className="text-neutral-500">المستفيد</dt>
                  <dd>{bank.beneficiary}</dd>
                </div>
              ) : null}
              {bank.bank ? (
                <div className="flex justify-between gap-4">
                  <dt className="text-neutral-500">البنك</dt>
                  <dd>{bank.bank}</dd>
                </div>
              ) : null}
              <div className="flex justify-between gap-4">
                <dt className="text-neutral-500">الآيبان</dt>
                <dd className="money select-all" dir="ltr">{bank.iban}</dd>
              </div>
              {bank.account ? (
                <div className="flex justify-between gap-4">
                  <dt className="text-neutral-500">رقم الحساب</dt>
                  <dd className="money select-all" dir="ltr">{bank.account}</dd>
                </div>
              ) : null}
            </dl>
          ) : (
            <p className="rounded bg-amber-50 p-3 text-sm text-amber-800">
              بيانات حساب الشركة غير متاحة الآن — تواصل مع الدعم للحصول عليها.
            </p>
          )}
          <p className="mt-4 text-xs text-neutral-500">
            تأمين المزاد لا يُحتسب من ثمن المركبة. بعد سداد الفاتورة كاملةً يمكنك طلب
            استرداد تأمينك من «محفظتي».
          </p>
        </section>
      ) : (
        <p className="mt-6 text-sm text-neutral-600">لا مبلغ متبقٍّ على هذه الفاتورة.</p>
      )}
    </PageShell>
  );
}
