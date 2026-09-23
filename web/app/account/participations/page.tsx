/**
 * مشاركاتي في المزادات — كلُّ مزادٍ دخلتَه، وعددُ مزايداتك فيه، وما صار إليه
 * تأمينُه. نظيرُ «مشاركاتي في المزادات» في v1 (`menu/accounts.php`).
 *
 * **حالةُ التأمين من الخادم لا من مطابقةٍ هنا.** `ParticipationInsurance`
 * يُقرأ من `money.Hold` وحده؛ والبديل — أن تطابق الشاشةُ «مزايداتي» على
 * «المحفظة» — قاعدةٌ في شاشة، وتخطئ أوّلَ ما يُفَكّ حجزٌ والمزايداتُ باقية.
 */

import type { Metadata } from "next";
import Link from "next/link";

import { CARD, SubpageHead, loadProfile } from "@/features/account/ui";
import { PageShell } from "@/features/shell/PageShell";
import { api, request } from "@/lib/api";
import { amount, count, dateTime } from "@/lib/format";

export const metadata: Metadata = {
  title: "مشاركاتي في المزادات",
  robots: { index: false, follow: false },
};

export const dynamic = "force-dynamic";

export default async function ParticipationsPage() {
  const { headers } = await loadProfile();
  const page = await request(() => api.GET("/api/v1/participations/", { headers }));

  return (
    <PageShell>
      <div className="mx-auto max-w-3xl">
        <SubpageHead
          title="مشاركاتي في المزادات"
          hint={`${count(page.total)} مزاداً — تأمينٌ واحدٌ لكلّ مزادٍ مهما بلغ عددُ السيارات.`}
        />

        {page.results.length === 0 ? (
          <div className={`${CARD} text-center`}>
            <p className="text-body-md text-on-surface-variant">لم تشارك في مزادٍ بعد.</p>
            <Link href="/" className="mt-3 inline-block text-label-md text-secondary hover:underline">
              تصفّح المزادات المفتوحة
            </Link>
          </div>
        ) : (
          <ul className="space-y-3">
            {page.results.map((item) => (
              <li key={item.auction.id} className={CARD}>
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="text-label-sm text-secondary">
                      مزاد <span className="money">{item.auction.number}</span> · {item.auction.state_label}
                    </p>
                    <h2 className="truncate text-headline-sm">{item.auction.title}</h2>
                    <p className="text-body-sm text-on-surface-variant">
                      ينتهي {dateTime(item.auction.ends_at)}
                    </p>
                  </div>
                  <span className="rounded-full bg-surface-container px-3 py-1 text-label-sm text-on-surface">
                    {count(item.bids_count)} مزايدة
                  </span>
                </div>

                <div className="mt-4 flex items-center justify-between gap-3 rounded-xl bg-surface-low px-4 py-3">
                  <span className="text-body-sm text-on-surface-variant">التأمين</span>
                  <span className="text-label-md">
                    {item.insurance.state_label}
                    {item.insurance.amount ? (
                      <span className="money ms-2 text-on-surface-variant">
                        {amount(item.insurance.amount)} {item.insurance.currency}
                      </span>
                    ) : null}
                  </span>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </PageShell>
  );
}
