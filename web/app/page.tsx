/**
 * الصفحة الأولى — هيكل مؤقّت حتى تصل قائمة المزادات (T1007).
 *
 * Deliberately not a "welcome to Next.js" placeholder: this route is what a
 * build check and a first deploy render, and a page that says nothing about
 * this product cannot tell anybody whether the deploy worked.
 */
export default function Home() {
  return (
    <main className="mx-auto max-w-3xl px-4 py-12">
      <h1 className="text-2xl font-bold">حراج</h1>
      <p className="mt-4 text-neutral-600">
        الأساس جاهز: العربية وRTL، والعميل المولَّد من المخطط، والجلسة في كوكيز
        محميّة. قائمة المزادات تصل في T1007.
      </p>
    </main>
  );
}
