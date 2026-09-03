/**
 * حالة الشحن بعد العودة من البوابة — ولا معامل واحد من الرابط يُصدَّق. T1021.
 *
 * The acceptance criterion is that **tampering with the return parameters
 * changes no balance**, and the way this page satisfies it is by not reading
 * them at all. The only thing it takes from the url is the `reference`, and a
 * reference is not a claim: it names a row the server wrote before the customer
 * ever reached the gateway. Everything shown comes from asking the backend what
 * that row says.
 *
 * Change `?status=paid` to anything you like and this page renders the same
 * state, because nothing here consults it. In v1 the app believed a payment had
 * succeeded on exactly that basis — the gateway does not carry our user id, and
 * what came back in the query string was both losable and forgeable.
 *
 * A reference that is not this customer's is the backend's 404. Ownership is not
 * checked here: a check in a screen is a check that is absent from every other
 * way of reaching the endpoint.
 */

import type { Metadata } from "next";
import Link from "next/link";
import { cookies } from "next/headers";
import { notFound, redirect } from "next/navigation";

import { PageShell } from "@/features/shell/PageShell";
import { ApiError, api, request } from "@/lib/api";
import { amount, dateTime } from "@/lib/format";
import { authHeader, hasSession } from "@/lib/session";

export const metadata: Metadata = {
  title: "حالة الشحن",
  robots: { index: false, follow: false },
};

export const dynamic = "force-dynamic";

export default async function TopupStatusPage({
  params,
}: {
  params: Promise<{ reference: string }>;
}) {
  const store = await cookies();
  if (!hasSession(store)) redirect("/sign-in");

  const { reference } = await params;
  const headers = authHeader(store);

  let intent;
  try {
    intent = await request(() =>
      api.GET("/api/v1/wallet/topups/{reference}/", {
        headers,
        params: { path: { reference } },
      }),
    );
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) notFound();
    if (error instanceof ApiError && (error.status === 401 || error.status === 403)) {
      redirect("/sign-in");
    }
    throw error;
  }

  return (
    <PageShell title="حالة الشحن">
      <div className="max-w-md rounded-lg border border-neutral-200 bg-white p-4">
        <dl className="space-y-3 text-sm">
          <div className="flex justify-between gap-4">
            <dt className="text-neutral-500">الحالة</dt>
            {/* The server's word for it, not a mapping kept here. */}
            <dd className="font-semibold">{intent.state_label}</dd>
          </div>
          <div className="flex justify-between gap-4">
            <dt className="text-neutral-500">المبلغ</dt>
            <dd className="money">
              {amount(intent.amount)} {intent.currency}
            </dd>
          </div>
          <div className="flex justify-between gap-4">
            <dt className="text-neutral-500">الغرض</dt>
            <dd>{intent.purpose_label}</dd>
          </div>
          <div className="flex justify-between gap-4">
            <dt className="text-neutral-500">المرجع</dt>
            <dd className="money">{intent.reference}</dd>
          </div>
          <div className="flex justify-between gap-4">
            <dt className="text-neutral-500">آخر تحديث</dt>
            <dd>{dateTime(intent.updated_at)}</dd>
          </div>
        </dl>

        <p className="mt-4 text-xs text-neutral-500">
          هذه الحالة مقروءة من سجلّنا، لا من رابط العودة. الرصيد يتحرّك حين تؤكّد
          البوابة الدفع للخادم.
        </p>

        <Link href="/wallet" className="mt-4 block text-sm underline">
          إلى المحفظة
        </Link>
      </div>
    </PageShell>
  );
}
