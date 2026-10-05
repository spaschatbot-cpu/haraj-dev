/**
 * المحفظة بدلائها مفصَّلة — ثلاثة أرقام لا واحد. T1019 / G5.
 *
 * v1 showed one number. A customer read «رصيدك 10,000», assumed it was his to
 * withdraw, and discovered it was pinned to a bid he had placed. The engine was
 * rebuilt around that (phase 002): the money sits in named buckets and each held
 * riyal points at the auction or invoice holding it — and this screen's only job
 * is to not collapse that back into one figure.
 *
 * So: available, held for auctions, locked against dues, each on its own line,
 * and every one of them **openable on the entries that explain it** (Article
 * 1-6). The bucket rows link to the statement filtered to that bucket, which is
 * what turns "why is 8,000 locked?" from a support call into a click.
 *
 * Every amount is a string from the server, rendered as it arrived. The totals
 * are the server's too — `total` is a field on the response, not a sum computed
 * here. That is G5 («المجموع يطابق الدفتر»): a sum computed in the browser is a
 * second derivation, and a second derivation can be right on the day the first
 * is wrong.
 */

import type { Metadata } from "next";
import Link from "next/link";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { RefundRequestForm } from "@/features/wallet/RefundRequestForm";
import { TopupButton } from "@/features/wallet/TopupButton";
import { Notice } from "@/features/shell/Notice";
import { PageShell } from "@/features/shell/PageShell";
import { ApiError, api, request } from "@/lib/api";
import { readFlash } from "@/lib/flash";
import { amount, count, dateTime } from "@/lib/format";
import { authHeader, hasSession } from "@/lib/session";

export const metadata: Metadata = {
  title: "محفظتي",
  robots: { index: false, follow: false },
};

export const dynamic = "force-dynamic";

export default async function WalletPage() {
  const store = await cookies();
  if (!hasSession(store)) redirect("/sign-in");

  const flash = readFlash(store);
  const headers = authHeader(store);

  let wallet;
  try {
    wallet = await request(() => api.GET("/api/v1/wallet/", { headers }));
  } catch (error) {
    if (error instanceof ApiError && (error.status === 401 || error.status === 403)) {
      redirect("/sign-in");
    }
    throw error;
  }

  /*
    الطلبُ القائم — وكان لا يُعرَض أصلاً: يضغط العميلُ «أرسل» فيُقال له «لديك
    طلبٌ قائم» وهو لا يراه في الصفحة ولا يملك إنهاءه. وهو **يمنع المزايدة**
    (`refund_pending`)، فغيابُه عن الشاشة يجعل المنعَ بلا سبب ظاهر.

    وفشلُ الجلب لا يُسقط المحفظة: الأرصدةُ هي سببُ الصفحة، وقائمةُ الطلبات
    زيادةٌ عليها.
  */
  let openRefund = null;
  //: وآيبانُ آخر طلبٍ يُملأ به الحقلُ سلفاً — من طلب مرّةً لا يُعيد كتابة
  //: أربعةٍ وعشرين محرفاً، وإعادةُ كتابتها هي الموضعُ الذي يُخطئ فيه رقم.
  let lastIban = "";
  try {
    const refunds = await request(() =>
      api.GET("/api/v1/wallet/refund-requests/", { headers }),
    );
    const rows = refunds ?? [];
    openRefund =
      rows.find((row) => row.state === "requested" || row.state === "sent") ?? null;
    lastIban = rows.find((row) => row.iban)?.iban ?? "";
  } catch {
    openRefund = null;
  }

  return (
    <PageShell title="محفظتي">
      <Notice
        message={flash?.message ?? ""}
        tone={flash?.code?.startsWith("refund_") || flash?.code === "saved" ? "info" : "error"}
      />

      {/*
        Three figures, never one. Each is the server's own field — `available`,
        `held_for_auctions`, `locked_for_dues` — and none is added up here.
      */}
      <div className="grid gap-4 sm:grid-cols-3">
        {[
          ["متاح للمزايدة والسحب", wallet.available],
          ["محجوز لمزادات", wallet.held_for_auctions],
          ["مقفول على مستحقات", wallet.locked_for_dues],
        ].map(([label, value]) => (
          <div key={label} className="rounded-lg border border-outline-variant bg-white p-4">
            <p className="text-sm text-on-surface-variant">{label}</p>
            <p className="money mt-1 text-2xl font-bold">{amount(value)}</p>
            <p className="text-xs text-on-surface-variant">{wallet.currency}</p>
          </div>
        ))}
      </div>

      <p className="mt-4 text-sm text-on-surface-variant">
        المجموع <span className="money font-semibold">{amount(wallet.total)}</span> ·
        بحسب الدفتر في {dateTime(wallet.as_of)}
      </p>

      <TopupButton />

      <h2 className="mt-10 mb-3 text-lg font-semibold">الدلاء</h2>
      <ul className="divide-y divide-outline-variant rounded-lg border border-outline-variant bg-white">
        {wallet.buckets.map((bucket) => (
          <li key={bucket.kind} className="flex items-center justify-between gap-4 p-4">
            <div>
              <p className="font-medium">{bucket.label}</p>
              <p className="text-sm text-on-surface-variant">
                {count(bucket.entry_count)} حركة
              </p>
            </div>
            <div className="flex items-center gap-4">
              <span className="money font-semibold">{amount(bucket.amount)}</span>
              {/*
                Article 1-6: every number opens on the entries that explain it.
                The link points at this app's own statement route rather than at
                the backend url the server put in `statement` — the browser
                cannot call the backend, and the filter is the same either way.
              */}
              <Link
                href={`/wallet/statement?bucket=${bucket.kind}`}
                className="text-sm underline"
              >
                الحركات
              </Link>
            </div>
          </li>
        ))}
      </ul>

      <h2 className="mt-10 mb-3 text-lg font-semibold">الحجوزات القائمة</h2>
      {wallet.holds.length === 0 ? (
        <p className="text-on-surface-variant">لا شيء محجوز.</p>
      ) : (
        <ul className="divide-y divide-outline-variant rounded-lg border border-outline-variant bg-white">
          {wallet.holds.map((hold) => (
            <li key={hold.id} className="flex items-center justify-between gap-4 p-4">
              <div>
                <p className="font-medium">{hold.reason_label}</p>
                {/*
                  What this money is pinned to. In v1 the question had no stored
                  answer at all and support resolved it from memory.
                */}
                <p className="text-sm text-on-surface-variant">
                  {hold.auction
                    ? `مزاد ${(hold.auction as { number?: number }).number ?? ""}`
                    : hold.invoice
                      ? `فاتورة ${(hold.invoice as { number?: string }).number ?? ""}`
                      : ""}
                  {" · "}
                  {dateTime(hold.created_at)}
                </p>
              </div>
              <span className="money font-semibold">{amount(hold.amount)}</span>
            </li>
          ))}
        </ul>
      )}

      <RefundRequestForm
        available={wallet.available}
        unit={wallet.deposit_unit}
        open={openRefund}
        iban={openRefund?.iban ?? lastIban}
      />
    </PageShell>
  );
}
