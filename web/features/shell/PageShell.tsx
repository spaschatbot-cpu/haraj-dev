/**
 * إطار الصفحات العامة — رأس وحدود عرض، في مكان واحد.
 *
 * Not a layout file, because the signed-in shell will differ and a single
 * layout that branches on the session is a layout that renders the wrong header
 * on the one page somebody forgot to pass the flag to.
 */

import Link from "next/link";

export function PageShell({
  title,
  children,
}: {
  title?: string;
  children: React.ReactNode;
}) {
  return (
    <>
      <header className="border-b border-neutral-200 bg-white">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-4 py-3">
          <Link href="/" className="text-lg font-bold">
            حراج
          </Link>
          <nav className="flex gap-4 text-sm">
            <Link href="/auctions" className="text-neutral-700 hover:underline">
              المزادات
            </Link>
            <Link href="/bids" className="text-neutral-700 hover:underline">
              مزايداتي
            </Link>
            <Link href="/wallet" className="text-neutral-700 hover:underline">
              محفظتي
            </Link>
            <Link href="/purchases" className="text-neutral-700 hover:underline">
              مشترياتي
            </Link>
            <Link href="/account" className="text-neutral-700 hover:underline">
              حسابي
            </Link>
          </nav>
        </div>
      </header>

      <main className="mx-auto max-w-5xl px-4 py-8">
        {title ? <h1 className="mb-6 text-2xl font-bold">{title}</h1> : null}
        {children}
      </main>
    </>
  );
}
