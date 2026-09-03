"use client";

/**
 * التحديث الحي في الويب — T1018 / J6.
 *
 * The one client component in this application, and it earns the exception: an
 * `EventSource` is a browser API and there is no server-rendered equivalent.
 *
 * What it shows and what it deliberately does not
 * -----------------------------------------------
 * The stream carries the customer's **own** bids and public vehicle states, and
 * nothing else — `apps/bidding/live.py` decides that and its docstring says why
 * at length. The short version, because it is the thing a future change would
 * get wrong: this is a **sealed auction**, there is no endpoint that lists the
 * bids on a car, and a live view of competitors' numbers would demolish that in
 * one component while looking like a feature.
 *
 * So there is no "highest bid" here, no "you are winning", no count of rivals.
 * If one appears in a design, the answer is that the server will not send it.
 *
 * «انقطع الاتصال» is the point of the component
 * ---------------------------------------------
 * The task names it directly: *رقم مزايدة قديم يبدو حياً أسوأ من لا رقم.* A
 * disconnected stream and a quiet one look identical — the numbers just sit
 * there — so the connection's state is rendered, and a stale figure is labelled
 * stale rather than left to be read as current.
 *
 * The initial values come from the server render (`initial`), so this component
 * has nothing to show before it connects and no flash of empty state. If the
 * script never runs at all, the page keeps the server's numbers and simply does
 * not update: worse, and still correct.
 */

import { useEffect, useState } from "react";

export interface LiveBid {
  id: number;
  vehicle_id: number;
  amount: string;
  is_withdrawn: boolean;
  is_superseded: boolean;
}

type Connection = "connecting" | "live" | "lost";

const LABELS: Record<Connection, string> = {
  connecting: "جارٍ الاتصال…",
  live: "التحديث حي",
  lost: "انقطع الاتصال — الأرقام أدناه قديمة",
};

export function LiveBids({
  vehicleId,
  initial,
}: {
  vehicleId: number;
  /** What the server rendered, so there is nothing to wait for. */
  initial: LiveBid | null;
}) {
  const [bid, setBid] = useState<LiveBid | null>(initial);
  const [connection, setConnection] = useState<Connection>("connecting");

  useEffect(() => {
    // The proxy prefix, like every other call from the browser: the session is
    // an HttpOnly cookie and the token never reaches this code (T1004).
    const source = new EventSource("/api/backend/api/v1/live/");

    source.addEventListener("open", () => setConnection("live"));

    source.addEventListener("state", (event) => {
      setConnection("live");
      try {
        const data = JSON.parse((event as MessageEvent<string>).data) as {
          bids: LiveBid[];
        };
        setBid(data.bids.find((row) => row.vehicle_id === vehicleId) ?? null);
      } catch {
        // A frame we cannot read is not a reason to blank the screen. The last
        // good value stays, and the connection state is what tells the customer
        // how much to trust it.
      }
    });

    source.addEventListener("error", () => setConnection("lost"));

    return () => source.close();
  }, [vehicleId]);

  return (
    <div className="mt-4 rounded border border-neutral-200 bg-neutral-50 p-3 text-sm">
      <p
        className={
          connection === "lost" ? "font-medium text-amber-800" : "text-neutral-500"
        }
      >
        {LABELS[connection]}
      </p>

      {bid ? (
        <p className="mt-1">
          مزايدتك القائمة <span className="money font-semibold">{bid.amount}</span> ريال
        </p>
      ) : (
        <p className="mt-1 text-neutral-600">لا مزايدة قائمة لك على هذه المركبة.</p>
      )}
    </div>
  );
}
